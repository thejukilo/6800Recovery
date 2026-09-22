import functools

from aiohttp import web

from .app_api import app
from .shared import generic_request_handler


external_storage_handler = generic_request_handler(
    "rlx_osal.plugins.external_storage_pb2", "web-external-storage", authenticated=True
)


@app.http_get("/api/external-storage/list")
@external_storage_handler
async def getExternalStorageList(request):
    from rlx_osal.plugins.external_storage_pb2 import ExternalStorageInfo

    ret = app.execute_osal("GetExternalStorageList")
    GB = 1024 * 1024 * 1024
    result = []
    for storage in ret.response.storage:
        d = {
            "id": storage.id,
            "description": storage.description,
            "url": storage.url,
            "configured": storage.configured,
            "mounted": storage.mounted,
            "sizeTotal": float(storage.sizeTotal / GB),
            "sizeUsed": float(storage.sizeUsed / GB),
            "sizeFree": float(storage.sizeFree / GB),
            "percent": (
                int(float(storage.sizeUsed) / float(storage.sizeTotal) * 100.0)
                if storage.mounted
                and storage.status == ExternalStorageInfo.Status.OK
                and storage.sizeTotal > 0
                else 0
            ),
            "writePermissions": storage.writePermissions,
            "nasType": storage.nasType,
            "status": storage.status,
        }

        result.append(d)
    return web.json_response(result)


@app.http_post("/api/external-storage/configure")
@external_storage_handler
async def configureExternalStorage(request):
    params = await request.json()
    url = app.get_param(params, "url")
    id = app.get_param(params, "id")
    if not url:
        return web.Response(
            text="Please provide an url.",
            status=400,
        )
    app.execute_osal("ConfigureExternalStorage", url, id)
    return web.Response()


@app.http_delete("/api/external-storage/disconnect")
@external_storage_handler
async def disconnectExternalStorage(request):
    params = await request.json()
    id = app.get_param(params, "id")
    app.execute_osal("DisconnectExternalStorage", id)
    return web.Response()


@app.http_post("/api/external-storage")
@external_storage_handler
async def addExternalStorage(request):
    params = await request.json()

    app.execute_osal(
        "AddExternalStorageMountPoint",
        params["path"],
        params["description"],
        params["options"].split(",") if params["options"] != "" else [],
    )
    return web.Response()


@app.http_delete(r"/api/external-storage/{id:\d+}")
@external_storage_handler
async def deleteExternalStorage(request):
    app.execute_osal("RemoveExternalStorageMountPoint", int(request.match_info["id"]))
    return web.Response()
