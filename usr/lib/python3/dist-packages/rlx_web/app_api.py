import os

import pam
import pytz
import psutil
import json
import asyncio
import platform
import shutil

from pathlib import Path
from multiprocessing import cpu_count

from .osal.keyboard import KeyboardLayouts
from .osal.date_and_time import format_dt_info, dt_info
from rlx_osal import OSAL, OSAL_NONE, OSAL_OK

from datetime import datetime, timedelta
from netifaces import ifaddresses, AF_INET
from netaddr import IPAddress
from launchy import Launchy

import cirrina
from .app import RLXWebApp
from aiohttp import web, hdrs
from http import HTTPStatus

from . import errors, utils
from .config import config as rlx_web_config
from .log import logger
from .auto_logout.helpers import update_last_access_time
from .remote_access.mobile_device import helpers as mobile_device_helpers
from .remote_access.mobile_device.db import update_granted_status_by_id

UPLOAD_DIR = "/opt/roche/var/tmp"
ETC_DIR = "/opt/roche/etc"


async def run_cmd(cmd, log_error=True, debug=False, cwd=None):
    stdout = ""

    async def outh(line):
        nonlocal stdout
        stdout += line + "\n"
        if debug:
            logger.info("stdout: %s" % line)

    stderr = ""

    async def errh(line):
        nonlocal stderr
        stderr += line + "\n"
        if debug:
            logger.info("stderr: %s" % line)

    if debug:
        logger.info("running: '%s'" % cmd)
    process = Launchy(cmd, outh, errh, cwd=cwd)
    await process.launch()
    ret = await process.wait()
    if debug:
        logger.info("ret: %d" % ret)
    if ret != 0 and log_error:
        logger.error("command: '%s'" % cmd)
        logger.error("command error: %s" % stderr)

    return ret, stdout, stderr


app: RLXWebApp = RLXWebApp()
app.title = "RLX Web"
app.description = "RLX Maintenance Web"
app.api_version = 1
app.contact = ""

# import API
from .addon import *  # noqa
from .auto_logout import api as auto_logout_api  # noqa
from .cluster import *  # noqa
from .docker.api import *  # noqa
from .edgeagent import *  # noqa
from .httpscontrol import *  # noqa
from .kubernetes import *  # noqa
from .launchcode import processLaunchCode, process_lc  # noqa
from .openvpn import *  # noqa
from .otss import *  # noqa
from .peripherals import *  # noqa
from .remote_access.mobile_device import api as mobile_device_api  # noqa
from .remote_access.remote_access_control import (  # noqa
    api as remote_access_control_api,
)
from .remote_screen import remote_screen  # noqa
from .remote_screen import external_remote_screen  # noqa
from .full_disk_encryption import api as full_disk_encryption_api  # noqa
from .report import *  # noqa
from .rsa2l import *  # noqa
from .securestorage import *  # noqa
from .externalstorage import *  # noqa
from .websocket import *  # noqa
from .samba_server import *  # noqa
from .date_and_time import *  # noqa
from .software_upgrade import *  # noqa
from .maintenance import *  # noqa

# NST project specific
from .nst import *  # noqa


async def offlineLaunchCode():
    launchcode_available = app.is_launch_code_available()
    OFFLINE_LAUNCHCODE = "/opt/roche/var/spool/launchcode"
    data = {}
    if launchcode_available and Path(OFFLINE_LAUNCHCODE).is_file():
        with open(OFFLINE_LAUNCHCODE, "r") as f:
            data = json.load(f)
            try:
                await process_lc(data["data"])
            except Exception:
                logger.exception("Error running offline launchCode")
            Path(OFFLINE_LAUNCHCODE).unlink()


class NetworkInfo:
    def __init__(self):
        self.netconfig = {}
        self.interface = []
        self.get_interface_name()

    def get_interface_name(self):
        self.interface_name = "eth0"
        networkmap = "/opt/roche/etc/rlx/networkmap"
        osal_env = "/etc/default/rlx-osal"
        if os.path.isfile(networkmap):
            try:
                with open(networkmap, "r") as f:
                    lines = f.readlines()
                    for line in lines:
                        if not line:
                            continue
                        if "main:" in line:
                            line = line.rstrip("\n").strip()
                            env = line.split()
                            if len(env) == 2:
                                self.interface_name = env[1].strip()
                                break
            except OSError as exc:
                logger.exception(exc)
        elif os.path.isfile(osal_env):
            try:
                with open(osal_env, "r") as f:
                    lines = f.readlines()
                    for line in lines:
                        if not line:
                            continue
                        line = line.rstrip("\n").strip()
                        env = line.split("=")
                        if len(env) == 2:
                            if "RLX_MAIN_NETIF" in env[0].strip():
                                self.interface_name = env[1].strip()
            except OSError as exc:
                logger.exception(exc)

    async def get_network_info(self):
        try:
            ret, networkctl, _ = await run_cmd(
                "networkctl status " + self.interface_name
            )
        except Exception as exc:
            logger.exception(exc)
            return

        if ret != 0:
            logger.error("Error getting network status")
            return

        if not networkctl:
            logger.error("Network interface list is empty")
            return

        lines = networkctl.split("\n")
        lastcfg = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if ": " in line:
                k, v = line.split(": ", 1)
                k = k.strip()
                v = v.strip()
                self.netconfig[k] = v
                lastcfg = k
            elif lastcfg is not None:
                oldval = self.netconfig[lastcfg]
                if not isinstance(oldval, list):
                    self.netconfig[lastcfg] = [oldval]
                (self.netconfig[lastcfg]).append(line.strip())

        inet_config = ifaddresses(self.interface_name).get(AF_INET, None)
        if inet_config:
            for config in inet_config:
                self.interface.append(config)

    def get_netmask(self):
        netmask = ""
        if self.interface:
            netmask = self.interface[0].get("netmask", "")
        if isinstance(netmask, list):
            netmask = netmask[0]
        return netmask

    def get_macaddr(self):
        if "HW Address" in self.netconfig:
            return self.netconfig.get("HW Address", "").split(" ")[0]
        elif "Hardware Address" in self.netconfig:
            return self.netconfig.get("Hardware Address", "").split(" ")[0]
        else:
            return ""

    def get_gateway(self):
        gateway = self.netconfig.get("Gateway", "")
        if isinstance(gateway, list):
            gateway = gateway[0]
        if " " in gateway:  # gateway name after space
            gateway = gateway.split(" ")
            gateway = gateway[0]
        return gateway

    def get_dns(self):
        dns1 = self.netconfig.get("DNS", "")
        dns2 = ""
        if isinstance(dns1, list):
            dns2 = dns1[1]
            dns1 = dns1[0]
        return [dns1, dns2]

    async def get_info(self):
        await self.get_network_info()
        network_info = {
            "status": self.get_status(),
            "dhcp": self.get_dhcp(),
            "ip": self.get_ip(),
            "netmask": self.get_netmask(),
            "gateway": self.get_gateway(),
            "dns1": self.get_dns()[0],
            "dns2": self.get_dns()[1],
            "netfile": self.netconfig.get("Network File", None),
            "macaddr": self.get_macaddr(),
            "ips": (await self.get_ip_all_interfaces()),
        }
        return network_info

    def get_ip(self):
        ip = [""]
        if self.interface:
            ip = []
            for config in self.interface:
                ip.append(config.get("addr", ""))
        return ip

    async def get_ip_all_interfaces(self):
        try:
            ret, networkctl, _ = await run_cmd("networkctl")
        except Exception as exc:
            logger.exception(exc)
            return [""]

        if ret != 0:
            logger.error("Error getting network interfaces")
            return [""]

        output = networkctl.split("\n")
        inames = []
        for line in output[1:-1]:
            if not line:
                continue
            if "ether" in line and "veth" not in line:
                inames.append(line.split()[1].strip())
        if not inames:
            logger.error("Network Info entries are empty for all interfaces")
            return [""]

        try:
            ret, networkctl, _ = await run_cmd("networkctl status")
        except Exception as exc:
            logger.exception(exc)
            return [""]

        if ret != 0:
            logger.error("Error getting network interfaces")
            return [""]

        if not networkctl:
            raise Exception("Network Info entries are empty for all interfaces")

        lines = networkctl.split("\n")
        lastcfg = None
        netconfig = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if ": " in line:
                k, v = line.split(": ", 1)
                k = k.strip()
                v = v.strip()
                netconfig[k] = v
                lastcfg = k
            elif lastcfg is not None:
                oldval = netconfig[lastcfg]
                if not isinstance(oldval, list):
                    netconfig[lastcfg] = [oldval]
                (netconfig[lastcfg]).append(line.strip())
        ips = [""]  # <IP> on <interface>
        try:
            ips = netconfig["Address"]
        except Exception:
            return [""]
        if not isinstance(ips, list):
            ips = [ips]
        ips_valid = []
        for ip in ips:
            ip_iname = ip.split()[-1].strip()
            if ip_iname in inames:
                ips_valid.append(ip)
        if not ips_valid:
            ips_valid = [""]
        ips_valid_clean = []
        for ip in ips_valid:
            ips_valid_clean.append(ip.split("on")[0].strip())
        return ips_valid_clean

    def get_status(self):
        state = self.netconfig.get("State", "?")
        if "configuring" in state:
            return "Configuring"
        if "routable" in state:
            return "OK"
        if "off" in state:
            return "Off"
        if "no-carrier" in state:
            return "Cable not connected"
        return state

    def get_dhcp(self):
        netfile = self.netconfig.get("Network File", None)
        if netfile is None or netfile == "n/a":
            return "Please configure network"
        try:
            with open(netfile) as f:
                config = f.read()
                if "DHCP=yes" in config:
                    return "yes"
                elif "DHCP=ipv4" in config:
                    return "yes"
                else:
                    return "no"
        except OSError:
            return "N/A"
        return "no"


class NTPInfo:
    def __init__(self):
        self.ntp_primary = []
        self.ntp_fallback = []
        self.use_ntp = False
        ret = app.execute_osal("GetNTPInfo")
        if ret.outcome != OSAL_OK:
            logger.error("Error getting NTP servers info")
            return
        self.ntp_primary = list(ret.response.servers)
        self.ntp_fallback = list(ret.response.fallbackNTPServers)
        self.use_ntp = ret.response.useNTP


def list_timezones():
    """
    Converts the list of all timezones from the pytz library into a structured dictionary.

    The dictionary categorizes timezones by their continent or region, with each continent/region
    as keys and a list of their specific timezones as values. Special cases like 'UTC' and 'Zulu'
    are included as standalone entries without a list of sub-regions.

    Returns:
        dict: A dictionary where keys are continent or region names (e.g., 'Africa', 'Europe'),
              and values are lists of strings representing the specific timezones within those regions.
              For special standalone timezones like 'UTC' and 'Zulu', the value is an empty list.

    Example of returned dictionary structure:
    {
        'Africa': ['Abidjan', 'Accra', 'Addis_Ababa', ...],
        'Europe': ['Amsterdam', 'Andorra', 'Astrakhan', ...],
        'UTC': ['UTC'],
        'Zulu': ['Zulu']
    }

    Note:
        This function requires the pytz library to be installed and available.
    """

    timezone_dict = {}

    for tz in pytz.all_timezones:
        parts = tz.split("/")

        region = parts[0]
        if region not in timezone_dict:
            timezone_dict[region] = []

        if len(parts) == 1:
            timezone_dict[region].append(tz)  # Here tz is just the region like 'UTC'
        else:
            specific_region = "/".join(parts[1:])
            timezone_dict[region].append(specific_region)
    return timezone_dict


# NOTE: do NOT change the `async def authenticate(...):` signature and
# file location of this function, as the tests depend on it:
# https://code.roche.com/rlx/rlx-testsuite/-/merge_requests/88
@app.auth_handler
async def authenticate(request, username, password):
    logger.info(f"Login: {username}")

    if not utils.is_local(request) and app.has_capability("web-remote-access"):
        if not app.read_remote_access_status():
            logger.warning(
                f"User '{username}' attempted to login directly through /login api"
            )
            return False

    if username is None:
        return False

    if username == "roche":
        authenticated = pam.authenticate(username, password)
    else:
        authenticated = pam.authenticate("fsr", f"{username}:{password}")

    if authenticated:
        app.execute_osal("NotifyMaintenanceWebAccessStarted", username)

        if app.has_capability("web-auto-logout"):
            update_last_access_time(request.cirrina.web_session)

        # Close websocket connections as they would remain unauthenticated
        await app.close_websocket_connections()

    return authenticated


@app.auth_unauthorized
async def unauthorized(request):
    request.cirrina.web_session.invalidate()
    return web.Response(status=401)


@app.logout_handler
def logout(request):
    username = request.cirrina.web_session.get("username")

    logger.info(f"Logout: {username}")

    if username is not None:
        app.execute_osal("NotifyMaintenanceWebAccessStopped", username)

    # Invalidate QR Code when user logout
    mobile_device_helpers.reset_registration_jwt()


@app.http_get("/api/authenticated")
async def get_authenticated(request: cirrina.server.CirrinaContext):
    if request.cirrina.web_session.get("username"):
        return web.json_response(status=200)
    else:
        return web.json_response(status=403)


@app.http_get("/api/ssh-pubkey")
async def getSSHPubKey(request):
    sshpubkey_file = "/opt/roche/home/.ssh/id_rsa.pub"
    if os.path.isfile(sshpubkey_file):
        try:
            with open(sshpubkey_file, "r") as f:
                sshpubkey = f.read().rstrip("\n")
                return web.Response(text=sshpubkey)
        except OSError as exc:
            logger.exception(exc)
            return web.Response(text="Internal Error calling getSSHPubKey", status=500)
    return web.Response(status=404)


@app.http_get("/api/upgrade/history")
@app.authenticated
async def upgradeHistory(request):
    ret = app.execute_osal("GetSoftwareHistory")
    hist = [
        {
            "ts": entry.startTime,
            "basever": entry.version,
            "success": entry.success,
        }
        for entry in ret.response.entries
    ]
    return web.json_response(hist)


async def do_upgrade(keepcurrentver, keepupgradesnapshot):
    try:
        app.execute_osal(
            "SoftwareUpgradeOffline",
            "",
            "",
            "",
            keepcurrentver,
            keepupgradesnapshot,
            "",
        )
    except Exception as e:
        app.logger.exception("SoftwareUpgradeOffline failed")
        await sendevent("SoftwareUpgradeFailed", {"data": str(e)})


@app.http_upload("/api/upgrade", upload_dir=UPLOAD_DIR)
@app.authenticated
async def file_upload(request, tempfile, filename, size):
    data = await request.post()
    if not filename.endswith(".tar.xz"):
        return web.Response(text="Wrong file format", status=415)
    keepcurrentver = data.get("keepcurrentver", None)
    if not keepcurrentver:
        return web.Response(text="Internal Error: keepcurrentver", status=400)
    keepcurrentver = keepcurrentver == "true"
    keepupgradesnapshot = False
    if os.path.isfile("/opt/roche/etc/.keepupgradesnapshot"):
        keepupgradesnapshot = True
    shutil.move(tempfile, "/opt/roche/var/spool/upgrade.tar.xz")
    app.upgrade_task = asyncio.ensure_future(
        do_upgrade(keepcurrentver, keepupgradesnapshot)
    )
    return web.Response()


@app.http_get("/api/upgrade/usb")
@app.authenticated
async def checkSoftwareUpgradeUSB(request):
    devname = app.get_argument(request, "devname")
    ret = app.execute_osal("GetSoftwareUpgradeFromUSBStatus", devname)
    d = {"available": ret.response.available, "filename": ret.response.filename}
    return web.json_response(d)


@app.http_post("/api/upgrade/usb")
@app.authenticated
async def upgradeFromUSB(request):
    params = await request.json()
    devname = params.get("devname", None)
    if devname is None:
        return web.Response(text="Internal Error", status=400)
    filename = params.get("upgradeFile", None)
    if filename is None:
        return web.Response(text="Internal Error", status=400)
    if not filename.endswith(".tar.xz"):
        return web.Response(text="Wrong file format", status=415)
    app.execute_osal(
        "CopyFromUSBStorage",
        devname,
        filename,
        "/opt/roche/var/spool",
        "upgrade.tar.xz",
    )
    app.execute_osal("SoftwareUpgradeOffline", "", "", "", False, False, "")
    return web.Response()


@app.http_get("/api/upgrade/log")
async def upgradeLog(request):
    lockfile = "/run/osal-upgrade.lock"
    appupgradelockfile = "/opt/roche/etc/.rlx-app-upgrade"
    osallog = "/opt/roche/var/log/rlx-upgrade.log"
    if os.path.isfile(lockfile) or os.path.isfile(appupgradelockfile):
        try:
            with open(osallog, "r") as f:
                output = f.read()
                logs = []
                entries = output.split("\n")
                for entry in entries:
                    entry = entry.strip()
                    if not entry:
                        continue
                    if (
                        entry.startswith("*I:")
                        or entry.startswith("*W:")
                        or entry.startswith("*E:")
                    ):
                        entry = entry[1:]
                        logs.append(entry)
                return web.json_response(logs)
        except OSError as exc:
            logger.exception(exc)
            return web.Response(text="Internal Error", status=500)
    return web.json_response("")


@app.http_post("/api/system/reboot-remote")
@app.authenticated
async def systemRebootRemote(request):
    app.execute_osal("SystemRestart", 1)
    return web.Response()


@app.http_post("/api/system/reboot")
async def systemReboot(request):
    if not utils.is_local(request):
        raise web.HTTPUnauthorized(text="Only local user can reboot the system")
    app.execute_osal("SystemRestart", 1)
    return web.Response()


@app.http_post("/api/system/shutdown")
async def systemShutdown(request):
    if not utils.is_local(request):
        raise web.HTTPUnauthorized(text="Only local user can shutdown the system")
    app.execute_osal("SystemShutdown", 1)
    return web.Response()


@app.http_get("/api/system/integrity")
@app.authenticated
async def getSystemIntegrityCheck(request):
    ret = app.execute_osal("CheckSoftwareIntegrity")
    passed = ret.response.passed
    modfiles = []
    for f in ret.response.changedFiles:
        if not f:
            continue
        modfiles.append(f)
    d = {"passed": passed, "modfiles": modfiles}
    return web.json_response(d)


@app.http_get("/api/system/settings")
@app.authenticated
async def getSystemSettings(request):
    settings = {}
    network_info = await NetworkInfo().get_info()
    netfile = network_info.get("netfile", None)
    if netfile is None or netfile == "n/a":
        network = {
            "use_dhcp": False,
            "ip": [""],
            "netmask": "",
            "gateway": "",
            "dns1": "",
            "dns2": "",
            "netfile": "",
            "macaddr": "",
            "status": "",
        }
    else:
        dhcp = network_info.get("dhcp", "")
        use_dhcp = "false"
        if dhcp == "yes":
            use_dhcp = "true"
        ip = network_info.get("ip", [""])
        netmask = network_info.get("netmask", "")
        gateway = network_info.get("gateway", "")
        dns1 = network_info.get("dns1", "")
        dns2 = network_info.get("dns2", "")
        macaddr = network_info.get("macaddr", "")
        status = network_info.get("status", "")
        network = {
            "use_dhcp": use_dhcp,
            "ip": ip,
            "netmask": netmask,
            "gateway": gateway,
            "dns1": dns1,
            "dns2": dns2,
            "netfile": netfile,
            "macaddr": macaddr,
            "status": status,
        }
    ntp_info = NTPInfo()
    ntp = {
        "use_ntp": ntp_info.use_ntp,
        "server1": ntp_info.ntp_primary,
        "server2": ntp_info.ntp_fallback,
    }
    tz = dt_info().tz_name
    area = None
    loc = None
    if tz:
        tz = tz.split("/", 1)
        area = tz[0].strip()
        if len(tz) == 1:
            loc = area
        else:
            loc = tz[1].strip()

    keyboardLayouts = KeyboardLayouts().layouts
    timezones = list_timezones()
    settings = {
        "network": network,
        "ntp": ntp,
        "hostname": get_hostname(),
        "keyboard_layouts": keyboardLayouts,
        "selected_keyboard_layout": get_keyboardLayout(),
        "timezones": timezones,
        "selected_timezone_area": area,
        "selected_timezone_loc": loc,
    }
    return web.json_response(settings)


@app.http_get("/api/system/settings/keyboard/layouts")
@app.authenticated
async def getKeyboardLayouts(request):
    keyboardLayouts = KeyboardLayouts().layouts
    InvertedKeyboardLayouts = {}
    if keyboardLayouts:
        for code, layout in keyboardLayouts.items():
            InvertedKeyboardLayouts[layout] = code
        return web.json_response(InvertedKeyboardLayouts)
    return web.Response(text="Failed calling getKeyboardLayouts", status=500)


@app.http_get("/api/system/settings/timezones")
@app.authenticated
async def getTimezones(request):
    timezones = list_timezones()
    if timezones:
        return web.json_response(timezones)
    return web.Response(text="Internal Error", status=500)


@app.http_post("/api/system/settings/network")
@app.authenticated
async def configureNetwork(request):
    settings = await request.json()
    use_dhcp = settings.get("usedhcp", None)
    if use_dhcp is None:
        return web.Response(text="Internal Error: use_dhcp is None", status=400)
    netfile = settings.get("netfile", None)
    if netfile is None:
        return web.Response(text="Internal Error: netfile is None", status=400)
    if use_dhcp == "true":
        app.execute_osal(
            "ConfigureNetworkInterface",
            True,
            [""],
            24,
            "",
            "",
            "",
            netfile,
            "",
            True,
            "",
        )
        # configuration may take some time wait 5 seconds, otherwise netfile can be "n/a"
        await asyncio.sleep(5)
        return web.Response()
    elif use_dhcp == "false":
        ips = settings.get("ip", None)
        if not ips:
            return web.Response(text="Internal Error: ips is None", status=400)
        netmaskCIDR = IPAddress(settings.get("netmask", None).strip()).netmask_bits()
        app.execute_osal(
            "ConfigureNetworkInterface",
            False,
            ips,
            netmaskCIDR,
            settings.get("gateway", None).strip(),
            settings.get("dns1", None).strip(),
            settings.get("dns2", None).strip(),
            netfile,
            "",
            False,
            "",
        )
        # configuration may take some time wait 5 seconds, otherwise netfile can be "n/a"
        await asyncio.sleep(5)
        return web.Response()
    return web.Response(text="Internal Error", status=500)


@app.http_post("/api/system/settings/ntp")
@app.authenticated
async def configureNTP(request):
    settings = await request.json()
    use_ntp = settings.get("usentp", None)

    if use_ntp is True:
        app.execute_osal(
            "ConfigureNTP", settings.get("ntpservers1"), settings.get("ntpservers2")
        )
        app.execute_osal("EnableNTP")

        return web.Response(status=HTTPStatus.OK)
    elif use_ntp is False:
        app.execute_osal("DisableNTP")
        return web.Response(status=HTTPStatus.OK)

    return web.HTTPBadRequest(reason="Invalid usentp value")


@app.http_post("/api/system/settings/keyboard/layouts")
@app.authenticated
async def configureKeyboardLayout(request):
    settings = await request.json()
    layout = settings.get("selectedkeyboardlayout", None)
    if layout:
        app.execute_osal("SetKeyboardLayout", layout)
        return web.Response()
    return web.Response(text="Internal Error: layout is None", status=400)


@app.http_post("/api/system/settings/timezones")
@app.authenticated
async def configureTimezone(request):
    settings = await request.json()
    tzarea = settings.get("selectedtimezonearea", None)
    tzloc = settings.get("selectedtimezoneloc", None)
    if tzarea and tzloc:
        tz = tzarea + "/" + tzloc
        if tzarea == "UTC":  # discard loc
            tz = "UTC"
        app.execute_osal("SetTimezone", tz)
        return web.Response()
    return web.Response(text="Internal Error: tzarea or tzloc is None", status=400)


@app.http_post("/api/system/settings/hostname")
@app.authenticated
async def setHostname(request):
    data = await request.json()
    hostname = data.get("hostname", None)
    if hostname:
        app.execute_osal("SetHostname", hostname)
        return web.Response()
    return web.Response(text="Internal Error: hostname is None", status=400)


@app.http_get("/api/system/snapshotinfo")
@app.authenticated
async def getSnapshotInfo(request):
    ret = OSAL().GetSnapshotInfo()
    if ret.outcome == OSAL_NONE:
        return web.Response(text="Warning: " + str(ret.errorMessage), status=204)
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)
    info = {
        "snapshotsSupported": ret.response.snapshotsSupported,
        "snapshottingAvailable": ret.response.snapshottingAvailable,
        "freeSnapshotSpace": ret.response.freeSnapshotSpace,
    }
    return web.json_response(info)


@app.http_post("/api/system/snapshot")
@app.authenticated
async def systemSnapshot(request):
    params = await request.json()
    snapshot_id = params.get("id", None)
    snapshot_action = params.get("action", None)

    try:
        snapshot_id = int(snapshot_id)
    except (TypeError, ValueError):
        return web.Response(reason="Invalid id", status=400)

    if snapshot_action == "remove":
        ret = OSAL().RemoveSystemVersion(snapshot_id)
    elif snapshot_action == "set_active":
        ret = OSAL().SetActiveSystemVersion(snapshot_id)
    elif snapshot_action == "restore":
        ret = OSAL().SetActiveSystemVersion(snapshot_id)
    else:
        return web.Response(reason="Invalid action", status=400)

    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)

    app.execute_osal("SystemRestart", 1)
    return web.Response()


@app.http_post("/api/system/factoryreset")
@app.authenticated
async def systemFactoryReset(request):
    app.execute_osal("FactoryReset")
    app.execute_osal("SystemRestart", 1)
    return web.Response()


@app.http_get("/api/system/systemversions")
@app.authenticated
async def getSystemVersions(request):
    systemVersions = []
    ret = OSAL().GetSystemVersionList()
    if ret.outcome == OSAL_NONE:
        return web.Response(text="Warning: " + str(ret.errorMessage), status=204)
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)
    for ver in ret.response.versions:
        if not ver:
            continue
        d = {
            "id": ver.systemID,
            "version": ver.version,
            "installDate": ver.installDate,
            "snapshotPercentages": list(ver.snapshotPercentages),
        }
        systemVersions.append(d)
    return web.json_response(systemVersions)


@app.http_get("/api/system/factorysystemversion")
@app.authenticated
async def getFactorySystemVersion(request):
    ret = OSAL().GetFactorySystemVersion()
    if ret.outcome == OSAL_NONE:
        return web.Response(text="Warning: " + str(ret.errorMessage), status=204)
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)
    d = {"snapshotPercentages": []}
    for perc in ret.response.snapshotPercentages:
        if not perc:
            continue
        d["snapshotPercentages"].append(perc)
    return web.json_response(d)


@app.http_get("/api/network/ping")
@app.authenticated
async def statusPing(request):
    ret = app.execute_osal("GetPingStatus")
    pingable = "false"
    if ret.response.pingable:
        pingable = "true"
    return web.json_response(pingable)


@app.http_post("/api/network/ping")
@app.authenticated
async def enablePing(request):
    app.execute_osal("EnablePing")
    return web.Response()


@app.http_delete("/api/network/ping")
@app.authenticated
async def disablePing(request):
    app.execute_osal("DisablePing")
    return web.Response()


@app.http_get("/api/snmp")
@app.authenticated
async def statusSNMP(request):
    ret = app.execute_osal("GetSNMPServerStatus")
    snmpEnabled = "false"
    if ret.response.enabled:
        snmpEnabled = "true"
    return web.json_response(snmpEnabled)


@app.http_post("/api/snmp")
@app.authenticated
async def enableSNMP(request):
    app.execute_osal("EnableSNMPServer")
    return web.Response()


@app.http_delete("/api/snmp")
@app.authenticated
async def disableSNMP(request):
    app.execute_osal("DisableSNMPServer")
    return web.Response()


@app.http_get("/api/ssh")
@app.authenticated
async def statusSSH(request):
    ret = app.execute_osal("GetSSHServerStatus")
    sshEnabled = "false"
    if ret.response.enabled:
        sshEnabled = "true"
    return web.json_response(sshEnabled)


@app.http_post("/api/ssh")
@app.authenticated
async def enableSSH(request):
    app.execute_osal("EnableSSHServer")
    return web.Response()


@app.http_delete("/api/ssh")
@app.authenticated
async def disableSSH(request):
    app.execute_osal("DisableSSHServer")
    return web.Response()


@app.http_get("/api/http-proxy")
@app.authenticated
async def statusHTTPProxy(request):
    httpProxy = ""
    httpProxyUser = ""
    try:
        http_proxy_info = OSAL().GetHTTPProxyInfo()
    except errors.OSALError:
        logger.error("Error: OSAL().GetHTTPProxyInfo()")
        return web.json_response({"http_proxy": httpProxy, "user": httpProxyUser})
    httpProxy = http_proxy_info.response.http_proxy
    httpProxyUser = http_proxy_info.response.user
    return web.json_response({"http_proxy": httpProxy, "user": httpProxyUser})


@app.http_post("/api/http-proxy")
@app.authenticated
async def configureHTTPProxy(request):
    data = await request.json()
    httpProxy = data.get("httpproxy", None)
    user = data.get("user", None)
    password = data.get("password", None)

    if httpProxy is not None:
        app.execute_osal("SetHTTPProxy", httpProxy, user, password)
        return web.Response()
    return web.Response(text="Internal Error: HTTP Proxy is undefined", status=400)


@app.http_get("/api/screenshot")
@app.authenticated
async def screenshot(request):
    ret = app.execute_osal("TakeScreenshot", "")
    fname = ret.response.filename
    if fname is None or not fname:
        return web.Response(text=str(ret), status=500)
    directory = ret.response.directory
    if directory is None or not os.path.isdir(directory):
        directory = utils.get_src_path_mapping(directory)
        if directory is None or not os.path.isdir(directory):
            return web.Response(text=str(ret), status=500)

    if os.path.isfile(directory + "/" + fname):
        headers = {
            hdrs.CACHE_CONTROL: "no-cache, no-store, must-revalidate",
            hdrs.CONTENT_DISPOSITION: "attachment; filename=" + fname,
            hdrs.ACCEPT: "image/*",
            hdrs.CONTENT_TRANSFER_ENCODING: "binary",
            hdrs.CONTENT_TYPE: "image/png",
            hdrs.EXPIRES: "0",
            hdrs.PRAGMA: "no-cache",
        }
        resp = web.FileResponse(directory + "/" + fname, headers=headers)
        await resp.prepare(request)
        await resp.drain()
        await resp.write_eof()
        await utils.remove_file(directory + "/" + fname, logger)
        return web.Response()
    return web.Response(text="Internal Error", status=500)


@app.http_post("/api/screenshot/usb")
@app.authenticated
async def screenshotToUSB(request):
    params = await request.json()
    devname = params.get("devname", None)
    if devname is None:
        return web.Response(text="devname is None", status=400)
    app.execute_osal("TakeScreenshotToUSB", "", "", devname)
    return web.Response()


@app.http_get("/api/system/logs")
@app.authenticated
async def getSystemLogs(request):
    # filter_by = request.GET.getone("filter", "")
    lines = app.get_argument(request, "lines", None)
    try:
        lines = int(lines)
    except Exception:
        lines = 200

    if lines < 0:
        return web.HTTPBadRequest(text=f"Invalid lines: {lines}")

    # make new websocket endpoint of this function
    # RequestClientEventChannel()
    # subscribe topic

    # ret = app.osal.GetSystemLogs(filter_by, lines)
    # if ret.outcome != OSAL_OK:
    #    return web.Response(text=str(ret.errorMessage), status=500)
    logs = []
    # for line in ret.response.logEntries:
    #    logger.debug('Got log line: %s', line)
    #    logs.append(json.loads(line))
    return web.json_response(logs)


@app.http_get("/api/system/logs/containers")
@app.authenticated
async def getSystemLogsContainers(request):
    ret = app.execute_osal("GetLoggingContainerList")
    return web.json_response(list(ret.response.names))


@app.http_get("/api/system/logs/files")
@app.authenticated
async def getSystemFileLogs(request):
    ret = app.execute_osal("GetLogFileList")

    valid_prefixes = ["u:", "i:"]

    def is_valid(fname):
        return any(fname.startswith(prefix) for prefix in valid_prefixes)

    fnames = [fname for fname in ret.response.names if is_valid(fname)]
    return web.json_response(fnames)


@app.http_get("/api/system/logs/appfiles")
@app.authenticated
async def getSystemAppFileLogs(request):
    ret = app.execute_osal("GetLogFileList")

    def is_valid(fname):
        return fname.startswith("a:")

    fnames = [fname for fname in ret.response.names if is_valid(fname)]
    return web.json_response(fnames)


def get_hostname():
    try:
        with open("/etc/hostname", "r") as f:
            return f.read().rstrip("\n").strip()
    except OSError:
        return ""


def get_keyboardLayout():
    keyboard_code = 0
    try:
        keyboard_code = KeyboardLayouts().current_layout.code
    except ArithmeticError as err:
        logger.error(err)
    return keyboard_code


@app.http_get("/api/system/stats")
@app.authenticated
async def systemStats(request):
    include_processes_stats = False
    if request.GET.getone("processes", False):
        include_processes_stats = request.GET.getone("processes") == "true"

    def get_hosttype():
        try:
            efi = ""
            if os.path.isdir("/sys/firmware/efi"):
                efi = " (efi)"
            with open("/sys/devices/virtual/dmi/id/product_name", "r") as f:
                return f.read().rstrip("\n").strip() + efi
        except OSError:
            return ""

    def get_machineid():
        try:
            with open("/etc/machine-id", "r") as f:
                return f.read().rstrip("\n").strip()
        except OSError:
            return ""

    def get_serialno():
        try:
            ret = app.execute_osal("GetSerialNumber")
        except errors.OSALCallError as exc:
            if exc.retval.outcome == OSAL_NONE:
                return ""
            raise
        return ret.response.serialNumber

    def get_time() -> str:
        time_and_date_info = dt_info()
        if time_and_date_info:
            return format_dt_info(time_and_date_info)
        return ""

    def get_uptime():
        try:
            with open("/proc/uptime", "r") as f:
                uptime_str = float(f.readline().split()[0])
                uptime_str = str(timedelta(seconds=uptime_str))
                uptime_str = uptime_str.split(".")[0]
                uptime_str = uptime_str.rsplit(":", 1)[0]
                uptime_h = uptime_str.split(":")[0]
                uptime_min = uptime_str.split(":")[1]
                return uptime_h + "h " + uptime_min + "m"
        except OSError:
            return "N/A"

    def getFromList(a, ix):
        try:
            a[ix] = a[ix].strip()
            return a[ix]
        except IndexError:
            return ""

    async def getTimedate():
        timedateconfig = {}
        try:
            ret, timedatectl, _ = await run_cmd("timedatectl")
        except Exception as exc:
            logger.exception(exc)
            return {}

        if ret != 0:
            logger.error("Error getting timedate")
            return {}

        lines = timedatectl.split("\n")
        lastcfg = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if ": " in line:
                k, v = line.split(": ", 1)
                k = k.strip()
                v = v.strip()
                timedateconfig[k] = v
                lastcfg = k
            elif lastcfg is not None:
                oldval = timedateconfig[lastcfg]
                timedateconfig[lastcfg] = [oldval, line.strip()]
        return timedateconfig

    try:
        network_info = await NetworkInfo().get_info()
        timedate = await getTimedate()
        try:
            load = os.getloadavg()
        except OSError:
            load = None
        statsInfo = {
            "hostname": get_hostname(),
            "hosttype": get_hosttype(),
            "keyboard": get_keyboardLayout(),
            "machineid": get_machineid(),
            "serialno": get_serialno(),
            "ip": network_info.get("ips", [""]),
            "macaddr": network_info.get("macaddr", ""),
            "status": network_info.get("status", ""),
            "timezone": timedate.get("Time zone", ""),
            "time": get_time(),
            "ntpsync": timedate.get("System clock synchronized", ""),
            "uptime": get_uptime(),
            "cpu": psutil.cpu_percent(),
            "cpucores": cpu_count(),
            "load": load,
            "kernel_ver": platform.release(),
        }

        ret = app.osal.GetDiskFreeList()
        if ret.outcome != OSAL_OK:
            return web.Response(text=str(ret.errorMessage), status=400)

        statsDisk = []
        GB = 1024 * 1024 * 1024
        for disk in ret.response.disks:
            d = {
                "fs": disk.device,
                "fstype": disk.fsType,
                "size": str("%.2f" % (float(disk.sizeTotal / GB))),  # convert to GB
                "usage": str("%.2f" % (float(disk.sizeUsed / GB))),  # convert to GB
                "avail": str("%.2f" % (float(disk.sizeFree / GB))),  # convert to GB
                "percent": int(float(disk.sizeUsed) / float(disk.sizeTotal) * 100.0),
                "mount": disk.mountPoint,
            }
            statsDisk.append(d)

        def fs(elem):
            return elem["mount"]

        statsDisk.sort(key=fs)

        statsMem = []
        try:
            ret, output, _ = await run_cmd("free -m -w")
        except Exception as exc:
            logger.exception(exc)
        if ret != 0:
            logger.error("Error getting memory stats")
        entries = output.split("\n")
        for entry in entries:
            entry = entry.strip()
            if not entry or "total" in entry:  # skip header
                continue
            s = entry.split()
            name = getFromList(s, 0).strip()
            name = name.replace(":", "")
            if name == "Mem":
                name = "RAM"
            d = {
                "name": name,
                "total": getFromList(s, 1),
                "used": getFromList(s, 2),
                "free": getFromList(s, 3),
                "shared": getFromList(s, 4),
                "buff": getFromList(s, 5),
                "cache": getFromList(s, 6),
            }
            statsMem.append(d)

        statsProcesses = []
        if include_processes_stats:
            try:
                ret, output, _ = await run_cmd("top -b -n1 -w512")
            except Exception as exc:
                logger.exception(exc)

            if ret != 0:
                logger.error("Error getting processes stats")

            entries = output.split("\n")
            for entry in entries:
                entry = entry.strip()
                if not entry or not entry[0].isdigit():  # skip header
                    continue
                s = entry.split(maxsplit=11)
                d = {
                    "pid": getFromList(s, 0),
                    "user": getFromList(s, 1),
                    "cpu": getFromList(s, 8),
                    "mem": getFromList(s, 9),
                    "time": getFromList(s, 10),
                    "cmd": getFromList(s, 11),
                }
                statsProcesses.append(d)

        stats = {
            "sysinfo": statsInfo,
            "disks": statsDisk,
            "mem": statsMem,
            "procs": statsProcesses,
            # "cpu": {},
            # "net": {},
            # "sys": {"uptime": 0}
        }
        return web.json_response(stats)
    except Exception as exc:
        logger.exception(exc)
        return web.Response(text="Internal Error", status=500)


@app.http_get("/api/system/ipaddress")
async def getIPAddress(request):
    try:
        network_info = await NetworkInfo().get_info()
        return web.json_response(network_info.get("ip", [""]))
    except Exception as exc:
        logger.exception(exc)
        return web.Response(text="Internal Error", status=500)


@app.http_get("/api/capabilities")
async def getCapabilities(request):
    return web.json_response(app.get_capabilities())


def _get_project_name():
    """Read the project name from disk"""
    if os.path.isfile(os.path.join(ETC_DIR, "project-title")):
        with open(os.path.join(ETC_DIR, "project-title"), "r") as f:
            return f.read().rstrip("\n").strip()
    elif os.path.isfile(os.path.join(ETC_DIR, "projectinfo")):
        with open(os.path.join(ETC_DIR, "projectinfo"), "r") as f:
            # FIXME: rename to rlx-project-info, make key/value file
            return f.read().strip().split("/")[0]
    else:
        logger.info("Project info not found")
        return "N/A"


def _get_project_version():
    """Read the project version from disk"""
    if os.path.isfile(os.path.join(ETC_DIR, "project-version")):
        with open(os.path.join(ETC_DIR, "project-version"), "r") as f:
            return f.read().rstrip("\n").strip()
    else:
        logger.info("Software version not found")
        return "N/A"


def _get_rlx_version():
    """Read the RLX version or RLX project release from disk"""
    if os.path.isfile(os.path.join(ETC_DIR, "rlx-version")):
        with open(os.path.join(ETC_DIR, "rlx-version"), "r") as f:
            return f.read().rstrip("\n").strip()
    elif os.path.isfile(os.path.join(ETC_DIR, "rlx-project-release")):
        # For backward compatibility
        with open(os.path.join(ETC_DIR, "rlx-project-release"), "r") as f:
            return f.read().rstrip("\n").strip()
    else:
        logger.info("RLX version not found")
        return "N/A"


def _get_debian_version():
    """Read the Debian version from disk"""
    debian_file = "/etc/debian_version"
    if os.path.isfile(debian_file):
        with open(debian_file, "r") as f:
            return f.read().strip()
    else:
        logger.info("Debian version not found")
        return "N/A"


def _get_release_date():
    """Derive the release date from the mtime of the rlx-version file"""
    mtime_file = os.path.join(ETC_DIR, "rlx-version")

    if os.path.isfile(mtime_file):
        return format_dt_info(
            datetime.fromtimestamp(
                os.path.getmtime(mtime_file), pytz.timezone(dt_info().tz_name)
            )
        )

    return None


def _get_upgrade_status():
    """Parse the GetSoftwareUpgrade status into a dictionary"""
    ret = app.execute_osal("GetSoftwareUpgradeStatus")

    status_names = {
        0: "not-running",
        1: "in-progress",
        2: "finished",
        3: "failed",
    }

    return {
        "upgrade_status": status_names.get(ret.response.status, ""),
        "upgrade_token": ret.response.token,
        "upgrade_description": ret.response.description,
        "upgrade_duration": ret.response.upgradeDuration,
        "upgrade_estimatedDuration": ret.response.estimatedUpgradeDuration,
        "upgrade_requiredFreeDiskSpace": ret.response.requiredFreeDiskSpace,
    }


@app.http_get("/api/status")
async def get_status(request):
    """Basic status information about RLX"""
    # Basic information needed for unauthenticated requests
    status = {
        "name": _get_project_name(),
        "software_version": _get_project_version(),
        "rlx_version": _get_rlx_version(),
        "launchcode_available": app.is_launch_code_available()
        and not Path("/opt/roche/var/spool/launchcode").is_file(),
        "local": utils.is_local(request),
    }

    # The web frontend only needs the following information only for authenticated requests
    status.update(
        {
            "debian_version": _get_debian_version(),
            "release_date": _get_release_date(),
            "real_ip": utils.get_real_ip(request),
        }
    )

    status.update(_get_upgrade_status())

    return web.json_response(status)


@app.http_post("/api/sftp")
@app.authenticated
async def configureSFTP(request):
    data = await request.json()
    password = data.get("password", "")
    if not password:
        return web.Response(text="Internal Error: password", status=400)
    app.execute_osal("ConfigureSFTP", password)
    app.reset_launch_code()
    return web.Response()


@app.http_post("/api/axeda")
@app.authenticated
async def configureAxeda(request):
    data = await request.json()
    environment = data.get("environment", "")
    model = data.get("model", "")
    serial = data.get("serial", "")
    if not environment or not model or not serial:
        return web.Response(
            text="Please provide an environment, model and serial", status=400
        )
    app.execute_osal("ConfigureAxeda", environment, model, serial)
    app.reset_launch_code()
    return web.Response()


@app.http_get("/api/axeda")
@app.authenticated
async def getAxedaConfiguration(request):
    ret = app.execute_osal("GetAxedaConfiguration")
    response = {
        "environments": [str(x) for x in ret.response.environments],
        "currentConfiguration": {
            "primaryServer": ret.response.current_configuration.primary_server,
            "backupServer": ret.response.current_configuration.backup_server,
            "model": ret.response.current_configuration.model,
            "serial": ret.response.current_configuration.serial,
        },
    }
    return web.json_response(response)


@app.http_get("/api/system/services")
@app.authenticated
async def getRLXServices(request):
    try:
        ret, services, _ = await run_cmd("systemctl -t service")
    except Exception as exc:
        logger.exception(exc)
        return web.Response(text="", status=412)
    if ret != 0:
        logger.error("Error getting RLX services")
        return web.Response(text="", status=412)
    svcs = []
    for o in services.split():
        if ".service" in o:
            svcs.append(o.split()[0].strip())
    svcs = [os.path.splitext(s)[0] for s in svcs]
    # preserve some system services
    preserved = ["systemd-journald", "systemd-networkd", "systemd-timesyncd"]
    for p in preserved:
        if p not in svcs:
            preserved.remove(p)
    extra_services = rlx_web_config.get("logs", "extra_services", fallback=[])
    if extra_services:
        extra_services = extra_services.split(",")
    excluded = [
        "apparmor",
        "blk",
        "console",
        "dbus",
        "getty",
        "haveged",
        "keyboard",
        "kmod",
        "k8s_POD_",
        "lvm",
        "plymouth",
        "system",
    ]
    response = [s for s in svcs if not s.startswith(tuple(excluded))]
    response = [*response, *preserved, *extra_services]
    response.sort()
    return web.json_response(response)


async def sendevent(eventname, data):
    subject = ""
    if eventname in ["USBStorageConnected", "USBStorageDisconnected"]:
        subject = "usb"
    elif eventname in [
        "RemoteScreenRequested",
        "RemoteScreenStarted",
        "RemoteScreenStopped",
    ]:
        subject = "remoteScreen"
    elif eventname in [
        "MobileDeviceRegistered",
        "MobileDeviceDeregistered",
        "MobileDeviceConnected",
        "MobileDeviceDisconnected",
        "DisconnectAllMobileDevices",
        "DisconnectMobileDevice",
        "AccessMobileDeviceGranted",
        "AccessMobileDeviceRevoked",
        "AccessMobileDeviceRequested",
    ] and app.has_capability("web-remote-access"):
        subject = "mobileDevices"
        if eventname == "DisconnectAllMobileDevices":
            logger.info("Closing connections to all mobile devices")
            await app.close_tcp_proxy_connections(group="mobile-device")
        elif eventname == "DisconnectMobileDevice":
            logger.info(f"Closing connection to mobile device #{data['id']}")

            def isDevice(request):
                try:
                    decoded_jwt = mobile_device_helpers.get_decoded_jwt_from_cookies(
                        request
                    )
                except Exception as e:
                    logger.error(f"Failed to decode JWT token: {e}")
                    return False

                return int(decoded_jwt["sub"]) == int(data["id"])

            await app.close_tcp_proxy_connections(
                group="mobile-device", isMatching=isDevice
            )
        elif eventname == "AccessMobileDeviceGranted":
            logger.info(f"Granting access to mobile device {data['id']}")
            update_granted_status_by_id(data["id"], True)
        elif eventname == "AccessMobileDeviceRevoked":
            logger.info(f"Revoking access of mobile device {data['id']}")
            update_granted_status_by_id(data["id"], False)

    elif eventname in [
        "MaintenanceWebAccessStarted",
        "MaintenanceWebAccessStopped",
        "MaintenanceWebAccessRequested",
        "MaintenanceWebAccessGranted",
        "MaintenanceWebAccessRejected",
        "MaintenanceWebAccessRevoked",
    ] and app.has_capability("web-remote-access"):
        subject = "remoteWeb"
        if eventname != "MaintenanceWebAccessRequested":
            app.remote_access_requested = False
        if eventname == "MaintenanceWebAccessRevoked":
            app.invalidate_sessions()
            await app.close_websocket_connections()

    elif eventname == "SoftwareUpgradeFailed":
        subject = "upgrade"
    else:
        logger.warning(f"unrecognized event: {eventname}")
        return
    evt = {"subject": subject, "event": eventname}
    evt.update(data)
    await app.websocket_broadcast(evt)
