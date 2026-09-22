from aiohttp import web
from datetime import datetime, timedelta
from .app_api import app, OSAL_OK
from rlx_osal import OSAL_HTTPS_DISABLED, OSAL_HTTPS_INTERNAL, OSAL_HTTPS_EXTERNAL
import OpenSSL.crypto
from os import makedirs
from pathlib import Path
from random import randrange
import pem


@app.http_get("/api/https-control")
@app.authenticated
async def getHttpsCertificates(request):
    ret = app.osal.GetHTTPSStatus()
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)
    internal = Path("/etc/ssl/rlx-certificate.pem")
    if ret.response.mode == 1 or internal.exists():
        modes = {
            "Do not use https": 0,
            "Use internal certificate": 1,
            "Upload external certificate": 2,
        }
    else:
        modes = {"Do not use https": 0, "Upload external certificate": 2}
    modes_status = [
        "HTTPS is not in use",
        "Using internal certificate",
        "Using custom certificate",
    ]
    certs = pem.parse(ret.response.certificates.encode())
    d = {
        "modes": modes,
        "mode": ret.response.mode,
        "status": modes_status[ret.response.mode],
        "certificates": certs[-1].as_text() if len(certs) > 0 else "",
        "redirect_http": ret.response.redirectHttp,
    }
    return web.json_response(d)


@app.http_post("/api/https-control/create-self-signed")
@app.authenticated
async def createHttpsCertificates(request):
    post_data = await request.post()
    ipaddress = post_data.get("ipaddress", "127.0.0.1")
    ipaddress_list = ipaddress.split(",")
    hostname = post_data.get("hostname", "localhost")
    hostname_list = hostname.split(",")
    if "localhost" not in hostname_list:
        hostname_list.append("localhost")
    if "127.0.0.1" not in ipaddress_list:
        ipaddress_list.append("127.0.0.1")

    if (
        Path("/opt/roche/home/ssl/ca-certificate-key.pem").exists()
        and Path("/opt/roche/home/ssl/ca-certificate.pem").exists()
    ):
        with open("/opt/roche/home/ssl/ca-certificate-key.pem", "rb") as pk:
            ca_pkey = pk.read()
            ckey = OpenSSL.crypto.load_privatekey(
                OpenSSL.crypto.FILETYPE_PEM, ca_pkey, b""
            )
        with open("/opt/roche/home/ssl/ca-certificate.pem", "rb") as cac:
            ca_cert = cac.read()
            ca = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, ca_cert)
    else:
        try:
            ckey = OpenSSL.crypto.PKey()
            ckey.generate_key(OpenSSL.crypto.TYPE_RSA, 4096)
            ca = OpenSSL.crypto.X509()
            ca.set_version(2)
            ca.set_pubkey(ckey)
            ca.set_serial_number(1)
            ca.gmtime_adj_notBefore(0)
            ca.set_notAfter(b"20991231235959Z")
            subj = ca.get_subject()
            subj.CN = "Self-Signed Instrument CA"
            ca.set_issuer(subj)
            ca.add_extensions(
                [
                    OpenSSL.crypto.X509Extension(
                        b"subjectKeyIdentifier", False, b"hash", subject=ca
                    ),
                ]
            )
            ca.add_extensions(
                [
                    OpenSSL.crypto.X509Extension(b"basicConstraints", True, b"CA:TRUE"),
                    OpenSSL.crypto.X509Extension(
                        b"keyUsage", True, b"keyCertSign, digitalSignature, cRLSign"
                    ),
                    OpenSSL.crypto.X509Extension(
                        b"authorityKeyIdentifier",
                        False,
                        b"keyid:always,issuer",
                        issuer=ca,
                    ),
                ]
            )
            ca.sign(ckey, "sha512")
            ca_cert = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, ca)
            ca_pkey = OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, ckey)
        except Exception as exc:
            app.logger.exception(exc)
            return web.Response(
                text="failure while generating self-signed certificate", status=500
            )

    try:
        pkey = OpenSSL.crypto.PKey()
        pkey.generate_key(OpenSSL.crypto.TYPE_RSA, 4096)
        cert = OpenSSL.crypto.X509()
        cert.set_version(2)
        subj = cert.get_subject()
        subj.CN = hostname_list[0]
        cert.set_issuer(ca.get_subject())
        cert.set_serial_number(randrange(2, 2**64))
        cert.gmtime_adj_notBefore(0)
        cert.set_notAfter(
            (datetime.now() + timedelta(days=7300)).strftime("%Y%m%d%H%M%SZ").encode()
        )
        cert.set_pubkey(pkey)
        cert.add_extensions(
            [
                OpenSSL.crypto.X509Extension(
                    b"subjectKeyIdentifier", False, b"hash", subject=cert
                ),
            ]
        )
        subjectAltName = []
        for host in hostname_list:
            subjectAltName.append("DNS:{}".format(host.strip()))
        for ip in ipaddress_list:
            subjectAltName.append("IP:{}".format(ip.strip()))
        cert.add_extensions(
            [
                OpenSSL.crypto.X509Extension(b"basicConstraints", True, b"CA:FALSE"),
                OpenSSL.crypto.X509Extension(
                    b"keyUsage",
                    True,
                    b"nonRepudiation, digitalSignature, keyEncipherment, keyAgreement",
                ),
                OpenSSL.crypto.X509Extension(b"extendedKeyUsage", True, b"serverAuth"),
                OpenSSL.crypto.X509Extension(
                    b"authorityKeyIdentifier", False, b"keyid:always, issuer", issuer=ca
                ),
                OpenSSL.crypto.X509Extension(
                    b"subjectAltName", False, ", ".join(subjectAltName).encode()
                ),
            ]
        )
        cert.sign(ckey, "sha512")
        chain = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
        pkey = OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, pkey)
    except Exception as exc:
        app.logger.exception(exc)
        return web.Response(
            text="failure while generating self-signed certificate", status=500
        )

    try:
        makedirs("/opt/roche/home/ssl", exist_ok=True)
        with open("/opt/roche/home/ssl/ca-certificate.pem", "wb") as out:
            out.write(ca_cert)
        with open("/opt/roche/home/ssl/ca-certificate-key.pem", "wb") as out:
            out.write(ca_pkey)
        with open("/opt/roche/home/ssl/custom-certificate.pem", "wb") as out:
            out.write(chain)
            out.write(ca_cert)
        with open("/opt/roche/home/ssl/custom-certificate-key.pem", "wb") as out:
            out.write(pkey)
    except Exception as exc:
        app.logger.exception(exc)
        return web.Response(text="failure while saving certificate", status=500)

    ret = app.osal.ChangeHTTPSMode(OSAL_HTTPS_EXTERNAL)
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)

    return web.Response()


def enableHttps():
    ret = app.osal.ChangeHTTPSMode(OSAL_HTTPS_INTERNAL)
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)
    return web.Response()


def disableHttps():
    ret = app.osal.ChangeHTTPSMode(OSAL_HTTPS_DISABLED)
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)
    return web.Response()


def customHttps(post_data):
    pfx_password = post_data.get("pfx_password", None)
    if not pfx_password:
        return web.Response(text="pfx password is required", status=400)
    pfx = post_data.get("pfx", None)
    if not pfx:
        return web.Response(text="pfx certificate is required", status=400)
    fileContent = b""
    try:
        fileContent = pfx.file.read()
    except Exception:
        return web.Response(text="unable to read pfx certificate", status=400)

    try:
        pkcs12 = OpenSSL.crypto.load_pkcs12(fileContent, pfx_password)
        pkey = OpenSSL.crypto.dump_privatekey(
            OpenSSL.crypto.FILETYPE_PEM, pkcs12.get_privatekey()
        )
        chain = b""
        raw_ca = pkcs12.get_ca_certificates()
        if raw_ca:
            for raw_cert in raw_ca:
                chain += OpenSSL.crypto.dump_certificate(
                    OpenSSL.crypto.FILETYPE_PEM, raw_cert
                )
        cert = OpenSSL.crypto.dump_certificate(
            OpenSSL.crypto.FILETYPE_PEM, pkcs12.get_certificate()
        )
    except Exception as exc:
        app.logger.exception(exc)
        return web.Response(text="invalid certificate or password", status=400)

    try:
        makedirs("/opt/roche/home/ssl", exist_ok=True)
        with open("/opt/roche/home/ssl/custom-certificate.pem", "wb") as out:
            out.write(cert)
            out.write(chain)
        with open("/opt/roche/home/ssl/custom-certificate-key.pem", "wb") as out:
            out.write(pkey)
    except Exception as exc:
        app.logger.exception(exc)
        return web.Response(text="failure while saving certificate", status=500)

    ret = app.osal.ChangeHTTPSMode(OSAL_HTTPS_EXTERNAL)
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)

    return web.Response()


@app.http_post("/api/https-control")
@app.authenticated
async def configureHTTPS(request):
    post_data = await request.post()
    mode = post_data.get("mode", None)
    try:
        mode = int(mode)
    except Exception:
        return web.Response(text="invalid mode type", status=400)
    if mode == OSAL_HTTPS_DISABLED:
        return disableHttps()
    elif mode == OSAL_HTTPS_INTERNAL:
        return enableHttps()
    elif mode == OSAL_HTTPS_EXTERNAL:
        return customHttps(post_data)
    return web.Response(text="invalid mode", status=400)


@app.http_post("/api/http-redirect")
@app.authenticated
async def redirectHTTP(request):
    json_data = await request.json()
    enable = json_data.get("redirect_http", None)
    if enable is None:
        return web.Response(text="invalid request", status=400)
    if enable:
        ret = app.osal.EnableHTTPRedirect()
    else:
        ret = app.osal.DisableHTTPRedirect()
    if ret.outcome != OSAL_OK:
        return web.Response(text=str(ret.errorMessage), status=500)
    return web.Response()
