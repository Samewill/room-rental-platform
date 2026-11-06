from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints


PhoneNumber = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^\+[1-9][0-9]{7,14}$",
    ),
]
VerificationCode = Annotated[
    str,
    StringConstraints(pattern=r"^[0-9]{6}$"),
]


class WhatsAppVerificationStartRequest(BaseModel):
    phone_number: PhoneNumber
    consent: Literal[True]


class WhatsAppVerificationConfirmRequest(BaseModel):
    code: VerificationCode


class WhatsAppStatusResponse(BaseModel):
    enabled: bool
