import functools

from aiohttp import web
from .app_api import app
from .shared import generic_request_handler


openvpn_handler = generic_request_handler(
    "rlx_osal.plugins.openvpn_pb2", "web-openvpn", authenticated=True
)


@app.http_get("/api/openvpn")
@openvpn_handler
async def getOpenVPNStatus(request):
    ret = app.execute_osal("GetOpenVPNConnectionStatus")
    d = {
        "enabled": ret.response.enabled,
        "active": ret.response.active,
        "exists": ret.response.exists,
        "ip": ret.response.ip,
    }
    return web.json_response(d)


@app.http_post("/api/openvpn")
@openvpn_handler
async def enableOpenVPN(request):
    app.execute_osal("EnableOpenVPNConnection")
    return web.Response()


@app.http_delete("/api/openvpn")
@openvpn_handler
async def disableOpenVPN(request):
    app.execute_osal("DisableOpenVPNConnection")
    return web.Response()


async def configure_openvpn(settings):
    remoteAddress = app.get_param(settings, "remote_address")
    remotePort = app.get_param(settings, "port")
    x509Name = app.get_param(settings, "x509_name")
    CARootCert = app.get_param(settings, "ca_root_cert")
    psk = app.get_param(settings, "psk")
    clientCert = app.get_param(settings, "client_cert")
    clientPrivKey = app.get_param(settings, "client_private_key")

    app.execute_osal(
        "ConfigureOpenVPNConnection",
        remoteAddress,
        int(remotePort),
        x509Name,
        CARootCert.replace("\r", ""),
        psk.replace("\r", ""),
        clientCert.replace("\r", ""),
        clientPrivKey.replace("\r", ""),
    )
    # restart OpenVPNConnection
    app.execute_osal("DisableOpenVPNConnection")
    app.execute_osal("EnableOpenVPNConnection")


@app.http_post("/api/openvpn/configure")
@openvpn_handler
async def configureOpenVPN(request):
    params = await request.json()

    remoteAddress = app.get_param(params, "remoteAddress")
    remotePort = app.get_param(params, "remotePort")
    x509Name = app.get_param(params, "x509Name")
    CARootCert = app.get_param(params, "CARootCert")
    psk = app.get_param(params, "psk")
    clientCert = app.get_param(params, "clientCert")
    clientPrivKey = app.get_param(params, "clientPrivKey")

    app.execute_osal(
        "ConfigureOpenVPNConnection",
        remoteAddress,
        int(remotePort),
        x509Name,
        CARootCert.replace("\r", ""),
        psk.replace("\r", ""),
        clientCert.replace("\r", ""),
        clientPrivKey.replace("\r", ""),
    )
    # restart OpenVPNConnection
    app.execute_osal("DisableOpenVPNConnection")
    app.execute_osal("EnableOpenVPNConnection")
    app.reset_launch_code()
    return web.Response()
