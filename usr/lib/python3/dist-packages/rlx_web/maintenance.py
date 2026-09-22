from aiohttp import web

from .app_api import app


@app.http_post("/api/maintenance")
@app.authenticated
async def configureMaintenanceWindow(request):
    data = await request.json()
    hour = data.get("hour", 4)
    minute = data.get("minute", 0)
    app.execute_osal("ConfigureMaintenanceWindow", int(hour), int(minute))
    return web.Response()


@app.http_get("/api/maintenance")
@app.authenticated
async def getMaintenanceConfiguration(request):
    ret = app.execute_osal("GetMaintenanceWindowInfo")
    response = {"hour": ret.response.hour, "minute": ret.response.minute}
    return web.json_response(response)
