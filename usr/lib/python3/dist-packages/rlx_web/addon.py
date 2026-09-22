import csv
import functools
import os
import typing as T
import shutil

from pathlib import Path
from aiohttp import web

from rlx_osal import OSAL_OK
from .shared import generic_request_handler

try:
    from rlx_osal.plugins.addon_pb2 import AddonPackages
except ImportError:
    AddonPackages = None

from .app_api import app, UPLOAD_DIR
from .utils import AnyDict, tail, remove_file, remove_dir


PkgT = AnyDict

destfile = "/opt/roche/var/spool/addon.tar.xz"
destdir = "/opt/roche/var/spool/addon"


async def _addon_cleanup():
    if os.path.isfile(destfile):  # cleanup old files
        await remove_file(destfile, app.logger)
    if os.path.isdir(destdir):  # cleanup old extracted addons
        await remove_dir(destdir, app.logger)
        return


addon_handler = generic_request_handler(
    "rlx_osal.plugins.addon_pb2", "web-addon", authenticated=True
)


def _parse_osal_packages(response: AddonPackages) -> T.List[PkgT]:
    pkgs = []
    for pkg in response.packages:
        pkgs.append(
            {
                "name": pkg.name,
                "version": pkg.version,
                "description": pkg.description,
                "long_description": pkg.long_description,
                "installed": pkg.installed,
            }
        )
    return pkgs


def _merge_packages(pkgs1: T.List[PkgT], pkgs2: T.List[PkgT]) -> T.List[PkgT]:
    def key(p):
        return (p["name"], p["version"])

    pkgs = {key(p): p for p in pkgs1}
    pkgs.update({key(p): p for p in pkgs2})
    return list(pkgs.values())


@app.http_get("/api/addon")
@addon_handler
async def addon_list(request):
    ret = app.osal.GetInstalledAddonPackages()
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)

    pkgs = _parse_osal_packages(ret.response)

    return web.json_response(
        {
            "packages": sorted(
                pkgs, key=lambda p: (p["description"], p["name"], p["version"])
            )
        }
    )


@app.http_post("/api/addon/cleanup")
@addon_handler
async def addon_cleanup(request):
    await _addon_cleanup()
    return web.Response()


@app.http_upload("/api/addon/upload", upload_dir=UPLOAD_DIR)
@addon_handler
async def addon_upload(request, tempfile, filename, size):
    if not filename.endswith(".tar.xz"):
        return web.Response(text="Wrong file format", status=415)

    await _addon_cleanup()

    shutil.move(tempfile, destfile)

    ret = app.osal.GetAddonPackages(destfile)
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)

    uploaded_pkgs = _parse_osal_packages(ret.response)

    ret = app.osal.GetInstalledAddonPackages()
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)

    installed_pkgs = _parse_osal_packages(ret.response)

    pkgs = _merge_packages(uploaded_pkgs, installed_pkgs)

    return web.json_response(
        {
            "packages": sorted(
                pkgs, key=lambda p: (p["description"], p["name"], p["version"])
            )
        }
    )


@app.http_post("/api/addon/install")
@addon_handler
async def addon_install(request):
    params = await request.json()
    app.logger.info("Installing addon: %s", params)

    pkg_name = params.get("package_name")
    if not pkg_name:
        return web.Response(text="Missing package_name", status=400)

    pkg_version = params.get("package_version")
    if not pkg_version:
        return web.Response(text="Missing package_version", status=400)

    ret = app.osal.InstallAddonPackage(pkg_name, pkg_version)
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)

    return web.json_response(
        {
            "ok": True,
        }
    )


@app.http_post("/api/addon/remove")
@addon_handler
async def addon_remove(request):
    params = await request.json()
    app.logger.info("Removing addon: %s", params)

    pkg_name = params.get("package_name")
    if not pkg_name:
        return web.Response(text="Missing package_name", status=400)

    pkg_version = params.get("package_version")
    if not pkg_version:
        return web.Response(text="Missing package_version", status=400)

    ret = app.osal.RemoveAddonPackage(pkg_name, pkg_version)
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)

    return web.json_response(
        {
            "ok": True,
        }
    )


@app.http_get("/api/addon/history")
@addon_handler
async def addon_history(request):
    n = int(request.query.get("n") or 10)
    histfile = Path("/opt/roche/var/log/rlx-addon-history.log")
    fieldnames = ["time", "package", "version", "action", "success"]
    history = []
    if histfile.exists():
        with histfile.open("r") as fid:
            r = csv.DictReader(fid, fieldnames=fieldnames, delimiter=";")
            history = list(tail(n, r))
    history.reverse()
    return web.json_response({"history": history})
