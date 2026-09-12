"""Primitivas de seguridad: hashing de contraseñas, JWT y TOTP.

Implementa lo descrito en plan/plan.md seccion 2.A y 2.B.9: Argon2id como
esquema principal de hashing, JWT de acceso de vida corta + refresh token
rotativo, y helpers de TOTP para MFA.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import pyotp
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


import uuid


def _create_token(subject: str, expires_delta: timedelta, token_type: str,
                   extra_claims: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": uuid.uuid4().hex,
    }
    if extra_claims:
        payload.update({k: v for k, v in extra_claims.items() if v is not None})
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    subject: str, clinic_id: str | None = None, role: str | None = None, email: str | None = None
) -> str:
    return _create_token(
        subject,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
        extra_claims={"clinic_id": clinic_id, "role": role, "email": email},
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(subject, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), token_type="refresh")


def create_password_reset_token(subject: str) -> str:
    return _create_token(subject, timedelta(hours=1), token_type="password_reset")


def create_invitation_token(subject: str, clinic_id: str) -> str:
    return _create_token(subject, timedelta(hours=48), token_type="doctor_invitation", extra_claims={"clinic_id": clinic_id})



def decode_token(token: str) -> dict[str, Any]:
    """Lanza jose.JWTError si el token es invalido o expiro."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def is_token_type(payload: dict[str, Any], expected_type: str) -> bool:
    return payload.get("type") == expected_type


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)


__all__ = [
    "JWTError",
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "create_password_reset_token",
    "create_invitation_token",
    "decode_token",
    "is_token_type",
    "generate_totp_secret",
    "verify_totp",
]
