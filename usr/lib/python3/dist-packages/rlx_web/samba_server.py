from aiohttp import web
from .app_api import app


@app.http_post("/api/samba-server/password")
@app.authenticated
async def setSambaServerPassword(request):
    data = await request.json()
    password = data.get("password", "")
    if not password:
        return web.Response(text="Missing Data: password", status=400)
    app.execute_osal("SetSambaServerPassword", password)
    return web.Response()
