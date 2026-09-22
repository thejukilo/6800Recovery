from dataclasses import dataclass
from pathlib import Path
import os


def get_variable_value_from_line(line: str, separator: str = "=") -> str:
    return line.strip().split(separator)[1]


def remove_outer_quotes(original_string: str) -> str:
    if original_string.startswith('"') and original_string.endswith('"'):
        return original_string.strip('"')
    return original_string


def unescape(escaped_quoted_string: str) -> str:
    original_string = escaped_quoted_string.replace("\\\\", "\\")
    original_string = original_string.replace("\\$", "$")
    original_string = original_string.replace("\\`", "`")
    original_string = original_string.replace("\\\"", "\"")
    return original_string


def http_proxy_exists(conf_file: Path = Path("/opt/roche/etc/rlx/http-proxy.conf")) -> bool:
    if os.path.exists(conf_file):
        return True
    return False


@dataclass
class HTTPProxyInfo:
    http_proxy: str = ""
    user: str = ""
    password: str = ""


@dataclass
class HTTPProxy:
    conf_file: Path = Path("/opt/roche/etc/rlx/http-proxy.conf")

    def get_escaped_info(self) -> HTTPProxyInfo:
        http_proxy = ""
        user = ""
        password = ""
        with open(self.conf_file, "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.strip().startswith("PROXY_SERVER="):
                    http_proxy = remove_outer_quotes(get_variable_value_from_line(line))
                if line.strip().startswith("USER="):
                    user = remove_outer_quotes(get_variable_value_from_line(line))
                if line.strip().startswith("PASSWORD="):
                    password = remove_outer_quotes(get_variable_value_from_line(line))
        return HTTPProxyInfo(http_proxy, user, password)

    def get_unescaped_info(self) -> HTTPProxyInfo:
        raw_info = self.get_escaped_info()
        http_proxy = raw_info.http_proxy
        user = raw_info.user
        password = raw_info.password
        return HTTPProxyInfo(unescape(http_proxy),
                             unescape(user),
                             unescape(password)
                             )
