from rlx_web.remote_access.constants import CAPABILITY
from rlx_web.config import config as rlx_web_config


def testing_enabled() -> bool:
    return rlx_web_config.getboolean(
        section=CAPABILITY, option="enable_testing", fallback=False
    )
