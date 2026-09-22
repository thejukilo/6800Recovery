import socket
import os
import configparser
import subprocess
import typing as T
import json

from aiohttp import web, ClientSession

from .app_api import app, run_cmd
from .errors import RLXWebError
from rlx_osal import KeyValue, OSAL_OK
from kubernetes import client
from kubernetes import config as kubernetes_config
from .configk8s import config as config_ini

from pathlib import Path


@app.http_get("/api/kubernetes")
@app.authenticated
async def queryKubernetes(request):
    try:
        _, stdout, _ = await run_cmd("systemctl is-active kubelet")
    except Exception as exc:
        app.logger.exception(exc)
        return web.Response(text="", status=500)
    state = stdout.strip().rstrip("\n")
    if state == "active":
        return web.json_response("true")
    return web.json_response("false")


def get_config_from_ini(section: str) -> T.List[T.Dict[str, T.Union[bool, str]]]:
    out = []  # type: T.List[T.Dict[str, T.Union[bool, str]]]
    if not config_ini.has_section(section):
        return out
    opts = config_ini.options(section)
    for o in opts:
        if o.endswith("_name"):
            entry: T.Dict[str, T.Union[bool, str]] = {}
            var_id = o.split("_")[0]  # "var_id" = var05
            entry["id"] = var_id[3:]  # "id" = 05
            entry["name"] = config_ini.get(section, o)  # "name": "site.name"
            entry["label"] = config_ini.get(
                section, f"{var_id}_label", fallback=entry["name"]
            )  # "label": "Site Name"
            entry["type"] = config_ini.get(
                section, f"{var_id}_type", fallback="text"
            )  # "type": "text"
            entry["default"] = config_ini.get(
                section, f"{var_id}_default", fallback=""
            )  # "default": ""
            entry["required"] = config_ini.getboolean(
                section, f"{var_id}_required", fallback=True
            )  # "required": False
            entry["validator"] = config_ini.get(
                section, f"{var_id}_validator", fallback=""
            )
            entry["example"] = config_ini.get(section, f"{var_id}_example", fallback="")
            if entry["type"] == "select":
                entry["vals"] = json.loads(
                    config_ini.get(section, f"{var_id}_values", fallback="{}")
                )
            out.append(entry)
    return (
        out  # out = {{"name": "site.name", "label": "Site Name", ...}, {"name": ...} }
    )


def read_setup():
    setup = {}
    if os.path.isfile("/opt/roche/etc/rlx-kubernetes/setup.ini"):
        try:
            with open("/opt/roche/etc/rlx-kubernetes/setup.ini", "r") as f:
                lines = f.read()
                lines = lines.split("\n")
                for line in lines:
                    if not line:
                        continue
                    k, v = line.split("=", 1)
                    if "password" in k.lower() or "secret" in k.lower():
                        setup[k] = {"value": ""}  # "password": {"value": ""}
                    else:
                        setup[k] = {"value": v}  # "site.description": {"value": "RTK"}
        except OSError as exc:
            app.logger.exception(exc)
            pass
    if os.path.isfile("/opt/roche/etc/rlx-kubernetes/rlx-kubernetes.ini"):
        try:
            rlx_kubernetes_ini = get_config_from_ini("kubernetes")
            d = {}
            for (
                entry
            ) in (
                rlx_kubernetes_ini
            ):  # {"name": "site.description", "label": "Site Description", ...}
                d = {
                    "id": entry["id"],  # "var number"
                    "label": entry["label"],  # "Site Description"
                    "type": entry["type"],  # text / string / select / number / password
                    "default": entry["default"],
                    "required": entry["required"],
                    "validator": entry["validator"],
                    "example": entry["example"],
                    **(
                        {"vals": entry["vals"]} if entry["type"] == "select" else {}
                    ),  # _values = {}
                }
                if entry["name"] not in setup:  # "site.description"
                    setup[entry["name"]] = {
                        "value": ""
                    }  # "site.description": {"value": ""}
                id_key = f"{entry['id']}_{entry['name']}"  # "05_site.description"
                setup[id_key] = setup.pop(entry["name"])
                setup[id_key].update(d)

        except OSError as exc:
            app.logger.exception(exc)
            pass
    return setup


def read_nodes():
    try:
        kubernetes_config.load_kube_config()
    except kubernetes_config.ConfigException:
        app.logger.exception("Could not configure kubernetes python client")

    v1 = client.CoreV1Api()
    pod_list = v1.list_pod_for_all_namespaces(watch=False).items
    node_list = v1.list_node(watch=False).items

    nodes = []
    for n in node_list:
        for s in n.status.addresses:
            if s.type == "InternalIP":
                ip = s.address
        for s in n.status.conditions:
            if s.type == "Ready":
                state = "not ready"
                if s.reason == "KubeletReady":
                    state = "ready"
        roles = []
        if (
            "node-role.kubernetes.io/master" in n.metadata.labels
        ):  # for backward compatibility as k8s 1.24.x doe snot use master label anymore
            roles.append("master")
        if "node-role.kubernetes.io/control-plane" in n.metadata.labels:
            roles.append("control-plane")
        if not roles:
            roles = ["worker"]  # default

        node_name = n.metadata.name
        try:
            output = subprocess.check_output(
                ["kubectl", "top", "node", node_name, "--no-headers"]
            )
        except subprocess.CalledProcessError:
            output = None

        cpu_usage_percent = ""
        mem_usage_percent = ""
        if output is not None:
            entries = str(output, "utf-8").split()
            cpu_usage_percent = entries[2]
            mem_usage_percent = entries[4]

        total_pods = sum([1 for pod in pod_list if pod.spec.node_name == node_name])
        ready_pods = []
        for pod in pod_list:
            if pod.spec.node_name == node_name:
                for s in pod.status.conditions:
                    if s.type == "Ready":
                        if s.status == "True":
                            ready_pods.append(1)

        ready_pods = sum(ready_pods)

        node = {
            "ip": ip,
            "name": node_name,
            "state": state,
            "roles": roles,
            "total_pods": total_pods,
            "ready_pods": ready_pods,
            "cpu": cpu_usage_percent,
            "memory": mem_usage_percent,
        }
        nodes.append(node)

    return nodes


@app.http_get("/api/kubernetes/env")
@app.authenticated
async def kubernetes_get_env(request):
    ret = app.execute_osal("GetKubernetesStatus")
    initialized = ret.response.initialized
    nodes = read_nodes() if initialized else []

    canJoin = True
    if os.path.exists("/etc/kubernetes/kubelet.conf"):
        canJoin = False
        initialized = True

    config = {
        "wasInitialized": initialized,
        "setup": read_setup(),
        "nodes": nodes,
        "canJoin": canJoin,
    }
    return web.json_response(config)


@app.http_get("/api/kubernetes/master")
@app.authenticated
async def kubernetes_ismaster(request):
    isMaster = os.path.exists("/opt/roche/etc/rlx-kubernetes/.installed")
    return web.json_response(isMaster)


async def configure_kubernetes(settings):
    config = []

    try:
        for k, v in settings.items():
            config.append(KeyValue(key=k, value=v))
        app.osal.InitializeKubernetes(config, background=True)
    except OSError as exc:
        app.logger.exception(exc)
        raise RLXWebError("cannot save kubernetes configuration")


@app.http_post("/api/kubernetes/env")
@app.authenticated
async def kubernetes_set_env(request):
    env = await request.json()
    config = []

    try:
        for k, v in env.items():
            if k[0].isdigit():
                stripped_key = k[3:]  # Strip the first 3 chars from the key (01_)
            else:
                stripped_key = k
            config.append(KeyValue(key=stripped_key, value=v))
        app.osal.InitializeKubernetes(config, background=True)
        app.reset_launch_code()
    except OSError as exc:
        app.logger.exception(exc)
        raise RLXWebError("cannot save kubernetes configuration")

    return web.Response()


@app.http_post("/api/kubernetes/joincluster")
async def kubernetes_joincluster(request):
    env = await request.json()
    # FIXME error handling

    # FIXME check for all other nodes too
    if env["masterhostname"] == socket.gethostname():
        return web.Response(
            text="Error hostname of worker node must be unique in k8s cluster",
            status=409,
        )

    pin = ""
    try:
        with open("/opt/roche/var/tmp/pinfile", "r") as f:
            pin = f.read().rstrip("\n")
    except OSError:
        return web.Response(text="Error reading pin file", status=412)
    if not pin:
        return web.Response(text="Error empty pin", status=412)
    Path("/opt/roche/var/tmp/pinfile").unlink()

    app.execute_osal(
        "JoinKubernetesCluster",
        env["ip"],
        int(env["port"]),
        env["token"],
        env["hash"],
        env["sshkey"],
        pin,
        env["masternodename"],
    )
    return web.Response()


async def add_k8s_node(ip: str, joinInfo: dict) -> bool:
    async with ClientSession() as session:
        url = f"http://{ip}/rlx/api/kubernetes/joincluster"
        async with session.post(url, json=joinInfo) as response:
            if response.status != 200:
                app.logger.error(
                    "{}: {}".format(
                        "Error while adding node to k8s cluster", await response.text()
                    )
                )
                raise web.HTTPBadGateway(
                    text=f"Error while adding node to k8s cluster: status={response.status}"
                )
            return True
    return False


@app.http_post("/api/kubernetes/joinnode")
@app.authenticated
async def kubernetes_addnode(request):
    env = await request.json()
    # FIXME error handling
    pin = env["pin"]
    ip = env["ip"]
    ret = app.execute_osal("GetJoinInfo", pin)
    d = {
        "ip": ret.response.ip,
        "port": ret.response.port,
        "token": ret.response.token,
        "hash": ret.response.hash,
        "sshkey": ret.response.sshkey,
        "masternodename": ret.response.masternodename,
        "masterhostname": socket.gethostname(),
    }

    res = await add_k8s_node(ip, d)
    if not res:
        return web.Response(text="Error adding node to k8s cluster", status=412)

    ret = app.execute_osal("ConfigureWorkerNodeInCluster", ip)

    return web.Response()


@app.http_get("/api/kubernetes/pods")
@app.authenticated
async def kubernetes_pods(request):
    try:
        kubernetes_config.load_kube_config()
    except kubernetes_config.ConfigException:
        app.logger.exception("Could not configure kubernetes python client")

    v1 = client.CoreV1Api()
    pods = []
    ret = v1.list_pod_for_all_namespaces(watch=False)
    for i in ret.items:
        restarts = 0
        ready = 0
        if i.status.container_statuses and isinstance(
            i.status.container_statuses, list
        ):
            for s in i.status.container_statuses:
                restarts += s.restart_count
                ready += int(s.ready)

        pods.append(
            {
                "name": i.metadata.name,
                "ip": i.status.host_ip,
                "node": i.spec.node_name,
                "namespace": i.metadata.namespace,
                "status": i.status.phase,
                "restarts": restarts,
                "ready": ready,
                "containers": len(i.spec.containers),
            }
        )
    return web.json_response(pods)


@app.http_post("/api/kubernetes/pod/delete")
@app.authenticated
async def deleteKubernetesPod(request):
    params = await request.json()
    name = params.get("name", None)
    if name is None:
        return web.Response(text="name is None", status=400)
    ns = params.get("ns", None)
    if ns is None:
        return web.Response(text="ns is None", status=400)
    # we do not use app.execute_osal because it does not support background yet
    ret = app.osal.DeleteKubernetesPod(name, ns, background=True)
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)
    return web.Response()


@app.http_get("/api/kubernetes/certs")
@app.authenticated
async def kubernetes_certs(request):
    ret = app.execute_osal("GetKubernetesCertsExpirationInfo")
    certsInfo = ret.response.info
    certs = []
    for cert in certsInfo:
        certs.append(
            {
                "cert": cert.cert,
                "expirationDate": cert.expirationDate,
                "residualTime": cert.residualTime,
            }
        )
    return web.json_response(certs)


@app.http_post("/api/kubernetes/certs")
@app.authenticated
async def kubernetes_renew_certs(request):
    try:
        app.osal.RenewKubernetesCerts(background=True)
    except OSError as exc:
        app.logger.exception(exc)
        raise RLXWebError("error renewing kubernetes certs")
    return web.Response()


@app.http_get("/api/kubernetes/installer/setup")
@app.authenticated
async def getInstallerSetup(request):
    INSTALLER_SETUP = "/opt/roche/etc/rlx-kubernetes/installer-setup"
    config = configparser.ConfigParser()
    config.read(INSTALLER_SETUP)
    labelText = config.get(
        "label", "text", fallback="Install Kubernetes and Software Components"
    )
    d = {"labelText": labelText}
    return web.json_response(d)
