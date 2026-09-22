from __future__ import annotations

import collections
import os
import typing as T

import itertools

from aiohttp.web_request import Request
from shutil import rmtree

AnyDict = T.Dict[str, T.Any]


# IP address of localhost
IP_LOCAL = "127.0.0.1"


def get_real_ip(request: Request) -> str:
    """Return real-ip from request. Use empty string if no real-ip is
    available."""
    real_ip: str = request.headers.get("X-Real-IP", "")
    return real_ip


def is_local(request: Request) -> bool:
    """Check if request is coming from localhost."""
    return get_real_ip(request) == IP_LOCAL


class DebianPackagesParser(object):
    """Adapted from https://github.com/ms7m/debian-packages-parser/"""

    def __init__(self, raw_packages_file):

        self._extra_strings_added = 0

        data_raw = raw_packages_file.splitlines()

        if data_raw[0] != "":
            data_raw.insert(0, "")
            self._extra_strings_added += 1

        if data_raw[-1] != "":
            data_raw.append("")
            self._extra_strings_added += 1

        self._data_splitted = data_raw

        if self._extra_strings_added != 0:
            self._extra_strings_added -= 1

        self._parse_to_seperated_lists()

    def _splitted_lines(self):
        return self._data_splitted.count("") - self._extra_strings_added

    def _parse_to_seperated_lists(self):

        # TODO: PLEASE REWRITE THIS IS
        # IS EXTREMELY UGLY
        #
        # It's basically just splitting the .splitlines()
        # into indiv. list seperated by < "" >

        size_of_splitlines = len(self._data_splitted)

        get_new_line_indexes = [
            index + 1
            for index, index_value in enumerate(self._data_splitted)
            if index_value == ""
        ]

        incomplete_data = [
            self._data_splitted[index_to_start:index_to_end]
            for index_to_start, index_to_end in zip(
                [0] + get_new_line_indexes,
                get_new_line_indexes
                + (
                    [size_of_splitlines]
                    if get_new_line_indexes[-1] != size_of_splitlines
                    else []
                ),
            )
        ]

        for sub_list in incomplete_data:
            for element_index, element in enumerate(sub_list):
                if element == "":
                    sub_list.pop(element_index)

        for sub_list_element, sub_list in enumerate(incomplete_data):
            if sub_list == []:
                incomplete_data.pop(sub_list_element)

        self._data = incomplete_data
        return self._data

    def _parse_string(self, string):

        if string == "":
            return False

        selected_string_split = string.split()
        selected_string_top = selected_string_split[0]
        selected_string_top_chars = [x for x in selected_string_top]

        if selected_string_top_chars.count(":") == 1:
            if "http" in selected_string_top:
                return False
            return True

        return False

    def _parse_to_dict(self):
        end_result = []

        for element_list in self._data:

            # selected_child = []
            selected_child = {}
            for selected_elements_index, selected_element in enumerate(element_list):

                selected_element_check = self._parse_string(selected_element)
                if selected_element_check is True:

                    selected_element_splitted = selected_element.split()
                    selected_element_key = selected_element_splitted[0]
                    selected_element_value = " ".join(selected_element_splitted[1:])

                    # check if the next values should be appended.

                    for inter_step in itertools.count(selected_elements_index + 1):
                        try:
                            selected_element_future = element_list[inter_step]
                            future_index_to_check = self._parse_string(
                                selected_element_future
                            )
                            if future_index_to_check is True:
                                break
                            else:
                                selected_element_value += " " + element_list[inter_step]
                        except IndexError:
                            break

                    # selected_child.append(
                    #     {
                    #         "tag": selected_element_key.strip(":"),
                    #         "value": selected_element_value,
                    #     }
                    # )
                    selected_child[selected_element_key.strip(":")] = selected_element_value
                else:
                    continue

            end_result.append(selected_child)
        return end_result

    def parse(self) -> T.List[AnyDict]:
        if self._data:
            return self._parse_to_dict()

        self._parse_to_seperated_lists()
        return self._parse_to_dict()


def tail(n: int, iterable: T.Iterable) -> T.Iterable:
    "Return an iterator over the last n items"
    # tail(3, 'ABCDEFG') --> E F G
    return iter(collections.deque(iterable, maxlen=n))


async def remove_file(fname, logger):
    try:
        if os.path.isfile(fname) or os.path.islink(fname):
            logger.info("removing file " + fname)
            os.remove(fname)
        else:
            logger.warning("cannot remove non-existing file " + fname)
    except OSError as error:
        logger.error("Error removing or closing downloaded file handle", error)


async def remove_dir(dirname, logger):
    try:
        if os.path.isdir(dirname):
            logger.info("removing directory " + dirname)
            rmtree(dirname)
        else:
            logger.warning("cannot remove non-existing directory " + dirname)
    except OSError as error:
        logger.error("Error removing or closing downloaded directory handle", error)


def _read_path_mapping():
    PATH_MAPPING = "/opt/roche/etc/rlx-osal/path-mapping"

    pm = {}
    if os.path.isfile(PATH_MAPPING):
        with open(PATH_MAPPING, "r") as pm_file:
            for line in pm_file.read().split("\n"):
                if line and not line.startswith("#"):
                    pm_entry = line.split(":")
                    pm[pm_entry[0].strip()] = pm_entry[1].strip()
    return pm if pm else None


def get_dest_path_mapping(host_path):
    pm = _read_path_mapping()

    return pm[host_path] if pm else None


def get_src_path_mapping(docker_path):
    pm = _read_path_mapping()

    return list(pm.keys())[list(pm.values()).index(docker_path)] if pm else None


def read_file(
        filepath: T.Union[str, os.PathLike],
        return_type: T.Union[str, bytes, None] = str
):
    """
    Read file and return its content as str or bytes
    Returns None if file can't be read or doesn't exist
    """
    try:
        if return_type == str:
            with open(filepath, 'rt') as f:
                content = f.read()
        elif return_type == bytes:
            with open(filepath, 'rb') as f:
                content = f.read()
        return content
    except (FileNotFoundError, PermissionError, IsADirectoryError):
        return None
