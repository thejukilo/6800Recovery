import os
from .app_api import app
from rlx_osal.osal import OSAL
from aiohttp import web
from rlx_osal import OSAL_OK


@app.http_get("/api/edgeagent")
@app.authenticated
async def getEdgeAgentConfiguration(request):
    ret = OSAL().GetEdgeAgentConfiguration()
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)
    response = {
        "environment": ret.response.environment,
        "assetType": ret.response.asset_type,
        "serial": ret.response.serial,
        "serialManagedAsset": ret.response.serial_managed_asset,
    }
    return web.json_response(response)


@app.http_get("/api/edgeagent/environments")
@app.authenticated
async def getEdgeAgentEnvironments(request):
    ret = OSAL().GetEdgeAgentEnvironments()
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)
    response = {
        "environments": list(ret.response.environment),
    }
    return web.json_response(response)


@app.http_post("/api/edgeagent")
@app.authenticated
async def configureEdgeAgent(request):
    data = await request.json()
    environment = data.get("environment", None)
    assetType = data.get("assetType", None)
    serial = data.get("serial", None)
    serialManagedAsset = data.get("serialManagedAsset", None)
    offlineKey = data.get("offlineKey", None)
    if (
        not environment
        or not assetType
        or not serial
        or not offlineKey
        or not serialManagedAsset
    ):
        return web.Response(
            text="Please provide an environment, asset type, serial number, offline trusted key.",
            status=400,
        )
    if (
        not data.get("overwriteConfig")
        and os.path.exists("/opt/roche/var/lib/rea/config/trust_key.cfg")
        and os.stat("/opt/roche/var/lib/rea/config/trust_key.cfg").st_size != 0
    ):
        return web.Response(
            text="Please confirm that you will now overwrite your current configuration.",
            status=400,
        )

    ret = OSAL().ConfigureEdgeAgent(
        environment, assetType, serial, offlineKey, serialManagedAsset
    )
    if ret.outcome != OSAL_OK:
        return web.Response(text=f"ERROR: {str(ret.errorMessage)}", status=500)
    return web.Response()
