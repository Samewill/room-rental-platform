from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, SecretStr, StringConstraints


FullName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
]
PhoneNumber = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=20),
]
BusinessName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
]


class RegisterRequest(BaseModel):
    full_name: FullName
    phone_no: PhoneNumber
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=128)
    business_name: BusinessName | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(gt=0)
