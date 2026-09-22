from datetime import datetime, timedelta, timezone
from secrets import token_hex
from typing import Optional, Dict, Any
from aiohttp.web import Request

import jwt
from pydantic.error_wrappers import ValidationError

from .constants import (
    JWT_ALGORITHM,
    AUTH_TOKEN_KEY,
    DEFAULT_REGISTRATION_TOKEN_LIFETIME,
)
from .db import insert_secret, select_secret
from .exceptions import RemoteAccessTokenException
from .models import Secret
from ...config import config as rlx_web_config
from rlx_web.log import logger

__registration_jwt_key = None


def get_expiry_date(delta: timedelta) -> datetime:
    """Return expiry date as datetime object with UTC timezone"""
    return datetime.now(timezone.utc) + delta


def format_validation_error(error: ValidationError) -> str:
    return ", ".join(
        [f"{', '.join(err.get('loc', ()))}: {err.get('msg')}" for err in error.errors()]
    )


def generate_registration_jwt(username: str) -> str:
    """Generate JWT token for registration"""
    global __registration_jwt_key
    exp = get_expiry_date(
        timedelta(
            minutes=rlx_web_config.getint(
                "remote-access-mobile-device",
                "registration_token_lifetime",
                fallback=DEFAULT_REGISTRATION_TOKEN_LIFETIME,
            )
        )
    )
    __registration_jwt_key = token_hex(32)
    token = jwt.encode(
        payload={"otp": token_hex(32), "user": username, "exp": exp},
        key=__registration_jwt_key,
        algorithm=JWT_ALGORITHM,
    )

    return token


def reset_registration_jwt() -> None:
    global __registration_jwt_key
    __registration_jwt_key = None


def decode_registration_jwt(token: str) -> Optional[Dict[str, Any]]:
    """Validate JWT token and return decoded JWT token"""
    if __registration_jwt_key is None:
        raise RemoteAccessTokenException("No registration password generated")

    try:
        required = ["exp", "user", "otp"]
        token = jwt.decode(
            jwt=token,
            key=__registration_jwt_key,
            algorithms=[JWT_ALGORITHM],
            options={"require": required},
        )

        return token

    except jwt.PyJWTError as e:
        raise RemoteAccessTokenException(f"Invalid or expired token: {e}")


def generate_auth_token(device_id: int, exp: datetime) -> str:
    secret = Secret(value=token_hex(32), device_id=device_id)
    insert_secret(secret)

    token = jwt.encode(
        payload={"sub": device_id, "exp": exp},
        key=secret.value,
        headers={"kid": str(secret.id)},
        algorithm=JWT_ALGORITHM,
    )

    return token


def decode_auth_jwt(token: str) -> Optional[Dict[str, Any]]:
    try:
        untrusted_header = jwt.get_unverified_header(token)

        if "kid" not in untrusted_header:
            raise RemoteAccessTokenException(
                "Missing or invalid kid param in token header"
            )

        secret = select_secret(int(untrusted_header["kid"]))

        if secret is None:
            return None

        required = ["exp", "sub"]
        token = jwt.decode(
            token,
            key=secret.value,
            algorithms=[JWT_ALGORITHM],
            options={"require": required},
        )

        return token

    except jwt.PyJWTError as e:
        raise RemoteAccessTokenException(f"Invalid or expired token: {e}")

    except Exception as e:
        if isinstance(e, RemoteAccessTokenException):
            raise e
        logger.error(f"Unhandled exception: {e}")
        return None


def get_decoded_jwt_from_cookies(request: Request) -> dict[str, Any]:
    auth_token = request.cookies.get(AUTH_TOKEN_KEY)
    if not auth_token:
        raise RemoteAccessTokenException(f"Missing {AUTH_TOKEN_KEY} cookie")

    decoded_jwt = decode_auth_jwt(auth_token)
    if not decoded_jwt:
        raise RemoteAccessTokenException("Invalid or expired authentication token")

    return decoded_jwt
