from aiohttp import web
from http import HTTPStatus

from ..app_api import app, OSAL_OK
from ..utils import is_local


@app.http_get("/api/remote-screen/status")
@app.authenticated
async def getRemoteScreenStatus(request):
    ret = app.osal.GetRemoteScreenStatus()

    if ret.outcome != OSAL_OK:
        return web.Response(
            text=str(ret.errorMessage), status=HTTPStatus.INTERNAL_SERVER_ERROR
        )

    return web.json_response({"running": ret.response.running})


@app.http_post("/api/remote-screen")
@app.authenticated
async def startRemoteScreen(request):
    ret = app.osal.StartRemoteScreen(request.cirrina.web_session["username"])

    if ret.outcome != OSAL_OK:
        return web.Response(
            text=str(ret.errorMessage), status=HTTPStatus.INTERNAL_SERVER_ERROR
        )

    return web.Response(status=HTTPStatus.OK)


@app.http_post("/api/remote-screen-local")
async def startRemoteScreenLocal(request):
    if not is_local(request):
        return web.Response(status=HTTPStatus.FORBIDDEN)

    ret = app.osal.StartRemoteScreen("localuser")

    if ret.outcome != OSAL_OK:
        return web.Response(
            text=str(ret.errorMessage), status=HTTPStatus.INTERNAL_SERVER_ERROR
        )

    return web.Response(status=HTTPStatus.OK)


@app.http_delete("/api/remote-screen")
@app.authenticated
async def stopRemoteScreen(request):
    ret = app.osal.StopRemoteScreen(request.cirrina.web_session["username"])

    if ret.outcome != OSAL_OK:
        return web.Response(
            text=str(ret.errorMessage), status=HTTPStatus.INTERNAL_SERVER_ERROR
        )

    return web.Response(status=HTTPStatus.OK)


@app.http_post("/api/remote-screen/request")
@app.authenticated
async def requestRemoteScreen(request):
    ret = app.osal.RequestRemoteScreen(request.cirrina.web_session["username"])

    if ret.outcome != OSAL_OK:
        return web.Response(
            text=str(ret.errorMessage), status=HTTPStatus.INTERNAL_SERVER_ERROR
        )

    return web.Response(status=HTTPStatus.OK)


@app.tcp_proxy_setup(
    "/api/remote-screen",
    group="remote-screen",
    authenticated=True,
    host="127.0.0.1",
    port=5900,
)
async def setup_remote_screen(_request: web.Request):
    """Init VNC connection"""
    pass
