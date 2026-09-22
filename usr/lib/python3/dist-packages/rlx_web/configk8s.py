'''RLX K8S SETUP config

RLX K8S SETUP is configured via an optional ini file in:
    $RLX_LAUNCH_CODES_CONFIG_FILENAME
which defaults to:
    /opt/roche/etc/rlx-kubernetes/setup.ini

- setup.ini is going to be deprecated in favor of /opt/roche/etc/rlx-kubernetes/rlx-kubernetes.ini
- rlx-kubernetes.ini is based on [kubernetes] section from project specific ini file
on launchcode repo: terraform-launch-code.rlx.navify.com

'''
import configparser
import logging
import os
import typing as T

from dotenv import load_dotenv


load_dotenv()

RLX_KUBERNETES_CONFIG_FILENAME_DEFAULT = "/opt/roche/etc/rlx-kubernetes/rlx-kubernetes.ini"

logger = logging.getLogger(__name__)


# https://stackoverflow.com/a/68068943
class EnvInterpolation(configparser.ExtendedInterpolation):
    """Interpolation which expands environment variables in values."""

    def before_read(
        self, parser: T.Any, section: str, option: str, value: str
    ) -> T.Any:
        value = super().before_read(parser, section, option, value)
        return os.path.expandvars(value)


filename = (
    os.environ.get("RLX_KUBERNETES_CONFIG_FILENAME")
    or RLX_KUBERNETES_CONFIG_FILENAME_DEFAULT
)
# TODO: check if file exists - don't raise exception
if not os.path.exists(filename):
    # raise Exception(f"File not found: {filename}")
    logger.error("File not found: %s", filename)

logger.info("Reading config from %s", filename)
config = configparser.ConfigParser(interpolation=EnvInterpolation())

# Fixing invalid escape sequences
config.optionxform = str  # Preserve case sensitivity
config.read(filename, encoding="utf-8")
