import functools
import os
import asyncio
import shlex

from aiohttp import web
from pathlib import Path

from .app_api import app, run_cmd
from .config import config
from .shared import generic_request_handler


DEFAULT_RANCHER_IMAGE = (
    "registry.lni.anywhere.navify.com/docker.io/" "rancher/rancher-agent:v2.5.7"
)


CONFIGURE_CLUSTER_FNAME = "/opt/roche/home/configure-cluster.started"


cluster_handler = generic_request_handler(capability="web-cluster", authenticated=True)


@app.http_get("/api/cluster")
@cluster_handler
async def statusCluster(request):
    rancher_image = config.get("rancher", "image", fallback=DEFAULT_RANCHER_IMAGE)
    if not os.path.isfile(CONFIGURE_CLUSTER_FNAME):
        return web.json_response({"wasStarted": False, "rancherImage": rancher_image})

    try:
        with open(CONFIGURE_CLUSTER_FNAME, "r") as f:
            configdata = f.read()
    except OSError:
        return web.Response(
            text="Internal Error: cannot read configure-cluster.started", status=500
        )
    d = {
        "wasStarted": True,
        "etcd": False,
        "workernode": False,
        "controlplane": False,
        "rancherImage": rancher_image,
    }
    lines = configdata.split("\n")
    for line in lines:
        line = line.strip()
        if not line or line[0] == "#":
            continue
        if line.startswith("ENDPOINT="):
            line_split = line.split("=")
            d["endpoint"] = line_split[1].strip()
        elif line.startswith("TOKEN="):
            line_split = line.split("=")
            d["token"] = line_split[1].strip()
        elif line.startswith("CACHECKSUM="):
            line_split = line.split("=")
            d["cachecksum"] = line_split[1].strip()
        elif line.startswith("ETCD="):
            line_split = line.split("=")
            if line_split[1].strip() == "true":
                d["etcd"] = True
        elif line.startswith("WORKERNODE="):
            line_split = line.split("=")
            if line_split[1].strip() == "true":
                d["workernode"] = True
        elif line.startswith("CONTROLPLANE="):
            line_split = line.split("=")
            if line_split[1].strip() == "true":
                d["controlplane"] = True
        elif line.startswith("RANCHER_IMAGE="):
            line_split = line.split("=")
            d["rancherImage"] = line_split[1].strip()
    return web.json_response(d)


@app.http_post("/api/cluster")
@cluster_handler
async def configureCluster(request):
    settings = await request.json()
    await configure_cluster(settings)
    app.reset_launch_code()
    return web.Response()


async def configure_cluster(settings):
    # endpoint and token are required params
    endpoint = app.get_param(settings, "endpoint")
    token = app.get_param(settings, "token")
    # The other params are not required
    cachecksum = app.get_param(settings, "cachecksum", "")
    etcd = app.get_param(settings, "etcd", "")
    workernode = app.get_param(settings, "workernode", "")
    controlplane = app.get_param(settings, "controlplane", "")
    rancher_image = app.get_param(settings, "rancherImage", "")

    use_etcd = ""
    etcd_str = "false"
    if etcd:
        use_etcd = " --etcd"
        etcd_str = "true"
    use_workernode = ""
    workernode_str = "false"
    if workernode:
        use_workernode = " --worker"
        workernode_str = "true"
    use_controlplane = ""
    controlplane_str = "false"
    if controlplane:
        use_controlplane = " --controlplane"
        controlplane_str = "true"
    use_cachecksum = ""
    if cachecksum:
        use_cachecksum = " --ca-checksum " + shlex.quote(cachecksum)

    if not rancher_image:  # if not defined in web interface use config file
        rancher_image = config.get("rancher", "image", fallback=DEFAULT_RANCHER_IMAGE)
    with open(CONFIGURE_CLUSTER_FNAME, "w") as f:
        f.write("ENDPOINT=" + endpoint + "\n")
        f.write("TOKEN=" + token + "\n")
        f.write("CACHECKSUM=" + cachecksum + "\n")
        f.write("ETCD=" + etcd_str + "\n")
        f.write("WORKERNODE=" + workernode_str + "\n")
        f.write("CONTROLPLANE=" + controlplane_str + "\n")
        f.write("RANCHER_IMAGE=" + rancher_image + "\n")

    cmd = (
        f"docker run -d --privileged --restart=unless-stopped --net=host "
        f"-v /etc/kubernetes:/etc/kubernetes -v /var/run:/var/run "
        f"--name rancher-agent {shlex.quote(rancher_image)} --server {shlex.quote(endpoint)} "
        f"--token {shlex.quote(token)} {use_cachecksum} {use_etcd} {use_workernode} "
        f"{use_controlplane}"
    ).strip()

    def reset_cluster():
        try:
            Path(CONFIGURE_CLUSTER_FNAME).unlink()
        except Exception as exc:
            app.logger.exception(exc)

    async def docker_run(cmd):
        app.logger.info("configuring cluster")
        ret, stdout, stderr = await run_cmd(cmd)
        if ret != 0:
            reset_cluster()
            app.logger.error("configuring cluster failed: %s" % stderr)
        app.logger.info("finished configuring cluster")

    asyncio.ensure_future(docker_run(cmd))
