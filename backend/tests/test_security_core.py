"""Pruebas de las primitivas de seguridad que no requieren base de datos.

Las pruebas de integracion completas (login/refresh contra MySQL real,
rotacion y deteccion de reuso de refresh tokens) se añaden junto con el
Modulo 1.5 en cuanto el stack de docker compose este disponible en CI
(ver plan/plan.md Modulo 7 - "Suite completa de Pytest").
"""

import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_totp_secret,
    hash_password,
    verify_password,
    verify_totp,
)


def test_password_hash_roundtrip():
    hashed = hash_password("Sup3rSecreta!")
    assert hashed != "Sup3rSecreta!"
    assert verify_password("Sup3rSecreta!", hashed)
    assert not verify_password("otra-clave", hashed)


def test_access_token_roundtrip():
    token = create_access_token("user-123", clinic_id="clinic-abc", role="DOCTOR")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert payload["clinic_id"] == "clinic-abc"
    assert payload["role"] == "DOCTOR"


def test_refresh_token_type():
    token = create_refresh_token("user-123")
    payload = decode_token(token)
    assert payload["type"] == "refresh"


def test_totp_roundtrip():
    import pyotp

    secret = generate_totp_secret()
    code = pyotp.TOTP(secret).now()
    assert verify_totp(secret, code)
    assert not verify_totp(secret, "000000")
