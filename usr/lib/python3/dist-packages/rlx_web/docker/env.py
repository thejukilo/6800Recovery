from typing import Dict, List
import yaml
import re
import os

from ..log import logger


DOCKER_COMPOSE_ENV_FILE = "/opt/roche/var/lib/docker-compose/.env"
DOCKER_COMPOSE_DEFAULT_ENV_FILE = "/opt/roche/etc/docker-compose.env"
DOCKER_COMPOSE_YML_FILE = "/opt/roche/etc/docker-compose.yml"

SECRETS_MASK = "*****"


def get_docker_compose_env_vars() -> Dict:
    """
    Read variables and values from the DOCKER_COMPOSE_ENV_FILE. Additionally
    add all variables referenced in the DOCKER_COMPOSE_YML_FILE with an empry
    value.  The resulting variables are filtered to only include
    user-configurable options, i.e. vars like A0_SOME_VAR_NAME and secrets are
    masked.

    Returns:
        Dict: Environment variables that can be set by the user, secrets masked
    """
    env_file = get_vars_from_env_file(DOCKER_COMPOSE_ENV_FILE)
    env_yml = get_vars_from_yml_file()

    for var in env_yml:
        if var not in env_file:
            env_file[var] = ""
    return hide_secrets(filter_vars(env_file))


def get_vars_from_env_file(file: str = DOCKER_COMPOSE_ENV_FILE) -> Dict:
    """
    Parse the given env file into a dictionary

    Returns:
        Dict: key is the variable name, value is the variable value
    """
    vars = {}
    lines = read_file(file).splitlines()
    var_pattern = re.compile(r"^([A-Z0-9_]+)=(.+)$")
    for line in lines:
        m = var_pattern.match(line)
        if m:
            vars[m.group(1)] = m.group(2)
    return vars


def read_file(file: str) -> str:
    data = ""
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                data = f.read()
        except OSError as err:
            logger.error(err)
    return data


def read_yml(yml_file: str) -> Dict:
    try:
        with open(yml_file, "r") as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as err:
                logger.error(err)
    except OSError as err:
        logger.error(err)
    return data


def get_vars_from_yml_file(file: str = DOCKER_COMPOSE_YML_FILE) -> List:
    """
    Parse DOCKER_COMPOSE_YML_FILE to get the
    environment variables that need to be evaluated

    Returns:
        List: names of environment variables that needs to be evaluated
    """
    vars = set()
    data = read_yml(file)
    services = data.get("services", None)
    if services:
        var_ref_pattern = re.compile(r"=\$\{([A-Z0-9_]+)\}$")
        for v in services.values():
            environment = v.get("environment", None)
            if environment:
                for e in environment:
                    m = var_ref_pattern.search(e)
                    if m:
                        vars.add(m.group(1))
    return list(vars)


def filter_vars(vars: Dict) -> Dict:
    """
    Only retain user defined keys of the form A0_SOME_VAR_NAME

    Args:
        vars (Dict): a dictionary of environment variables names (keys) and values

    Returns:
        Dict: a dictionary that only containes variables ment to be configured by the user
    """
    # Only keep keys of the form A0_SOME_VAR_NAME
    return {k: v for k, v in vars.items() if re.fullmatch("[A-Z][0-9]+_[A-Z0-9_]+", k)}


def hide_secrets(vars: Dict) -> Dict:
    """
    For secrets, change value to "*****" if set, otherwise ""

    Args:
        vars (Dict): a dictionary of environment variables names (keys) and values

    Returns:
        Dict: a dictionary with masked secrets
    """

    def mask(var, value):
        if ("PASSWORD" in var or "SECRET" in var) and value:
            return SECRETS_MASK

        return value

    return {k: mask(k, v) for k, v in vars.items()}
