from json import JSONDecodeError
from pydantic import ValidationError
from rlx_web.app_api import app
from rlx_osal import OSAL_OK
from aiohttp.web import Request, Response, json_response
from rlx_web.full_disk_encryption.models import ChangePassphraseRequest
from functools import wraps
from rlx_web.full_disk_encryption.constants import PLUGIN, CAPABILITY
from http import HTTPStatus
from ..shared import generic_request_handler


disk_encryption_handler = generic_request_handler(
    PLUGIN, CAPABILITY, authenticated=True
)


@app.http_post("/api/disk-encryption/change-passphrase")
@disk_encryption_handler
async def change_passphrase(request):
    try:
        data = ChangePassphraseRequest(**await request.json())
        ret = app.osal.ChangePassphraseEncryptedStorage(
            data.old_passphrase, data.new_passphrase
        )
        if ret.outcome != OSAL_OK:
            return Response(status=HTTPStatus.BAD_REQUEST, text=str(ret.errorMessage))
        return Response()
    except JSONDecodeError:
        return Response(status=HTTPStatus.BAD_REQUEST, text="Missing request data")
    except ValidationError as e:
        return json_response(
            status=HTTPStatus.BAD_REQUEST, reason="Received invalid data", data=e.json()
        )
