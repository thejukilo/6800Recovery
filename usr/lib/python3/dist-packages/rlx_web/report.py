"""System reports.

Generate and download system reports.

"""

from datetime import datetime
import os

from aiohttp import web, hdrs

from .app_api import app
from .utils import remove_file


@app.http_get("/api/report/prepare")
@app.authenticated
async def systemReportPrepare(request):
    """Generate a system report, ready to be downloaded.

    Store the path to the generated report in the user's session.
    Note: call this method *before* trying to download the report.

    """
    logdays = app.get_argument(request, "logdays")
    try:
        logdays = int(logdays)
    except Exception:
        return web.Response(text="Internal Error: int logdays", status=500)

    reportamount = app.get_argument(request, "reportamount")
    try:
        reportamount = int(reportamount)
    except Exception:
        return web.Response(text="Internal Error: int reportamount", status=500)

    filelist_str = app.get_argument(request, "filelist")
    filelist = False
    if filelist_str == "true":
        filelist = True

    rlxsystemreport_str = app.get_argument(request, "rlxsystemreport")
    rlxsystemreport = False
    if rlxsystemreport_str == "true":
        rlxsystemreport = True

    rlxintegritycheck_str = app.get_argument(request, "rlxintegritycheck")
    rlxintegritycheck = False
    if rlxintegritycheck_str == "true":
        rlxintegritycheck = True

    applicationLogs_str = app.get_argument(request, "applicationLogs")
    applicationLogs = False
    if applicationLogs_str == "true":
        applicationLogs = True

    ret = app.execute_osal(
        "CreateSystemReport",
        "",
        logdays,
        filelist,
        rlxsystemreport,
        applicationLogs,
        reportamount,
        rlxintegritycheck,
    )  # use OSAL to create filename
    fname = ret.response.filename
    if not fname:
        return web.Response(text="Internal Error: fname empty", status=400)
    directory = ret.response.directory
    if not directory:
        return web.Response(text="Internal Error: directory empty", status=500)

    request.cirrina.web_session["system_report_path"] = os.path.join(directory, fname)
    return web.Response()


@app.http_get("/api/report/download")
@app.authenticated
async def systemReportDownload(request):
    """Download a previously generated system report and/or application logs file only."""

    fname = request.cirrina.web_session.get("system_report_path")
    if not fname:
        raise web.HTTPBadRequest(reason=f"Missing system report path: {fname}")
    if not os.path.isfile(fname):
        raise web.HTTPInternalServerError(text=f"Invalid system report path: {fname}")

    reportname = os.path.basename(fname)
    if os.path.islink(fname):
        reportname = os.path.basename(os.readlink(fname))

    headers = {
        hdrs.CACHE_CONTROL: "no-cache, no-store, must-revalidate",
        hdrs.CONTENT_DISPOSITION: "attachment; filename=" + reportname,
        hdrs.CONTENT_TYPE: "application/zip",
        hdrs.EXPIRES: "0",
        hdrs.PRAGMA: "no-cache",
    }

    resp = web.FileResponse(fname, headers=headers)

    # Note: Internally prepare calls write_eof which means afterwards no further modifications of the response are allowed
    await resp.prepare(request)
    # Ensure that the response has been sent before proceeding with the cleanup
    await resp.write_eof()

    if os.path.islink(fname):
        await remove_file(os.path.dirname(fname) + "/" + os.readlink(fname), app.logger)

    await remove_file(fname, app.logger)

    try:
        del request.cirrina.web_session["system_report_path"]
    except Exception:
        pass

    return web.Response()


@app.http_post("/api/report/usb")
@app.authenticated
async def systemReportToUSB(request):
    """Generate and store a system report to USB."""

    params = await request.json()

    devname = params.get("devname", None)
    if devname is None:
        return web.Response(text="devname is None", status=400)

    logdays = params.get("logdays", None)
    if logdays is None:
        return web.Response(text="Internal Error: logdays", status=400)
    try:
        logdays = int(logdays)
    except Exception:
        return web.Response(text="Internal Error: int logdays", status=500)

    filelist_str = params.get("filelist", None)
    if filelist_str is None:
        return web.Response(text="Internal Error: filelist", status=400)
    filelist = False
    if filelist_str == "true":
        filelist = True

    rlxsystemreport_str = params.get("rlxsystemreport", None)
    if rlxsystemreport_str is None:
        return web.Response(text="Internal Error: rlxsystemreport", status=400)
    rlxsystemreport = False
    if rlxsystemreport_str == "true":
        rlxsystemreport = True

    applicationLogs_str = params.get("applicationLogs", None)
    if applicationLogs_str is None:
        return web.Response(text="Internal Error: applicationLogs", status=400)
    applicationLogs = False
    if applicationLogs_str == "true":
        applicationLogs = True

    reportamount = params.get("reportamount", None)
    if reportamount is None:
        return web.Response(text="Internal Error: reportamount", status=400)
    try:
        reportamount = int(reportamount)
    except Exception:
        return web.Response(text="Internal Error: int reportamount", status=500)

    rlxintegritycheck_str = params.get("rlxintegritycheck", None)
    if rlxintegritycheck_str is None:
        return web.Response(text="Internal Error: rlxintegritycheck", status=400)
    rlxintegritycheck = False
    if rlxintegritycheck_str == "true":
        rlxintegritycheck = True

    tstamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    try:
        with open(
            "/opt/roche/etc/projectinfo", "r"
        ) as f:  # FIXME: rename to rlx-project-info, make key/value file
            name = f.read().strip().split("/")[0]
    except OSError:
        name = ""

    ver = None
    try:
        with open("/opt/roche/etc/project-version", "r") as f:
            ver = f.read().rstrip("\n").strip()
    except OSError:
        pass

    if not ver:  # try obsolete file
        try:
            with open("/opt/roche/etc/rlx-project-release", "r") as f:
                ver = f.read().rstrip("\n").strip()
        except OSError:
            ver = ""

    filename = "SystemReport_" + name + "_" + ver + "_" + tstamp + ".zip"

    ret = app.execute_osal(
        "CreateSystemReport",
        filename,
        logdays,
        filelist,
        rlxsystemreport,
        applicationLogs,
        reportamount,
        rlxintegritycheck,
    )
    fname = ret.response.filename
    if not fname:
        return web.Response(text="Internal Error", status=500)
    directory = ret.response.directory
    if not directory:
        return web.Response(text="Internal Error", status=500)

    if os.path.isfile(directory + "/" + fname):
        app.execute_osal(
            "CopyFilesToUSBStorage", devname, [directory + "/" + fname], "systemreports"
        )
        await remove_file(directory + "/" + fname, app.logger)
        return web.Response()
    return web.Response(text="Internal Error", status=500)
