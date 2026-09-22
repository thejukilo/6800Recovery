import re
import typing as T

from aiohttp import web

from rlx_osal.osal import UnknownOSALMethodError


RLX_ERROR_HTTP_HEADER = "X-RLX-Error"
# Regex of what constitutes valid value as http header
HTTP_HEADER_VALUE_RE = re.compile(r"[^0-9a-zA-Z ]")
# HTTP headers can't be too long
HTTP_HEADER_MAX_LENGTH = 1000


def _fmt_http_header_value(txt: str) -> str:
    return re.sub(HTTP_HEADER_VALUE_RE, "", txt)[:HTTP_HEADER_MAX_LENGTH]


class RLXWebError(Exception):
    """Base class for all RLX Web errors."""


class OSALError(RLXWebError):
    """Generic OSAL error."""


class OSALCallError(OSALError):
    """OSAL call error."""

    def __init__(self, retval: T.Any):
        super().__init__()
        self.retval = retval

    def __str__(self) -> str:
        return f"OSALCallError: {self.retval.errorMessage}"

    def __repr__(self) -> str:
        return str(self)


@web.middleware
async def error_middleware(request, handler):
    """Middleware to handle errored http responses.

    Error messages are logged and reported to the client using
    RLX_ERROR_HTTP_HEADER.
    """
    from rlx_web.app_api import app

    try:
        response = await handler(request)

    # Raised by the OSAL client, when no OSAL method is found.
    # E.g. when a plugin is missing.
    except UnknownOSALMethodError as exc:
        msg = f"Unknown OSAL method: {exc}"
        app.logger.exception(msg)
        raise web.HTTPNotImplemented(
            text=msg, headers={RLX_ERROR_HTTP_HEADER: _fmt_http_header_value(msg)}
        )

    # Generic OSAL error, e.g. OSALCallError
    except OSALError as exc:
        msg = f"{exc!r}"
        app.logger.exception(msg)
        raise web.HTTPInternalServerError(
            text=msg,
            headers={RLX_ERROR_HTTP_HEADER: _fmt_http_header_value(msg)},
        )

    # Generic HTTP Exception: we just want to log it and re-raise it as is
    except web.HTTPException as exc:
        msg = f"HTTP exception: {exc!r}"
        app.logger.warning(msg)
        raise

    # Unknown error. Just log it and report it using RLX_ERROR_HTTP_HEADER
    except Exception as exc:
        msg = f"Unknown error: {exc!r}"
        app.logger.exception(msg)
        raise web.HTTPInternalServerError(
            text=msg, headers={RLX_ERROR_HTTP_HEADER: _fmt_http_header_value(msg)}
        )

    # Success
    else:
        return response
