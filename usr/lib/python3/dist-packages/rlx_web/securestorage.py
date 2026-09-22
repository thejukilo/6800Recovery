from aiohttp import web
from .app_api import app, OSAL_OK


@app.http_get("/api/secure-storage")
async def getSecureStorageStatus(request):
    ret = app.osal.GetEncryptedStorageInfo()
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=400)
    d = {
        "unlocked": ret.response.unlocked,
        "setup": ret.response.setup,
        "keepUnlockedOnReboot": ret.response.keepUnlockedOnReboot,
    }
    return web.json_response(d)


@app.http_post("/api/secure-storage/lock")
async def lockSecureStorage(request):
    ret = app.osal.LockEncryptedStorage()
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=400)
    return web.Response()


@app.http_post("/api/secure-storage/unlock")
async def unlockSecureStorage(request):
    json_data = await request.json()
    name = json_data.get("name", None)
    if not name:
        return web.Response(text="Username not found", status=412)
    password = json_data.get("pass", None)
    if not password:
        return web.Response(text="Password not found", status=412)
    keep = json_data.get("keep", False)
    ret = app.osal.UnlockEncryptedStorage(name, password, keep)
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=400)
    return web.Response()


@app.http_post("/api/secure-storage")
async def setupSecureStorage(request):
    json_data = await request.json()
    password = json_data.get("pass", None)
    if not password:
        return web.Response(text="Password not found", status=412)
    keep = json_data.get("keep", False)
    ret = app.osal.SetupEncryptedStorage(password, keep)
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=400)
    app.reset_launch_code()
    return web.Response()


async def configure_encrypted_storage(settings):
    password = app.get_param(settings, "masterPassphrase")
    keep = app.get_param(settings, "keep")
    if not password:
        app.logger.exception("Password for encrypted storage not found")
        return
    app.osal.SetupEncryptedStorage(password, keep)
