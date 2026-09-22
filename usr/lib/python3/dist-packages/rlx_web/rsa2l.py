from .app_api import app
from rlx_osal.osal import OSAL
from aiohttp import web
from rlx_osal import OSAL_OK


@app.http_get("/api/rsa2l/settings")
@app.authenticated
async def getRSA2LSettings(request):
    ret = OSAL().GetRSA2LSettings()
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)
    response = {
        "basic": {
            "gateway_ip": ret.response.basic.gatewayIP,
            "gateway_port": ret.response.basic.gatewayPort,
        },
        "download": {
            "download_enabled": ret.response.download.downloadEnabled,
            "download_rule": ret.response.download.downloadRule,
            "monitor_folders": ret.response.download.monitorFolders,
            "max_download_retries": ret.response.download.maxDownloadRetries,
            "high_water_mark_maxlimit": ret.response.download.highWaterMarkMaxlimit,
            "high_water_mark_action": ret.response.download.highWaterMarkAction,
            "warninglimit_maxlimit": ret.response.download.warninglimitMaxlimit,
            "warninglimit_send_alarm": ret.response.download.warninglimitSendAlarm,
        },
        "upload": {
            "upload_enabled": ret.response.upload.uploadEnabled,
            "max_upload_retries": ret.response.upload.maxUploadRetries,
            "upload_folder_scan_interval": ret.response.upload.uploadFolderScanInterval,
            "retention_period": ret.response.upload.retentionPeriod,
            "high_water_mark_maxlimit": ret.response.upload.highWaterMarkMaxlimit,
            "high_water_mark_action": ret.response.upload.highWaterMarkAction,
            "warninglimit_maxlimit": ret.response.upload.warninglimitMaxlimit,
            "warninglimit_send_alarm": ret.response.upload.warninglimitSendAlarm,
        },
        "log": {
            "retention_period": ret.response.log.retentionPeriod,
            "max_log_file_size": ret.response.log.maxLogFileSize,
            "log_debug": ret.response.log.logDebug,
        },
    }
    return web.json_response(response)


@app.http_patch("/api/rsa2l/settings")
@app.authenticated
async def configureRSA2L(request):
    data = await request.json()

    failures = []

    if "basic" in data:
        try:
            ret = OSAL().ConfigureRSA2LGateway(
                data["basic"]["gateway_ip"],
                data["basic"]["gateway_port"],
            )

            if ret.outcome != OSAL_OK:
                failures.append(
                    (500, f"Failed to apply basic settings: {ret.errorMessage}")
                )
        except KeyError as e:
            failures.append((400, str(e)))

    if "download" in data:
        try:
            ret = OSAL().ConfigureRSA2LDownloadSettings(
                data["download"]["download_enabled"],
                data["download"]["download_rule"],
                data["download"]["monitor_folders"],
                data["download"]["max_download_retries"],
                data["download"]["high_water_mark_maxlimit"],
                data["download"]["high_water_mark_action"],
                data["download"]["warninglimit_maxlimit"],
                data["download"]["warninglimit_send_alarm"],
            )

            if ret.outcome != OSAL_OK:
                failures.append(
                    (500, f"Failed to apply download settings: {ret.errorMessage}")
                )
        except KeyError as e:
            failures.append((400, str(e)))

    if "upload" in data:
        try:
            ret = OSAL().ConfigureRSA2LUploadSettings(
                data["upload"]["upload_enabled"],
                data["upload"]["max_upload_retries"],
                data["upload"]["upload_folder_scan_interval"],
                data["upload"]["retention_period"],
                data["upload"]["high_water_mark_maxlimit"],
                data["upload"]["high_water_mark_action"],
                data["upload"]["warninglimit_maxlimit"],
                data["upload"]["warninglimit_send_alarm"],
            )

            if ret.outcome != OSAL_OK:
                failures.append(
                    (500, f"Failed to apply upload settings: {ret.errorMessage}")
                )
        except KeyError as e:
            failures.append((400, str(e)))

    if "log" in data:
        try:
            ret = OSAL().ConfigureRSA2LLogSettings(
                data["log"]["retention_period"],
                data["log"]["max_log_file_size"],
                data["log"]["log_debug"],
            )

            if ret.outcome != OSAL_OK:
                failures.append(
                    (500, f"Failed to apply log settings: {ret.errorMessage}")
                )
        except KeyError as e:
            failures.append((400, str(e)))

    if len(failures) == 0:
        return web.Response()
    else:
        codes, messages = zip(*failures)
        return web.Response(text=", ".join(messages), status=max(codes))
