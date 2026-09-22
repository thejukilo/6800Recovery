from functools import wraps
from aiohttp.web import Request
from types import FunctionType
from rlx_web.app_api import app


def generic_request_handler(
    plugin: str = "", capability: str = "", authenticated=True
) -> FunctionType:
    """
    Returns a decorator function that checks whether OSAL plugin and web capability are available

    param plugin: The name of the plugin
    param capability: The name of the capability
    authenticated: Whether the handler requires authentication
    """
    if not (plugin or capability):
        raise ValueError("Either plugin or capability must be provided")

    def handler(func: FunctionType):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if plugin:
                app.require_plugin(plugin)
            if capability:
                app.require_capability(capability)
            response = await func(*args, **kwargs)
            return response

        return wrapper if not authenticated else app.authenticated(wrapper)

    return handler
