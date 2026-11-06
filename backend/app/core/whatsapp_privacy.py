import base64
import binascii
import hashlib
import hmac
import os
import re

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

from app.core.config import get_settings


_PHONE_NUMBER_PATTERN = re.compile(
    r"(?<![0-9])\+?(?:[0-9][\s()./-]*){8,}",
)
_E164_PATTERN = re.compile(r"^\+[1-9][0-9]{7,14}$")
_PHONE_AAD = b"room-rental-platform:whatsapp-phone:v1"


def normalize_phone_number(phone_number: str) -> str:
    normalized = phone_number.strip()
    if not _E164_PATTERN.fullmatch(normalized):
        raise ValueError("Phone number must be in E.164 format.")
    return normalized


def contains_phone_number(content: str) -> bool:
    return any(
        sum(character.isascii() and character.isdigit() for character in match.group())
        >= 8
        for match in _PHONE_NUMBER_PATTERN.finditer(content)
    )


def redact_phone_numbers(content: str) -> str:
    return _PHONE_NUMBER_PATTERN.sub("[phone number removed]", content)


def _secret(name: str) -> bytes:
    settings = get_settings()
    value = getattr(settings, name)
    if value is None:
        raise RuntimeError(f"{name} must be configured.")
    return value.get_secret_value().encode("utf-8")


def _encryption_key() -> bytes:
    encoded = _secret("whatsapp_phone_encryption_key")
    try:
        key = base64.urlsafe_b64decode(encoded)
    except (ValueError, binascii.Error) as exc:
        raise RuntimeError(
            "WhatsApp phone encryption key must be URL-safe base64.",
        ) from exc
    if len(key) != 32:
        raise RuntimeError(
            "WhatsApp phone encryption key must decode to 32 bytes.",
        )
    return key


def encrypt_phone_number(phone_number: str) -> str:
    nonce = os.urandom(12)
    ciphertext = AESGCM(_encryption_key()).encrypt(
        nonce,
        phone_number.encode("utf-8"),
        _PHONE_AAD,
    )
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_phone_number(encrypted_phone: str) -> str:
    try:
        value = base64.urlsafe_b64decode(encrypted_phone.encode("ascii"))
        nonce, ciphertext = value[:12], value[12:]
        return AESGCM(_encryption_key()).decrypt(
            nonce,
            ciphertext,
            _PHONE_AAD,
        ).decode("utf-8")
    except (InvalidTag, ValueError, UnicodeDecodeError, binascii.Error) as exc:
        raise RuntimeError("Stored WhatsApp phone mapping is invalid.") from exc


def phone_lookup_hash(phone_number: str) -> str:
    key = _lookup_key()
    return hmac.new(
        key,
        phone_number.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def verification_code_hash(user_id: int, code: str) -> str:
    payload = f"whatsapp-verification:{user_id}:{code}".encode("ascii")
    return hmac.new(
        _lookup_key(),
        payload,
        hashlib.sha256,
    ).hexdigest()


def _lookup_key() -> bytes:
    key = _secret("whatsapp_phone_lookup_key")
    if len(key) < 32:
        raise RuntimeError(
            "WhatsApp phone lookup key must be at least 32 bytes.",
        )
    return key
