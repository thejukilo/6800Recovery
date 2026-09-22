from functools import wraps
from json import JSONDecodeError

import pam
from aiohttp.web_response import Response, json_response
from rlx_osal import OSAL_OK

from rlx_web.app_api import app
from rlx_web.remote_access.constants import PLUGIN, CAPABILITY
from rlx_web.remote_access.remote_access_control.helpers import testing_enabled


def remote_access_handler(handler):
    """Remote access handler decorator.

    - Check if remote_access plugin exists
    - Check we have the necessary capability
    """

    @wraps(handler)
    async def wrapper(*args, **kwargs):
        app.require_plugin(PLUGIN)
        app.require_capability(CAPABILITY)
        app.read_remote_access_status()

        return await handler(*args, **kwargs)

    return wrapper


def remote_access_testing_handler(handler):
    """Remote access handler decorator for testing only endpoints.

    - Check if remote_access plugin exists
    - Check we have the necessary capability
    - Check if testing is enabled in configuration
    """

    @wraps(handler)
    async def wrapper(*args, **kwargs):
        app.require_plugin(PLUGIN)
        app.require_capability(CAPABILITY)
        app.read_remote_access_status()

        if not testing_enabled():
            return Response(status=400, text="Testing disabled")

        return await handler(*args, **kwargs)

    return wrapper


@app.http_get("/api/remote-access/status")
@remote_access_handler
async def get_remote_access_status(_request):
    """Get remote access status"""
    data = dict(
        granted=app.read_remote_access_status(),
        requested=app.remote_access_requested,
    )
    data.update(testing_enabled=testing_enabled())
    return json_response(data)


@app.http_post("/api/remote-access/request")
@remote_access_handler
async def request_remote_access(_request):
    """Request remote access"""
    if app.read_remote_access_status():
        return Response(status=400, reason="Remote web access already granted")

    try:
        params = await _request.json()
        username = params.get("username")
        password = params.get("password")
    except JSONDecodeError:
        return Response(
            status=400, reason="Missing required parameters 'username' and 'password'"
        )

    if username and password:
        if username == "roche":
            authorized = pam.authenticate(username, password)

        else:
            authorized = pam.authenticate("fsr", f"{username}:{password}")
    else:
        return Response(
            status=400,
            reason=f"Missing required parameter '{'username' if not username else 'password'}'.",
        )

    if authorized:
        ret = app.osal.RequestMaintenanceWebAccess(username)

        if ret.outcome != OSAL_OK:
            return Response(reason=str(ret.errorMessage), status=500)
        app.remote_access_requested = True
        return Response(status=202)
    else:
        return Response(status=403, reason="Invalid username or password.")


@app.http_post("/api/remote-access/grant/web")
@remote_access_testing_handler
async def grant_remote_web_access(_request):
    """Grant remote maintenance web access"""
    ret = app.osal.GrantMaintenanceWebAccess()

    if ret.outcome != OSAL_OK:
        return Response(reason=str(ret.errorMessage), status=500)

    return Response(status=200)


@app.http_post("/api/remote-access/reject/web")
@remote_access_testing_handler
async def reject_remote_web_access(_request):
    """Reject remote maintenance web access"""
    ret = app.osal.RejectMaintenanceWebAccess()

    if ret.outcome != OSAL_OK:
        return Response(reason=str(ret.errorMessage), status=500)

    return Response(status=200)


@app.http_post("/api/remote-access/revoke/web")
@remote_access_testing_handler
async def revoke_remote_web_access(_request):
    """Revoke remote maintenance web access"""
    ret = app.osal.RevokeMaintenanceWebAccess()

    if ret.outcome != OSAL_OK:
        return Response(reason=str(ret.errorMessage), status=500)

    return Response(status=200)


@app.http_post("/api/remote-access/grant/shell")
@remote_access_testing_handler
async def grant_remote_shell_access(_request):
    """Grant shell access"""
    ret = app.osal.GrantShellAccess()

    if ret.outcome != OSAL_OK:
        return Response(reason=str(ret.errorMessage), status=500)

    return Response(status=200)


@app.http_post("/api/remote-access/reject/shell")
@remote_access_testing_handler
async def reject_remote_shell_access(_request):
    """Reject shell access"""
    ret = app.osal.RejectShellAccess()

    if ret.outcome != OSAL_OK:
        return Response(reason=str(ret.errorMessage), status=500)

    return Response(status=200)


@app.http_post("/api/remote-access/revoke/shell")
@remote_access_testing_handler
async def revoke_remote_shell_access(_request):
    """Revoke shell access"""
    ret = app.osal.RevokeShellAccess()

    if ret.outcome != OSAL_OK:
        return Response(reason=str(ret.errorMessage), status=500)

    return Response(status=200)
