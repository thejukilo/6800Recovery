#!/usr/bin/env python3

"""
This script runs Software Update logic in the following order:

    1. installation of the software update packages
    2. installation of the auxiliary packages
    3. reboot at the end

    Descriptions more in detail:
    *  OSAL software upgrade status must be UPGRADE_SUCCESSFUL before the script to run. (initial update must be by C# SWU)
    *  pending-updates must contain pending packages, conforming to semantic versioning with (SW, UserAssistance, LanguagePackage) prefixes.
    *  it first tries any SW upgrades (which involves reboot by RLX)
    *  then, it tries any auxiliary packages installation
    *  if the auxiliary packages installation fails, then reverts to the bootable snapshot, and reboot.
    *  if the auxiliary packages installation succeeds, it verifies that all packages are indeed installed. If not, reverts to the bootable snapshot
    *  regardless of succcess/failure, always reboot at the end

"""

import collections
import json
import logging
import os
import re
import traceback
from datetime import datetime
from typing import Any, Iterable

from rlx_osal import OSAL
from rlx_osal.outcome import Outcome
from rlx_osal.osal_pb2 import UPGRADE_SUCCESSFUL
from rlx_osal.plugins.addon_pb2 import AddonPackages

Response = collections.namedtuple('Response', ['outcome', 'errorMessage', 'response'])

PENDING_UPDATES_PATH = "/opt/roche/var/lib/mollab/private/software-update/pending-updates/"
SOFTWARE_UPDATE_STATUS_PATH = "/opt/roche/var/lib/mollab/private/software-update/software_update_status.json"
VERSION_PATTERN_REGEX = r"[_\.]?(\d+\.\d+\.\d+\.\d+)\b"
SW_UPDATE_FILENAME_REGEX = r"(?:(Roche\.([^.]+))\.)?SW\.(?P<version>\d+\.\d+\.\d+\.\d+)\.(?P<builddate>[0-9]{8})(\.(?P<extension>(tar$)|(tar\.xz$)|zip))"
AUXILIARY_UPDATE_FILENAME_REGEX = r"(?:(Roche\.([^.]+))\.)?(?P<type>LanguagePackage|UserAssistance)\.(?P<version>\d+\.\d+\.\d+\.\d+)\.(?P<language>[a-z]{2}(?:-[A-Z]{2})?)?\.(?P<builddate>[0-9]{8})(\.(?P<extension>(tar$)|(tar\.xz$)|zip))"
LOG_DIR = "/opt/roche/var/lib/mollab/shared/logs/"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s]%(message)s", filename=f"{LOG_DIR}/swupdate_{datetime.now().strftime('%Y%m%d')}.log")

def extract_semantic_version(version: str) -> str | None:
    match = re.search(VERSION_PATTERN_REGEX, version)
    return match.group(1) if match else None

def extract_semantic_version_from_filename(filename: str) -> str | None:
    match_sw = re.match(SW_UPDATE_FILENAME_REGEX, filename)   

    if match_sw:     
      return match_sw.group('version')
    
    match_other = re.match(AUXILIARY_UPDATE_FILENAME_REGEX, filename)
    return match_other.group('version') if match_other else None


def filter_by_type(filenames: list[str], type: str) -> list[str]:
    return [filename for filename in filenames if type in filename]


def get_filenames_sorted_by_semantic_version(directory: str) -> list[str]:
    return sorted(get_files_with_filter(directory, extract_semantic_version_from_filename),
                  key=extract_semantic_version_from_filename,
                  reverse=False)


def get_files_with_filter(directory: str, IsMatch) -> list[str]:
    found_files = [file
            for _, _, files in os.walk(directory)
            for file in files]
    logger.debug(f"Checking files: \n{format_to_string(found_files)}")
    return [file
            for file in found_files if IsMatch(file) is not None]


def format_to_string(anArray: Iterable[Any]) -> str:
    return "\n".join(anArray)


def check_upgrade_status_is_successful(osal: OSAL) -> tuple[bool, Response]:
    ok, response = is_osal_response_ok(osal.GetSoftwareUpgradeStatus(), "GetSoftwareUpgradeStatus")
    if not ok:
        return False, response

    logger.debug(f"Software update status: {map_upgrade_status_to_enum(response.status)}")
    if response.status is not UPGRADE_SUCCESSFUL:
        return False, response

    logger.info(f"Proceeding with status(\n{response}) ")
    return True, response


def write_software_update_status_file(response : Response):
    data = { "token": response.token,
             "status": response.status,
             "description": response.description,
             "upgradeDuration": response.upgradeDuration,
             "estimatedUpgradeDuration": response.estimatedUpgradeDuration,
             "requiredFreeDiskSpace": response.requiredFreeDiskSpace,
             "snapshotPrefix": response.snapshotPrefix}
    with open(SOFTWARE_UPDATE_STATUS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

"""
Install SW Packages:
    1. Send SoftwareUpgradeOffline()
        1.1 OSAL invokes system reboot during the SW upgrade
    2. Check the osal response and return the status
        2.1 If OSAL invokes system reboot, obviously no response will be returned.
"""


def install_sw_packages(osal: OSAL, snapshot_prefix: str, pending_updates_path: str, sw_filename: str) -> bool:
    prefix_info = f"with prefix: '{snapshot_prefix}'" if snapshot_prefix else "with no prefix"
    logger.info(f"Sending 'SoftwareUpgradeOffline' with '{sw_filename}' and {prefix_info}")

    try:
        osal_resp = osal.SoftwareUpgradeOffline(
            pending_updates_path + sw_filename,          # path
            sw_filename,                                 # description
            sw_filename,                                 # token
            False,                                       # keepCurrentVersion
            False,                                       # keepUpgradeSnapshot
            snapshot_prefix if snapshot_prefix else "")  # useExistingSnapshot

        ok, response = is_osal_response_ok(osal_resp,
                                   "SoftwareUpgradeOffline",
                                   f"succeeded for '{sw_filename}'")
        
        if ok:
           return True
        
        if not ok:
           logger.error(f"Error while installing software packages. Response: {response}")
           handle_installation_failure(osal)
           return False

    except Exception as e:
        logger.error(f"Exception while installing software packages: {e}")
        handle_installation_failure(osal)
        return False


"""
Install Auxiliary Packages:
    1. For each the auxiliary package(s) in the directory:
        1.1 Send GetAddonPackages() to get addon packages
            1.1.1 Send InstallAddonPackage() for each addon package
    2. Verify installed packages with GetInstalledAddonPackages()
    3. Return True if all installed packages are successfully installed, else False
"""


def install_auxiliary_packages(osal: OSAL, pending_updates_path: str, auxiliary_filenames: list[str]) -> bool:
    logger.info(f"Installing auxiliary packages:\n{format_to_string(auxiliary_filenames)}\n")
    try:

        ok, installed_addons = process_auxililary_packages(osal, pending_updates_path, auxiliary_filenames)
        if not ok or not installed_addons:
            handle_installation_failure(osal)
            return False

        logger.info(f"Verifying {len(installed_addons)} installed addon package(s)")
        if not verify_installed_addon_packages(osal, installed_addons):
            handle_installation_failure(osal)
            return False

        logger.info("Auxiliary packages installed successfully")
        return True

    except Exception as e:
        logger.error(f"Error installing auxiliary packages: {e}")
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        return False


def process_auxililary_packages(osal: OSAL, pending_updates_path: str, auxiliary_filenames: list[str]) -> tuple[bool, list[dict[str, Any]]]:
    installed_packages = []
    for index, package in enumerate(auxiliary_filenames, start=1):
        logger.info(f"Processing auxiliary package [{index}]: '{package}'")

        # each auxiliary package contains multiple addon packages.
        addonPackages = invoke_get_addon_packages_for_auxiliary_package(osal, pending_updates_path, package)

        if addonPackages:
            logger.info(f"Installing addon package(s) in order: '{json.dumps(addonPackages, indent=2)}'")

            if not install_addon_packages(osal, addonPackages):
                return False, []
            else:
                installed_packages.extend(addonPackages)
        else:
            logger.error(f"Failed to get addon packages for '{package}'")

    return True, installed_packages


def invoke_get_addon_packages_for_auxiliary_package(osal: OSAL, directory_path: str, package: str) -> list[dict[str, Any]]:
    ok, response = is_osal_response_ok(osal.GetAddonPackages(directory_path + package), "GetAddonPackages", "succeeded")
    if not ok:
        return []
    return safe_parser(response, parse_addon_packages)


def install_addon_packages(osal: OSAL, addonPackages: list[dict[str, Any]]) -> bool:
    for package in addonPackages:
        ok, _ = is_osal_response_ok(
            osal.InstallAddonPackage(package["name"], package["version"]),
            "InstallAddonPackage", f"succeeded for '({package['name']}, {package['version']})'")

        # as soon as one package installation fails, immediately return false.
        if not ok:
            return False

    # If all packages are successfully installed, only then, return true.
    return True


def verify_installed_addon_packages(osal: OSAL, addon_packages: list[dict[str, Any]]) -> bool:
    ok, response = is_osal_response_ok(
        osal.GetInstalledAddonPackages(),
        "GetInstalledaddonPackages",
        "succeeded")

    if not ok:
        logger.error("Failed to get installed addon packages")
        return

    installed_packages = safe_parser(response, parse_addon_packages)
    logger.info(f"\nActual installed auxiliary package(s): '{json.dumps(installed_packages, indent=2)}'")

    # check installed_packages contain all addon_packages based on version and name
    for package in addon_packages:
        if not any(pkg["name"] == package["name"] and
                   pkg["version"] == package["version"] and
                   pkg["installed"]
                   for pkg in installed_packages):
            logger.error(f"Package '{package}' not installed")
            return False
    return True


def get_systemid_of_max_version(osal: OSAL) -> int | None:
    ok, response = is_osal_response_ok(osal.GetSystemVersionList(), "GetSystemVersionList", "succeeded")
    if not ok:
        return None

    versions = safe_parser(response, parse_system_versions)
    if not versions:
        logger.error("No versions returned from OSAL")
        return None

    logger.info(f"{len(versions)} Version(s) returned from OSAL: {json.dumps(versions, indent=2)}")

    sorted_by_max_versions = sort_by_max_version_with_semantic_version(versions)

    if not sorted_by_max_versions:
        logger.error("No maximum version found")
        return None
    elif not sorted_by_max_versions[0].get("systemID"):
        logger.error("No systemID found")
        return None
    else:
        return sorted_by_max_versions[0]["systemID"]


def sort_by_max_version_with_semantic_version(versions) -> list[dict[str, Any]]:
    return sorted([v for v in versions if extract_semantic_version(v["version"]) is not None],
                  key=lambda x: extract_semantic_version(x["version"]),
                  reverse=True)


def handle_installation_failure(osal: OSAL):

    system_id = get_systemid_of_max_version(osal)
    if not system_id:
        logger.error("SystemID not found")
    else:
        logger.info(f"Setting active system version to {system_id}")
        is_osal_response_ok(osal.SetActiveSystemVersion(system_id), "SetActiveSystemVersion", f"succeeded with '{system_id}'")

    invoke_system_restart(osal)


def invoke_system_restart(osal):
    logger.info("Restarting the system")
    is_osal_response_ok(osal.SystemRestart(), "SystemRestart", "succeeded")


def safe_parser(response, parse_func) -> list[dict[str, Any]]:
    try:
        return parse_func(response)
    except Exception as e:
        logger.error(f"An error occurred during parsing with {parse_func.__name__}: {e}")
        return []


def parse_addon_packages(response: AddonPackages) -> list[dict[str, Any]]:
    return list(map(lambda pkg: {
                "name": pkg.name,
                "version": pkg.version,
                "description": pkg.description,
                "long_description": pkg.long_description,
                "installed": pkg.installed,
                }, response.packages))


def parse_system_versions(response) -> list[dict[str, Any]]:
    return list(map(lambda ver: {
                "systemID": ver.systemID,
                "version": ver.version,
                "install_date": ver.installDate,
                # "snapshort_percentages": version.SnapshotPercentages
                }, response.versions))


def map_upgrade_status_to_enum(status: int) -> str:
    status_mapping = {
        0: "UPGRADE_NOT_RUNNING",
        1: "UPGRADE_IN_PROGRESS",
        2: "UPGRADE_SUCCESSFUL",
        3: "UPGRADE_FAILED",
    }
    return status_mapping.get(status, "Unknown")


def map_response_status_to_enum(status: int) -> str:
    status_mapping = {
        0: "NONE",
        1: "OK",
        2: "ERROR",
        3: "UNKNOWN_REQUEST",
        4: "PARAMETER_ERROR",
        5: "BUSY",
        6: "NO_BACKGROUND",
        7: "PROCESSING",
    }
    return status_mapping.get(status, "Unknown")


def is_osal_response_ok(osal_resp: Response, command: str, success_message: str | None = None) -> tuple[bool, Response]:
    if osal_resp.outcome != Outcome.OK.value:
        logger.error(f"'{command}' failed with {map_response_status_to_enum(osal_resp.outcome)}: {osal_resp.errorMessage}")
        return False, osal_resp.response
    else:
        logger.info(f"'{command}' {success_message}") if success_message else None
        return True, osal_resp.response


def main() -> int:
    logger.info("==== Software Update - Post Installation ====")

    # Delete log files which are older than 7 days
    os.system("find " + LOG_DIR + "swupdate_*.log -mtime +7 -delete")

    osal = OSAL()

    # Get last update status and proceed only if successful.
    # If it failed, the initial update failed and there is no sense in proceeding.
    successful, response = check_upgrade_status_is_successful(osal)
    write_software_update_status_file(response)
    if not successful:
        return 0

    sorted_filenames = get_filenames_sorted_by_semantic_version(PENDING_UPDATES_PATH)

    if not sorted_filenames:
        logger.info(f"No matching files found in '{PENDING_UPDATES_PATH}'")
        return 0

    logger.info(f"\nAvailable {len(sorted_filenames)} upgrade package(s):\n{format_to_string(sorted_filenames)}\n")

    sw_filenames = filter_by_type(sorted_filenames, "SW.")
    auxiliary_filenames = filter_by_type(sorted_filenames, "UserAssistance.")
    auxiliary_filenames += filter_by_type(sorted_filenames, "LanguagePackage.")

    if sw_filenames:
        # RLX will invoke reboot during the upgrade, so it won't be returned here unless it failed to start the upgrade.
        return 0 if install_sw_packages(osal, response.snapshotPrefix, PENDING_UPDATES_PATH, sw_filenames[0]) else 1
    elif auxiliary_filenames:
        # All auxiliary updates are installed sequentially 
        install_auxiliary_packages(osal, PENDING_UPDATES_PATH, auxiliary_filenames)

    logger.info("Finished processing sw and auxiliary upgrade packages")

    invoke_system_restart(osal)
    return 0


if __name__ == "__main__":
    main()