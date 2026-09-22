from aiohttp import web

from .app_api import app, run_cmd
from .shared import generic_request_handler


peripherals_handler = generic_request_handler(
    "rlx_osal.plugins.usb_storage_pb2", "web-peripherals", authenticated=True
)


@app.http_get("/api/peripherals")
@peripherals_handler
async def getPeripherals(request):
    # TODO(pflanzem): The sizes should probably part of the list returned by OSAL
    async def get_device_size(uuid):
        devpath = "/dev/disk/by-uuid/" + uuid
        ret, stdout, stderr = await run_cmd("readlink " + devpath)
        if ret != 0:
            return web.Response(text=stderr, status=412)
        devpart = stdout.rstrip("\n").strip()
        devpart = devpart.split("/")[-1]
        try:
            with open("/proc/partitions", "r") as f:
                lines = f.readlines()
                for line in lines:
                    if not line:
                        continue
                    if devpart not in line:
                        continue
                    line = line.rstrip("\n").strip()
                    line = line.split()
                    if len(line) == 4:
                        return line[2]
                return ""
        except OSError as exc:
            app.logger.exception(exc)

    peripherals = {}
    ret = app.execute_osal("GetUSBStorageList")
    usb_storage = []
    for device in ret.response.devices:
        size = float(await get_device_size(device.uuid)) * 1024  # to bytes
        d = {
            "label": device.label,
            "uuid": device.uuid,
            "devname": device.devname,
            "size": str(size),
        }
        usb_storage.append(d)
    peripherals = {"usb_storage": usb_storage}
    return web.json_response(peripherals)
