from aiohttp import web
import functools
from http import HTTPStatus

from ..app_api import app
from ..config import config
from ..log import logger
from ..shared import generic_request_handler

CAPABILITY = "web-external-remote-screen"


external_remote_screen_handler = generic_request_handler(
    capability=CAPABILITY, authenticated=False
)


@app.http_get("/api/external-remote-screen/info")
@external_remote_screen_handler
@app.authenticated
async def getRemoteScreenInfo(request):
    try:
        return web.json_response(
            {
                "name": config["external-remote-screen"]["name"],
                "host": config["external-remote-screen"]["host"],
                "port": config["external-remote-screen"].getint("port"),
            }
        )
    except KeyError:
        return web.Response(status=HTTPStatus.NOT_FOUND)


# FIXME: Once there is a way to mock this call it should be re-enabled to avoid
# unnecessary warnings and the warning should be changed to an error
# if app.has_capability(CAPABILITY):

try:

    @app.tcp_proxy_setup(
        "/api/external-remote-screen",
        group="external-remote-screen",
        authenticated=True,
        host=config["external-remote-screen"]["host"],
        port=config["external-remote-screen"].getint("port"),
    )
    async def setup_remote_screen(_request: web.Request):
        """Init VNC connection"""
        pass

except KeyError as e:
    if e == "external-remote-screen":
        logger.warning(f"Missing config entry: {e}")
    else:
        logger.error(f"Missing config entry: {e}")
