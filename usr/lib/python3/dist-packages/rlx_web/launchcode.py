import typing as T
import shlex

import aiohttp
from .app_api import app
from .config import config
from .cluster import configure_cluster
from .docker.api import configure_docker
from .kubernetes import configure_kubernetes
from .openvpn import configure_openvpn
from .securestorage import configure_encrypted_storage
from rlx_osal.osal import OSAL
from rlx_osal import OSAL_OK
from .http_proxy import HTTPProxy, HTTPProxyInfo, http_proxy_exists
from typing import Optional, Dict


LaunchCode = T.Dict[str, T.Any]


@app.http_post("/api/launch-code")
async def processLaunchCode(request):
    if not app.is_launch_code_available():
        raise aiohttp.web.HTTPBadRequest(text="Launch Code: already configured")
    json_data = await request.json()
    launch_code = json_data.get("code")
    data = await fetch_launch_code(launch_code)
    try:
        await process_lc(data)
    except Exception:
        app.logger.exception("Error processing launch code")
        raise aiohttp.web.HTTPInternalServerError(text="Error processing launch code")
    return aiohttp.web.Response()


def get_launchcode_url(launch_code: str) -> Optional[str]:
    url_tmpl = config.get("launch-code", "url", fallback=None)
    if url_tmpl is None:
        raise aiohttp.web.HTTPNotImplemented(text="Launch code url not configured")
    return f"{url_tmpl}/{launch_code}"


def get_http_proxy_info() -> Optional[HTTPProxyInfo]:
    http_proxy = HTTPProxy()
    http_proxy_info = http_proxy.get_unescaped_info()
    http_proxy = http_proxy_info.http_proxy
    return http_proxy_info


def get_session_args(launch_code: str) -> Dict:
    session_args = {"ssl": True}
    session_args["url"] = get_launchcode_url(launch_code)
    if http_proxy_exists():
        http_proxy_info = get_http_proxy_info()
        session_args["proxy"] = f"http://{http_proxy_info.http_proxy}"
        if http_proxy_info.user and http_proxy_info.password:
            session_args["proxy_auth"] = aiohttp.BasicAuth(
                http_proxy_info.user, http_proxy_info.password
            )
    return session_args


async def fetch_launch_code(launch_code: str) -> LaunchCode:
    async with aiohttp.ClientSession() as session:
        session_args = get_session_args(launch_code)
        async with session.get(**session_args) as response:
            if response.status != 200:
                app.logger.error(
                    "{}: {}".format(
                        "Error while getting launch code", await response.text()
                    )
                )
                raise aiohttp.web.HTTPBadGateway(
                    text=f"Error while getting launch code: status={response.status}"
                )
            return await response.json()


async def process_lc(data: LaunchCode) -> None:
    # must be first as kubernetes may depend on secure storage
    if "encryptedStorage" in data.keys():
        try:
            await configure_encrypted_storage(data["encryptedStorage"])
        except Exception:
            raise aiohttp.web.HTTPInternalServerError(
                text="Launch Code: cannot configure encrypted storage"
            )
    if "sftp" in data.keys():
        password = data["sftp"].get("password", "")
        app.execute_osal("ConfigureSFTP", password)
    if "cluster" in data.keys():
        try:
            await configure_cluster(data["cluster"])
        except Exception:
            raise aiohttp.web.HTTPInternalServerError(
                text="Launch Code: cannot configure cluster"
            )
    if "axeda" in data.keys():
        environment = data["axeda"].get("environment", "")
        model = data["axeda"].get("model", "")
        serial = data["axeda"].get("serial", "")
        app.execute_osal("ConfigureAxeda", environment, model, serial)
    if "openvpn" in data.keys():
        try:
            await configure_openvpn(data["openvpn"])
        except Exception:
            raise aiohttp.web.HTTPInternalServerError(
                text="Launch Code: cannot configure openvpn"
            )
    if "kubernetes" in data.keys():
        try:
            await configure_kubernetes(data["kubernetes"])
        except Exception:
            raise aiohttp.web.HTTPInternalServerError(
                text="Launch Code: cannot configure kubernetes"
            )
    if "docker" in data.keys():
        try:
            await configure_docker(data["docker"])
        except Exception:
            raise aiohttp.web.HTTPInternalServerError(
                text="Launch Code: cannot configure docker"
            )
    if "sambaserver" in data.keys():
        password = data["sambaserver"].get("password", None)
        if password:
            try:
                OSAL().SetSambaServerPassword(password)
            except Exception:
                raise aiohttp.web.HTTPInternalServerError(
                    text="Launch Code: cannot configure SMB server"
                )
    if "network" in data.keys():
        for netif in data["network"]:
            usedhcp = netif.get("usedhcp", False)
            ipaddresses = netif.get("ipaddresses", [])
            netmask = netif.get("netmask", 24)
            gateway = netif.get("gateway", "")
            dns = netif.get("dns", "")
            dns2 = netif.get("dns2", "")
            iface = netif.get("iface", "")
            usentp = netif.get("usentp", False)
            role = netif.get("role", "")
            if usedhcp or ipaddresses:
                app.execute_osal(
                    "ConfigureNetworkInterface",
                    usedhcp,
                    ipaddresses,
                    netmask,
                    gateway,
                    dns,
                    dns2,
                    "",
                    iface,
                    usentp,
                    role,
                )
    if "hostname" in data.keys():
        try:
            hostname = data["hostname"].get("hostname", "")
            app.execute_osal("SetHostname", hostname)
        except Exception:
            raise aiohttp.web.HTTPInternalServerError(
                text="Launch Code: cannot configure hostname"
            )
    if "http_proxy" in data.keys():
        proxy_server = data["http_proxy"].get("proxy_server", "")
        proxy_user = data["http_proxy"].get("proxy_user", "")
        proxy_password = data["http_proxy"].get("proxy_password", "")
        app.execute_osal("SetHTTPProxy", proxy_server, proxy_user, proxy_password)
    if "ntp" in data.keys():
        ntp_server = data["ntp"].get("ntp_server", "").split(",")
        fallback_server = data["ntp"].get("fallback_server", "").split(",")
        app.execute_osal("SetNTPServers", ntp_server, fallback_server)
    if "navify" in data.keys():
        image_name = shlex.quote(data["navify"].get("image_name", ""))
        args = data["navify"].get("args", [])
        if "http_proxy" in data.keys():
            proxy_server = data["http_proxy"].get("proxy_server", "")
            proxy_user = data["http_proxy"].get("proxy_user", "")
            proxy_password = data["http_proxy"].get("proxy_password", "")
            if proxy_user and proxy_password:
                http_proxy = f"http://{proxy_user}:{proxy_password}@{proxy_server}"
            else:
                http_proxy = f"http://{proxy_server}"
            # we do not use app.execute_osal because it does not support background yet
            ret = app.osal.StartNavifyDocker(
                http_proxy, image_name, args, background=True
            )
            if ret.outcome != OSAL_OK:
                return aiohttp.web.Response(text=str(ret.errorMessage), status=500)
        else:
            ret = app.osal.StartNavifyDocker("", image_name, args, background=True)
            if ret.outcome != OSAL_OK:
                return aiohttp.web.Response(text=str(ret.errorMessage), status=500)
    app.reset_launch_code()
