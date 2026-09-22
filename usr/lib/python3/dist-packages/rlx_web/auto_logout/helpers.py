import time

from ..config import config as rlx_web_config

AUTO_LOGOUT_DEFAULT_TIMEOUT = 5


def get_auto_logout_timeout():
    """Read the timeout value from the config file or return a default value"""
    return (
        rlx_web_config.getint(
            "auto-logout", "timeout", fallback=AUTO_LOGOUT_DEFAULT_TIMEOUT
        )
        * 60
    )


def update_last_access_time(session):
    """Set the current time as last access into the session"""
    session["last_access"] = time.time()


def is_session_expired(session):
    """
    Check if the last access time stored in the session plus the timeout is
    older than the current time
    """
    last_access = session.get("last_access", 0)
    timeout = get_auto_logout_timeout()

    return time.time() - last_access > timeout
