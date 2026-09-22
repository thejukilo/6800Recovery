from aiohttp import web
import shutil

from .app_api import app
from rlx_osal.osal import OSAL
from rlx_osal.errors import OSALError, UnknownOSALMethodError
from .log import logger


@app.http_upload("/api/nst/upload", upload_dir="/opt/roche/var/tmp")
@app.authenticated
async def tar_file_upload(request, tempfile, filename, size):
    if not filename.endswith(".tar.gz"):
        return web.Response(text="Wrong file format", status=415)
    shutil.move(tempfile, "/opt/roche/var/spool/nst-driver.tar.gz")
    try:
        OSAL().NSTInstallDriver()
    except (UnknownOSALMethodError, OSALError) as err:
        logger.error(err)
    return web.Response()


@app.http_get("/api/nst/driver/info")
@app.authenticated
async def get_driver_info(resquest) -> web.Response:
    try:
        r = OSAL().GetNSTDriverInfo().response
        driver_info = {
            "name": r.name,
            "customer": r.customer,
            "version": r.version,
            "description": r.description,
        }
    except OSALError as err:
        logger.error(err)
        return web.Response(text="Internal Error", status=500)
    return web.json_response(driver_info)
