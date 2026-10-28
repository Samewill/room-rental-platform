from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from jwt import InvalidTokenError

from app.core.config import get_settings


_password_hash = PasswordHash.recommended()
_jwt_algorithm = "HS256"


def _get_jwt_secret() -> str:
    secret_setting = get_settings().jwt_secret_key
    if secret_setting is None:
        raise RuntimeError("JWT_SECRET_KEY must be configured to issue tokens.")

    secret = secret_setting.get_secret_value()
    if len(secret.encode("utf-8")) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be at least 32 bytes long.")

    return secret


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return _password_hash.verify(password, hashed_password)


def create_access_token(user_id: int) -> str:
    if user_id <= 0:
        raise ValueError("user_id must be a positive integer.")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        minutes=get_settings().access_token_expire_minutes,
    )
    claims = {
        "sub": str(user_id),
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(claims, _get_jwt_secret(), algorithm=_jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    try:
        claims = jwt.decode(
            token,
            _get_jwt_secret(),
            algorithms=[_jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
    except InvalidTokenError:
        return None

    subject = claims.get("sub")
    if not isinstance(subject, str):
        return None

    try:
        user_id = int(subject)
    except ValueError:
        return None

    return user_id if user_id > 0 else None