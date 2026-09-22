import os
import yaml
from aiohttp import web

from ..app_api import app, OSAL_OK, run_cmd
from ..errors import RLXWebError
from ..http_proxy import HTTPProxy, http_proxy_exists
from .env import (
    DOCKER_COMPOSE_ENV_FILE,
    DOCKER_COMPOSE_DEFAULT_ENV_FILE,
    SECRETS_MASK,
    get_docker_compose_env_vars,
    get_vars_from_env_file,
)


class safelist(list):
    def get(self, index, default=None):
        try:
            return self.__getitem__(index)
        except IndexError:
            return default


@app.http_get("/api/docker")
@app.authenticated
async def queryDocker(request):
    try:
        _, stdout, _ = await run_cmd("systemctl is-active docker")
    except Exception as exc:
        app.logger.exception(exc)
        return web.Response(text="", status=400)
    state = stdout.strip().rstrip("\n")
    if state == "active":
        return web.json_response("true")
    return web.json_response("false")


@app.http_get("/api/docker/env")
@app.authenticated
async def docker_get_env(request):
    try:
        env_vars = get_docker_compose_env_vars()
    except (OSError, yaml.YAMLError) as err:
        app.logger.error(err)
        return web.Response(text=err, status=400)
    return web.json_response(env_vars)


async def configure_docker(user_env):
    docker_env_file = DOCKER_COMPOSE_ENV_FILE

    if not os.path.exists(docker_env_file):
        docker_env_file = DOCKER_COMPOSE_DEFAULT_ENV_FILE

    env = get_vars_from_env_file(docker_env_file)

    for var, value in user_env.items():
        # Update values in the environment with the new user provided ones unless the value is masked
        if value != SECRETS_MASK:
            env[var] = value

    # Get http proxy config info and set env variables for docker
    if http_proxy_exists():
        http_proxy_info = HTTPProxy().get_unescaped_info()
        proxy_server = http_proxy_info.http_proxy
        user = http_proxy_info.user
        password = http_proxy_info.password

        if user and password:
            env["HTTP_PROXY"] = f"http://{user}:{password}@{proxy_server}"
        else:
            env["HTTP_PROXY"] = f"http://{proxy_server}"

        env["HTTPS_PROXY"] = env["HTTP_PROXY"]

    try:
        with open(DOCKER_COMPOSE_ENV_FILE, "w") as f:
            for var, value in env.items():
                f.write(f"{var}={value}\n")
    except OSError as exc:
        app.logger.exception(exc)
        raise RLXWebError("Failed to save the new docker configuration")

    fname = "/opt/roche/var/spool/.docker-compose-inactive"

    try:
        if os.path.isfile(fname) or os.path.islink(fname):
            os.remove(fname)
    except OSError as error:
        app.logger.error(f"Error removing {fname}", error)

    ret = app.osal.RestartDockerContainers()

    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=400)


@app.http_post("/api/docker/env")
@app.authenticated
async def docker_set_env(request):
    env = await request.json()
    await configure_docker(env)
    app.reset_launch_code()
    return web.Response()


@app.http_post("/api/docker/container/stop")
@app.authenticated
async def stopDockerContainers(request):
    params = await request.json()
    names = params.get("names", None)
    if names is None:
        return web.Response(text="names is None", status=400)
    if not isinstance(names, list):
        names = [names]
    ret = app.osal.StopDockerContainer(names)
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=400)
    return web.Response()


@app.http_post("/api/docker/container/start")
@app.authenticated
async def startDockerContainers(request):
    params = await request.json()
    names = params.get("names", None)
    if names is None:
        return web.Response(text="names is None", status=400)
    if not isinstance(names, list):
        names = [names]
    ret = app.osal.StartDockerContainer(names)
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=400)
    return web.Response()


@app.http_post("/api/docker/container/restart")
@app.authenticated
async def restartDockerContainers(request):
    params = await request.json()
    names = params.get("names", None)
    if names is None:
        return web.Response(text="names is None", status=400)
    if not isinstance(names, list):
        names = [names]
    ret = app.osal.RestartDockerContainer(names)
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=400)
    return web.Response()


@app.http_get("/api/docker/container/status")
@app.authenticated
async def statusDockerContainer(request):
    name = request.GET.getone("name", None)
    if name is None:
        return web.Response(text="name is None", status=400)
    ret = app.osal.GetDockerContainerStatus(name)
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=400)
    running = ret.response.running
    if not running:  # empty response
        running = "false"
    return web.json_response(running)


@app.http_get("/api/docker/stats")
@app.authenticated
async def dockerStats(request):
    include_stats = False
    if request.GET.getone("stats", False):
        include_stats = request.GET.getone("stats") == "true"
    containers = {}
    stats = {}

    def splitNumberAndUnit(s):
        for i, c in enumerate(s):
            if c == ".":
                continue
            if not c.isdigit():
                break
        number = s[:i].strip()
        unit = s[i:].strip()
        return number, unit

    def convertToBytes(number, unit="B"):
        if unit == "B":
            return number
        if unit == "kB":
            number *= 1000
        elif unit == "MB":
            number *= 1000000
        elif unit == "GB":
            number *= 1000000000
        elif unit == "TB":
            number *= 1000000000000
        elif unit == "KiB":
            number *= 1024
        elif unit == "MiB":
            number *= 1048576
        elif unit == "GiB":
            number *= 1073741824
        elif unit == "TiB":
            number *= 1099511627776
        return number

    # images = {}
    # fmt = "{{.Repository}};{{.Tag}};{{.Size}}"
    # try:
    #     output = subprocess.check_output(['docker', 'images', '-a', '--format', fmt ])
    # except subprocess.CalledProcessError:
    #     return web.Response(text="", status=412)

    # entries = str(output, "utf-8").split("\n")
    # for entry in entries:
    #     entry = entry.strip()
    #     if not entry:
    #         continue
    #     s = entry.split(";")
    #     if len(s) != 3:
    #         app.logger.error("docker images: invalid data")
    #         continue
    #     image, tag, size = s
    #     size_number, size_unit = splitNumberAndUnit(size.strip())
    #     size_number = float(size_number)
    #     size_number = convertToBytes(size_number, size_unit)
    #     p = image.split("/")
    #     name = p[-1]
    #     images["{}:{}".format(image, tag)] = (name, tag, size_number)

    # get container list and basic info
    fmt = "{{.ID}};{{.Names}};{{.Image}}"
    try:
        ret, stdout, _ = await run_cmd("docker ps -a --no-trunc --format " + fmt)
    except Exception as exc:
        app.logger.exception(exc)
        return web.Response(text="", status=412)
    if ret != 0:
        app.logger.error("Error getting docker stats")
        return web.Response(text="", status=412)

    entries = stdout.split("\n")
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        s = entry.split(";")
        if len(s) != 3:
            app.logger.error("docker ps: invalid data")
            continue
        cid, name, image = s
        ver = image.split(":")[-1]
        containers[cid] = (name, ver)

    for cid in containers:
        fmtHealth = "{{.State.Health.Status}}"
        fmt = "{{.State.Status}}"

        try:
            ret, stdout, _ = await run_cmd(
                "docker inspect " + cid + " --format " + fmtHealth, log_error=False
            )
            if ret != 0:  # fallback to default API
                ret, stdout, _ = await run_cmd(
                    "docker inspect " + cid + " --format " + fmt
                )
        except Exception as exc:
            app.logger.exception(exc)
            return web.Response(text="", status=412)
        if ret != 0:
            app.logger.error("Error getting docker stats")
            return web.Response(text="", status=412)

        status = stdout.rstrip("\n").strip()
        containers[cid] += (status,)

    if include_stats:
        fmt = "{{.ID}};{{.CPUPerc}};{{.MemUsage}};{{.NetIO}};{{.BlockIO}}"
        try:
            ret, stdout, _ = await run_cmd(
                "docker stats --no-stream --no-trunc --format " + fmt
            )
        except Exception as exc:
            app.logger.exception(exc)
            return web.Response(text="", status=412)
        if ret != 0:
            app.logger.error("Error getting docker stats")
            return web.Response(text="", status=412)

        entries = stdout.split("\n")
        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue
            s = entry.split(";")
            if len(s) != 5:
                app.logger.error("docker stats: invalid data")
                continue
            container, cpu, mem, net, block = s
            mem = mem.split("/")
            mem_usage = mem[0]
            mem_limit = mem[1]
            net = net.split("/")
            net_in = net[0]
            net_out = net[1]
            block = block.split("/")
            block_in = block[0]
            block_out = block[1]

            mem_usage_number, mem_usage_unit = splitNumberAndUnit(mem_usage.strip())
            mem_limit_number, mem_limit_unit = splitNumberAndUnit(mem_limit.strip())
            mem_usage_number = float(mem_usage_number)
            mem_usage_number = convertToBytes(mem_usage_number, mem_usage_unit)
            mem_limit_number = float(mem_limit_number)
            mem_limit_number = convertToBytes(mem_limit_number, mem_limit_unit)

            net_in_number, net_in_unit = splitNumberAndUnit(net_in.strip())
            net_out_number, net_out_unit = splitNumberAndUnit(net_out.strip())
            net_in_number = float(net_in_number)
            net_in_number = convertToBytes(net_in_number, net_in_unit)
            net_out_number = float(net_out_number)
            net_out_number = convertToBytes(net_out_number, net_out_unit)

            block_in_number, block_in_unit = splitNumberAndUnit(block_in.strip())
            block_out_number, block_out_unit = splitNumberAndUnit(block_out.strip())
            block_in_number = float(block_in_number)
            block_in_number = convertToBytes(block_in_number, block_in_unit)
            block_out_number = float(block_out_number)
            block_out_number = convertToBytes(block_out_number, block_out_unit)

            stats[container] = (
                cpu.replace("%", ""),
                mem_usage_number,
                mem_limit_number,
                net_in_number,
                net_out_number,
                block_in_number,
                block_out_number,
            )

    info = []
    for key in containers:
        stat = []
        stat.extend(containers[key])
        if key in stats:
            stat.extend(stats[key])
        stat = safelist(stat)
        ret = app.osal.GetDockerContainerStatus(key)  # key=ID is unique
        if ret.outcome != OSAL_OK:
            return web.Response(text=str(ret.errorMessage), status=400)
        running = ret.response.running
        if not running:  # empty response
            running = False
        d = {
            "name": stat.get(0),
            "version": stat.get(1),
            "status": stat.get(2),
            "cpu": stat.get(3),
            "mem_usage": stat.get(4),
            "mem_limit": stat.get(5),
            "net_in": stat.get(6),
            "net_out": stat.get(7),
            "block_in": stat.get(8),
            "block_out": stat.get(9),
            "running": running,
        }
        info.append(d)

    def name(elem):
        return elem["name"]

    info.sort(key=name)

    system = []
    fmt = "{{.Type}};{{.TotalCount}};{{.Active}};{{.Size}}"
    try:
        ret, stdout, _ = await run_cmd("docker system df --format " + fmt)
    except Exception as exc:
        app.logger.exception(exc)
        return web.Response(text="", status=412)
    if ret != 0:
        app.logger.error("Error getting docker stats")
        return web.Response(text="", status=412)

    entries = stdout.split("\n")
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        if entry.startswith("TOTAL"):  # skip header
            continue
        s = entry.split(";")
        s = safelist(s)
        total_size = s.get(3, default="").strip()
        total_size_number, total_size_unit = splitNumberAndUnit(total_size)
        total_size_number = float(total_size_number)
        # https://godoc.org/github.com/docker/go-units#HumanSize
        # https://github.com/moby/moby/blob/062f2a3eae418c07a9a18661492a1c8beaaed60a/cli/command/formatter/disk_usage.go#L197-L203
        # HumanSize is used in docker size calculation, MB=1000*KB
        total_size_number = convertToBytes(total_size_number, total_size_unit)
        d = {
            "typename": s.get(0, default="").strip(),
            "total": s.get(1, default="").strip(),
            "active": s.get(2, default="").strip(),
            "size": total_size_number,
        }
        system.append(d)

    statsAll = {"containers": info, "system": system}
    return web.json_response(statsAll)
