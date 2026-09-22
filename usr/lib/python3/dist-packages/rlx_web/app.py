from aiohttp import web
import cirrina
from functools import wraps
import importlib
from pathlib import Path
from rlx_osal import OSAL, OSAL_OK
from rlx_osal.errors import UnknownOSALMethodError
import typing as T

from . import errors, utils
from .auto_logout.helpers import is_session_expired
from .log import logger

# Unique instance representing a missing parameter
_missing = object()


class RLXWebApp(cirrina.Server):
    LAUNCH_CODE_AVAILABLE = "/opt/roche/home/.launchcode_available"
    REMOTE_ACCESS_STATUS_FILE = Path("/var/lib/rlx-remote-access/maintenance-web/allow")
    session_storage_config = {}

    def __init__(self):
        self.osal = OSAL()

        super().__init__(
            app_kws={"middlewares": [errors.error_middleware]},
            **self.session_storage_config,
        )

        self.remote_access_requested = False

    def authenticated(self, func):
        """
        Decorator to enforce valid session before
        executing the decorated function.
        """

        _authenticated = super().authenticated(func)

        @wraps(func)
        async def _wrapper(request, *args, **kwargs):
            if request.cirrina.web_session.new:
                return await _authenticated(request, *args, **kwargs)

            if self.has_capability("web-auto-logout"):
                if is_session_expired(request.cirrina.web_session):
                    try:
                        await self._logout(request)
                    except Exception as e:
                        logger.warning(
                            f"Auto logout failed. Invalidating the session. {e}"
                        )
                        request.cirrina.web_session.invalidate()

                    return web.Response(status=401, reason="Session expired")

            return await func(request, *args, **kwargs)

        return _wrapper

    def get_capabilities(self) -> T.List[str]:
        ret = self.osal.GetCapabilityList()
        if ret.outcome != OSAL_OK:
            logger.error("Error calling get_capabilities")
            return []
        return list(ret.response.capabilities)

    def has_capability(self, capability: str) -> bool:
        return capability in self.get_capabilities()

    def require_capability(self, capability: str) -> None:
        if not self.has_capability(capability):
            raise web.HTTPNotImplemented(text=f"Capability {capability} not available")

    @staticmethod
    def has_plugin(plugin: str) -> bool:
        try:
            importlib.import_module(plugin)
            return True
        except ModuleNotFoundError:
            return False

    def require_plugin(self, plugin: str) -> None:
        if not self.has_plugin(plugin):
            raise web.HTTPNotImplemented(text=f"Plugin {plugin} not available")

    def is_launch_code_available(self) -> bool:
        return Path(self.LAUNCH_CODE_AVAILABLE).is_file()

    def reset_launch_code(self) -> None:
        try:
            Path(self.LAUNCH_CODE_AVAILABLE).unlink()
        except Exception:
            self.logger.exception("Error resetting launch code")

    def execute_osal(self, osal_msg, *args, **kwargs):
        """Execute an OSAL call.

        Raise OSAL specific exceptions on errors.
        Handle them in errors.error_middleware.
        """
        try:
            osal_func = getattr(self.osal, osal_msg)
            ret = osal_func(*args, **kwargs)
        except UnknownOSALMethodError:
            raise
        except Exception as exc:
            raise errors.OSALError(exc)
        if ret.outcome != OSAL_OK:
            raise errors.OSALCallError(retval=ret)
        return ret

    def get_argument(self, request, key, default=_missing):
        """Get a query argument and raise 400 if missing, unless default is
        given."""
        try:
            return request.GET.getone(key)
        except KeyError:
            if default is not _missing:
                return default
            raise web.HTTPBadRequest(reason=f"Missing required parameter: {key}")

    def get_param(self, params, key, default=_missing):
        """Get a request POST data param and raise 400 if missing, unless default is
        given."""
        try:
            return params[key]
        except KeyError:
            if default is not _missing:
                return default
            raise web.HTTPBadRequest(reason=f"Missing required parameter: {key}")

    def read_remote_access_status(self):
        """Read remote access status from filesystem"""

        if not self.has_capability("web-remote-access"):
            return True

        try:
            if not self.REMOTE_ACCESS_STATUS_FILE.exists():
                raise FileNotFoundError

            status = utils.read_file(self.REMOTE_ACCESS_STATUS_FILE)

            if status:
                status = int(status)

                if status in [0, 1]:
                    return bool(status)
                else:
                    raise ValueError
            else:
                raise ValueError
        except ValueError:
            self.logger.error(
                f"Error reading remote access status: unknown status '{status}'"
            )
            return False
        except FileNotFoundError:
            self.logger.error("Error reading remote access status: FileNotFoundError")
            return False
