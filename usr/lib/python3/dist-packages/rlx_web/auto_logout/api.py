from aiohttp import web
import functools
from rlx_web.app_api import app

from .helpers import get_auto_logout_timeout, update_last_access_time
from ..shared import generic_request_handler


def __make_last_access_response(request):
    return web.json_response(
        {
            "last_access": request.cirrina.web_session.get("last_access", 0),
            "timeout": get_auto_logout_timeout(),
        }
    )


auto_logout_handler = generic_request_handler(
    capability="web-auto-logout", authenticated=False
)


@app.http_get("/api/auto-logout/last-access")
@app.authenticated
@auto_logout_handler
async def get_last_access(request):
    return __make_last_access_response(request)


@app.http_post("/api/auto-logout/last-access")
@app.authenticated
@auto_logout_handler
async def update_last_access(request):
    update_last_access_time(request.cirrina.web_session)
    return __make_last_access_response(request)
