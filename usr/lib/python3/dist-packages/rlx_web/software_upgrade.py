from .app_api import app
from .log import logger
from rlx_osal.errors import OSALError
from rlx_osal.osal import OSAL

from aiohttp import web


@app.http_get("/api/upgrade/snapshot/exists")
@app.authenticated
async def upgradeSnapshotStatus(request) -> web.Response:
    exists = False
    try:
        snapshots = OSAL().GetSystemVersionList().response.versions
        if snapshots:
            for snapshot in snapshots:
                if snapshot.systemID == 0:
                    exists = True
                    break
    except OSALError as err:
        logger.error(err)
        return web.Response(text="Internal Error", status=500)
    return web.json_response({"exists": exists})
