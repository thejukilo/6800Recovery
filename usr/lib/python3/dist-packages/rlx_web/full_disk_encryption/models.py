from pydantic import BaseModel


class ChangePassphraseRequest(BaseModel):
    old_passphrase: str
    new_passphrase: str
