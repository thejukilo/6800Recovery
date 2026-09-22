from datetime import datetime, timedelta, timezone
from http import HTTPStatus
import json

from aiohttp import web, web_request
from pydantic import ValidationError
from rlx_osal import OSAL_OK, osal

from .constants import DEFAULT_DEVICE_TOKEN_LIFETIME, AUTH_TOKEN_KEY, CONFIG_PATH
from ..constants import PLUGIN, CAPABILITY
from .db import (
    session_wrapper,
    session_wrapper_async,
    select_all_devices,
    select_device,
    insert_device,
    delete_device_by_id,
    update_device_by_id,
    granted_status_by_id,
)
from .exceptions import (
    RemoteAccessAuthException,
    RemoteAccessTokenException,
    InvalidMobileDeviceException,
)
from .helpers import (
    generate_registration_jwt,
    decode_registration_jwt,
    generate_auth_token,
    get_expiry_date,
    format_validation_error,
    get_decoded_jwt_from_cookies,
    reset_registration_jwt,
)
from .models import (
    DeviceRegistrationRequest,
    Device,
    DeviceDeleteRequest,
    DeviceUpdateData,
    DeviceUpdateParams,
)
from rlx_web.app_api import app
from rlx_web.log import logger
from rlx_web.utils import get_real_ip
from ...config import config as rlx_web_config
from ...shared import generic_request_handler


remote_access_handler = generic_request_handler(
    plugin=PLUGIN, capability=CAPABILITY, authenticated=False
)


def require_remote_access(request: web.Request):
    """
    Decorator that checks whether remote access plugin and capability is available
    and ensures that client is authorized to make the request
    """
    request.app.require_plugin(PLUGIN)
    request.app.require_capability(CAPABILITY)

    decoded_jwt = get_decoded_jwt_from_cookies(request)
    device = select_device(int(decoded_jwt["sub"]))

    if not device:
        raise RemoteAccessAuthException("Device not registered")

    if not device.granted:
        raise RemoteAccessAuthException("Device access not granted")


def remote_access_auth_handler(request: web.Request):
    try:
        require_remote_access(request)
        return True
    except Exception as e:
        logger.error(f"Remote access denied: {e}")
        return False


@app.http_get("/api/remote-access/mobile-device/config")
@app.authenticated
@remote_access_handler
@session_wrapper_async
async def get_mobile_device_config(_request: web.Request) -> web.Response:
    """Get configuration information for the mobile device API"""
    try:
        with open(CONFIG_PATH) as fd:
            return web.json_response(json.load(fd))
    except OSError as e:
        logger.error(e)
        return web.Response(
            status=HTTPStatus.NOT_FOUND,
            reason="Missing mobile device configuration",
        )
    except json.JSONDecodeError as e:
        logger.error(e)
        return web.Response(
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            reason="Invalid mobile device configuration",
            text=e,
        )


@app.http_put("/api/remote-access/mobile-device/config")
@app.authenticated
@remote_access_handler
@session_wrapper_async
async def set_mobile_device_config(request: web.Request) -> web.Response:
    """Set configuration information for the mobile device API"""
    try:
        data = await request.json()
        config = {k: data[k] for k in ["server"]}
    except KeyError as e:
        logger.error(f"Missing value for key: {e}")
        return web.Response(
            status=HTTPStatus.BAD_REQUEST,
            reason=f"Missing setting for {e}",
        )
    except (TypeError, json.JSONDecodeError) as e:
        logger.error(e)
        return web.Response(
            status=HTTPStatus.BAD_REQUEST,
            reason="Invalid JSON request body",
        )

    try:
        with open(CONFIG_PATH, "w") as fd:
            json.dump(config, fd)
    except OSError as e:
        logger.error(e)
        return web.Response(
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            reason="Failed to write mobile device configuration",
        )
    except Exception as e:
        logger.error(e)
        return web.Response(
            status=HTTPStatus.INTERNAL_SERVER_ERROR, reason="Unknown failure", text=e
        )

    return web.Response(status=HTTPStatus.CREATED)


@app.http_get("/api/remote-access/mobile-device")
@app.authenticated
@remote_access_handler
async def get_registered_mobile_devices(_request: web.Request) -> web.Response:
    """Get a list of registered mobile devices"""
    data = select_all_devices()
    return web.json_response(data)


@app.http_post("/api/remote-access/mobile-device/register")
@remote_access_handler
@session_wrapper_async
async def register_device(request: web_request.Request) -> web.Response:
    """Register a new mobile device"""
    try:
        data = DeviceRegistrationRequest(**await request.json())
        decoded_jwt = decode_registration_jwt(data.token)

        max_age = timedelta(
            days=rlx_web_config.getint(
                "remote-access-mobile-device",
                "device_token_lifetime",
                fallback=DEFAULT_DEVICE_TOKEN_LIFETIME,
            )
        )
        exp_date = get_expiry_date(max_age)

        new_device = Device(
            name=data.name,
            ip=get_real_ip(request),
            valid_until=exp_date,
            registration_date=datetime.now(timezone.utc),
            otp=decoded_jwt["otp"],
        )

        # insert device into database
        try:
            insert_device(new_device)
        except InvalidMobileDeviceException as e:
            return web.Response(status=HTTPStatus.CONFLICT, reason=e.reason)

        reset_registration_jwt()

        # send OSAL event
        osal_response: osal.Response = app.execute_osal(
            "NotifyMobileDeviceRegistered",
            new_device.id,
            decoded_jwt["user"],
        )
        if osal_response.outcome != OSAL_OK:
            logger.error(
                f"Failed to send MobileDeviceRegistered OSAL event: {osal_response.errorMessage}"
            )
            return web.Response(
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                reason="Failed to send OSAL event",
            )

        logger.info("New mobile device registered")

        response = web.Response(status=HTTPStatus.CREATED)
        auth_token = generate_auth_token(new_device.id, exp_date)
        response.set_cookie(
            AUTH_TOKEN_KEY, auth_token, max_age=int(max_age.total_seconds())
        )
        return response

    except json.JSONDecodeError:
        return web.Response(
            status=HTTPStatus.BAD_REQUEST, reason="Missing request body"
        )

    except ValidationError as e:
        return web.json_response(
            status=HTTPStatus.BAD_REQUEST,
            reason="Received invalid data",
            data=e.errors(),
        )

    except RemoteAccessTokenException as e:
        return web.Response(status=HTTPStatus.UNAUTHORIZED, reason=e.message)


@app.http_delete("/api/remote-access/mobile-device")
@app.authenticated
@remote_access_handler
@session_wrapper_async
async def delete_mobile_device(request: web.Request) -> web.Response:
    """Delete a registered mobile device by id"""
    try:
        data = DeviceDeleteRequest(**request.query)

        if delete_device_by_id(data.id):
            osal_response: osal.Response = app.execute_osal(
                "DisconnectMobileDevice", data.id
            )

            if osal_response.outcome != OSAL_OK:
                logger.error(
                    f"Failed to disconnect mobile device: {osal_response.errorMessage}"
                )
                return web.Response(
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                    reason="Device deleted but failed to disconnect it",
                )

            osal_response: osal.Response = app.execute_osal(
                "NotifyMobileDeviceDeregistered",
                data.id,
                request.cirrina.web_session.get("username"),
            )

            if osal_response.outcome != OSAL_OK:
                logger.error(
                    f"Failed to send MobileDeviceDeregistered event: {osal_response.errorMessage}"
                )
                return web.Response(
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                    reason="Device deleted but failed to send MobileDeviceDeregistered event",
                )

            return web.Response()

        return web.Response(status=HTTPStatus.BAD_REQUEST, reason="Device not found")

    except ValidationError as e:
        return web.Response(
            status=HTTPStatus.BAD_REQUEST,
            reason=f"Invalid request parameters ({format_validation_error(e)})",
        )


@app.http_patch("/api/remote-access/mobile-device")
@app.authenticated
@remote_access_handler
@session_wrapper_async
async def update_mobile_device(request: web.Request) -> web.Response:
    """Update a registered mobile device by name"""
    try:
        params = DeviceUpdateParams(**request.query)

        if not request.can_read_body:
            return web.Response(
                status=HTTPStatus.BAD_REQUEST, reason="Missing request body"
            )

        data = DeviceUpdateData(**await request.json())
        result = update_device_by_id(params.id, data)
        if not result:
            return web.Response(
                status=HTTPStatus.IM_A_TEAPOT,
                reason="Failed to update the device in database",
            )

        return web.Response(status=HTTPStatus.OK)

    except ValidationError as e:
        return web.json_response(
            status=HTTPStatus.BAD_REQUEST,
            reason=format_validation_error(e),
            data=e.errors(),
        )

    except Exception as e:
        logger.error(f"Unhandled exception occurred: {e}")
        return web.Response(
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            reason="Unhandled exception occurred",
        )


@app.http_post("/api/remote-access/mobile-device/token")
@app.authenticated
@remote_access_handler
@session_wrapper_async
async def generate_registration_token(request: web.Request) -> web.Response:
    """Generate a new registration token"""
    username = request.cirrina.web_session.get("username")
    registration_jwt = generate_registration_jwt(username)
    return web.json_response(data={"token": registration_jwt})


@app.http_delete("/api/remote-access/mobile-device/token")
@app.authenticated
@remote_access_handler
@session_wrapper_async
async def delete_registration_token(_request: web.Request) -> web.Response:
    """Resets the registration password to None so it can't be used"""
    reset_registration_jwt()
    return web.Response(status=HTTPStatus.OK)


@app.http_put("/api/remote-access/mobile-device/remote-screen")
async def start_remote_screen(request):
    """Starts a remote screen by running StartRemoteScreen OSAL method"""
    try:
        require_remote_access(request)
    except Exception as e:
        return web.Response(status=HTTPStatus.UNAUTHORIZED, reason=e)

    ret = app.osal.StartRemoteScreen("mobile-device")

    if ret.outcome != OSAL_OK:
        return web.Response(
            text=str(ret.errorMessage), status=HTTPStatus.INTERNAL_SERVER_ERROR
        )

    return web.Response(status=HTTPStatus.OK)


@app.tcp_proxy_setup(
    "/api/remote-access/mobile-device/remote-screen",
    group="mobile-device",
    authenticated=remote_access_auth_handler,
    host="127.0.0.1",
    port=5900,
)
async def setup_remote_screen(_request: web.Request):
    """Init VNC connection"""
    pass


def _remote_screen_connection_handler(
    web_socket: web.WebSocketResponse, notification: str
):
    request = web_socket.cirrina.request

    try:
        decoded_jwt = get_decoded_jwt_from_cookies(request)
        app.execute_osal(notification, int(decoded_jwt["sub"]))
        logger.info(
            f"Sent notification '{notification}' for device {int(decoded_jwt['sub'])}"
        )
    except Exception as e:
        logger.warning(f"Failed to send notification {notification}: {e}")


@app.tcp_proxy_connect(group="mobile-device")
@session_wrapper
def remote_screen_connect(web_socket: web.WebSocketResponse):
    request = web_socket.cirrina.request
    decoded_jwt = get_decoded_jwt_from_cookies(request)
    device_id = int(decoded_jwt["sub"])

    osal_response: osal.Response = app.execute_osal(
        "RevokeAccessMobileDevice", device_id
    )

    if osal_response.outcome != OSAL_OK:
        logger.error(
            f"Failed to revoke access for device {device_id}: {osal_response.errorMessage}"
        )

    _remote_screen_connection_handler(web_socket, "NotifyMobileDeviceConnected")


@app.tcp_proxy_disconnect(group="mobile-device")
@session_wrapper
def remote_screen_disconnect(web_socket: web.WebSocketResponse):
    _remote_screen_connection_handler(web_socket, "NotifyMobileDeviceDisconnected")


@app.http_delete("/api/remote-access/mobile-device/remote-screen")
@app.authenticated
@remote_access_handler
@session_wrapper_async
async def terminate_all_sessions(_request: web.Request) -> web.Response:
    osal_response: osal.Response = app.execute_osal("DisconnectAllMobileDevices")

    if osal_response.outcome != OSAL_OK:
        logger.error(
            f"Failed to disconnect all mobile devices: {osal_response.errorMessage}"
        )
        return web.Response(
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            reason="Failed to disconnect all mobile devices",
        )

    return web.Response(status=HTTPStatus.OK)


@app.http_delete(r"/api/remote-access/mobile-device/remote-screen/{id:\d+}")
@app.authenticated
@remote_access_handler
@session_wrapper_async
async def terminate_device_session(request: web.Request) -> web.Response:
    osal_response: osal.Response = app.execute_osal(
        "DisconnectMobileDevice", int(request.match_info["id"])
    )

    if osal_response.outcome != OSAL_OK:
        logger.error(
            f"Failed to disconnect mobile device: {osal_response.errorMessage}"
        )
        return web.Response(
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            reason="Failed to disconnect mobile device",
        )

    return web.Response(status=HTTPStatus.OK)


@app.http_put("/api/remote-access/mobile-device/request-access")
@remote_access_handler
async def request_access_mobile_device(request: web.Request) -> web.Response:
    """
    Unauthenticated endpoint to request remote access from mobile device
    by executing RequestAccessMobileDevice OSAL method
    """
    decoded_jwt = get_decoded_jwt_from_cookies(request)
    device_id = int(decoded_jwt["sub"])
    osal_response: osal.Response = app.execute_osal(
        "RequestAccessMobileDevice", device_id
    )
    if osal_response.outcome != OSAL_OK:
        logger.error(
            f"Failed to request access for mobile device {device_id}: {osal_response.errorMessage}"
        )
        return web.Response(
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            reason="Failed to request access for mobile device {device_id}",
        )
    return web.Response(status=HTTPStatus.OK)


@app.http_get("/api/remote-access/mobile-device/request-access")
@remote_access_handler
@session_wrapper_async
async def request_access_mobile_device_status(request: web.Request) -> web.Response:
    """
    Checks the cookie in request and returns 200 if the client is authorized for remote access
    """
    try:
        decoded_jwt = get_decoded_jwt_from_cookies(request)
    except RemoteAccessTokenException as e:
        logger.info(e)
        return web.Response(status=HTTPStatus.UNAUTHORIZED, reason=e.message)

    device_id = int(decoded_jwt["sub"])

    return web.json_response(
        status=HTTPStatus.OK, data={"access_granted": granted_status_by_id(device_id)}
    )


@app.http_put(r"/api/remote-access/mobile-device/{id:\d+}/grant-access")
@app.authenticated
@remote_access_handler
async def grant_access_mobile_device(request: web.Request) -> web.Response:
    """
    Grants access for an authenticated mobile device by executing GrantAccessMobileDevice OSAL method
    """
    device_id = int(request.match_info["id"])
    osal_response: osal.Response = app.execute_osal(
        "GrantAccessMobileDevice", device_id
    )
    if osal_response.outcome != OSAL_OK:
        logger.error(
            f"Failed to grant access for mobile device {device_id}: {osal_response.errorMessage}"
        )
        return web.Response(
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            reason="Failed to grant access for mobile device {device_id}",
        )
    return web.Response(status=HTTPStatus.OK)


@app.http_put(r"/api/remote-access/mobile-device/{id:\d+}/revoke-access")
@app.authenticated
@remote_access_handler
async def revoke_access_mobile_device(request: web.Request) -> web.Response:
    """
    Revokes access for a mobile device identified by its ID by executing RevokeAccessMobileDevice OSAL method
    """
    device_id = int(request.match_info["id"])
    osal_response: osal.Response = app.execute_osal(
        "RevokeAccessMobileDevice", device_id
    )
    if osal_response.outcome != OSAL_OK:
        logger.error(
            f"Failed to revoke access for mobile device {device_id}: {osal_response.errorMessage}"
        )
        return web.Response(
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            reason="Failed to revoke access for mobile device {device_id}",
        )
    return web.Response(status=HTTPStatus.OK)
