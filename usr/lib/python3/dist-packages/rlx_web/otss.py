import json

from aiohttp import web
from .app_api import app


@app.http_get("/api/otss")
async def getOTSSInfo(request):
    ret = app.execute_osal("GetOTSSInfo")
    return web.json_response(json.loads(ret.response.otss))
