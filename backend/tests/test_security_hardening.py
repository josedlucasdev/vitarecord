"""Endurecimiento de autenticacion y superficies publicas (plan/plan.md 2.B.9 y 2.B.10).

- Backoff exponencial y bloqueo temporal de login.
- MFA obligatorio por rol y por politica de clinica (recepcionistas).
- Login social emulado deshabilitado por defecto.
- Firma obligatoria en el webhook de WhatsApp cuando hay app secret.
- Validaciones de arranque en produccion.
"""

import hashlib
import hmac
import json
import uuid

import pyotp
import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from app.core import login_guard
from app.core.config import Settings, settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.clinic import Clinic
from app.models.user import RefreshToken, User

CLINIC_1 = "c1111111-1111-1111-1111-111111111111"
FORM = {"content-type": "application/x-www-form-urlencoded"}


async def _create_user(role: str, clinic_id: str | None = None) -> tuple[str, str]:
    email = f"sec_{role.lower()}_{uuid.uuid4().hex[:10]}@example.com"
    async with AsyncSessionLocal() as session:
        user = User(
            email=email,
            full_name=f"Usuario prueba {role}",
            hashed_password=hash_password("Password123!"),
            role=role,
            status="ACTIVE",
            clinic_id=clinic_id,
            license_verification_status="VERIFIED" if role == "DOCTOR" else "NOT_APPLICABLE",
        )
        session.add(user)
        await session.commit()
        return user.id, email


async def _delete_user(user_id: str) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def _login(client: AsyncClient, email: str, password: str = "Password123!", **extra):
    return await client.post("/api/v1/auth/login", data={"username": email, "password": password, **extra}, headers=FORM)


@pytest.mark.anyio
async def test_login_backoff_after_repeated_failures(client: AsyncClient):
    email = f"noexiste_{uuid.uuid4().hex[:8]}@example.com"
    for _ in range(3):
        resp = await _login(client, email, "incorrecta")
        assert resp.status_code == 401
    # Tras el 3er fallo consecutivo se exige esperar (backoff exponencial).
    resp = await _login(client, email, "incorrecta")
    assert resp.status_code == 429
    assert int(resp.headers["Retry-After"]) >= 1


@pytest.mark.anyio
async def test_login_lockout_blocks_even_correct_password(client: AsyncClient):
    user_id, email = await _create_user("PATIENT")
    try:
        for _ in range(settings.LOGIN_MAX_ATTEMPTS):
            await login_guard.register_login_failure(email, "10.0.0.1")
        resp = await _login(client, email)
        assert resp.status_code == 429
        assert "bloqueada" in resp.json()["detail"]
    finally:
        await login_guard.register_login_success(email)
        from app.core.redis import get_redis

        await get_redis().delete(f"login:lock:{email}", "login:ip:10.0.0.1")
        await _delete_user(user_id)


@pytest.mark.anyio
async def test_mfa_is_mandatory_for_privileged_roles(client: AsyncClient):
    user_id, email = await _create_user("CLINIC_ADMIN", CLINIC_1)
    settings.MFA_ENFORCEMENT_ENABLED = True
    try:
        login = await _login(client, email)
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        blocked = await client.get("/api/v1/appointments", headers=headers)
        assert blocked.status_code == 403
        assert blocked.json()["detail"].startswith("MFA_SETUP_REQUIRED")

        # Los endpoints de configuracion de MFA siguen disponibles.
        me = await client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200
        setup = await client.post("/api/v1/auth/mfa/setup", headers=headers)
        assert setup.status_code == 200
        secret = setup.json()["secret"]
        enable = await client.post(
            "/api/v1/auth/mfa/enable",
            json={"secret": secret, "code": pyotp.TOTP(secret).now()},
            headers=headers,
        )
        assert enable.status_code == 200

        allowed = await client.get("/api/v1/appointments", headers=headers)
        assert allowed.status_code == 200

        # Un rol con MFA obligatorio no puede desactivarlo.
        disable = await client.post("/api/v1/auth/mfa/disable", json={"password": "Password123!"}, headers=headers)
        assert disable.status_code == 403
    finally:
        settings.MFA_ENFORCEMENT_ENABLED = False
        await _delete_user(user_id)


@pytest.mark.anyio
async def test_receptionist_mfa_follows_clinic_policy(client: AsyncClient):
    user_id, email = await _create_user("RECEPTIONIST", CLINIC_1)
    settings.MFA_ENFORCEMENT_ENABLED = True
    try:
        login = await _login(client, email)
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        # Politica por defecto: MFA opcional para recepcionistas.
        assert (await client.get("/api/v1/appointments", headers=headers)).status_code == 200

        async with AsyncSessionLocal() as session:
            clinic = (await session.execute(select(Clinic).where(Clinic.id == CLINIC_1))).scalar_one()
            clinic.require_mfa_for_receptionists = True
            await session.commit()

        blocked = await client.get("/api/v1/appointments", headers=headers)
        assert blocked.status_code == 403
        assert blocked.json()["detail"].startswith("MFA_SETUP_REQUIRED")
    finally:
        settings.MFA_ENFORCEMENT_ENABLED = False
        async with AsyncSessionLocal() as session:
            clinic = (await session.execute(select(Clinic).where(Clinic.id == CLINIC_1))).scalar_one()
            clinic.require_mfa_for_receptionists = False
            await session.commit()
        await _delete_user(user_id)


@pytest.mark.anyio
async def test_dev_social_login_disabled_by_default(client: AsyncClient):
    settings.ALLOW_DEV_SOCIAL_LOGIN = False
    try:
        resp = await client.post("/api/v1/auth/facebook", json={"access_token": "dev_fb_123456789"})
        assert resp.status_code != 200
    finally:
        settings.ALLOW_DEV_SOCIAL_LOGIN = True


@pytest.mark.anyio
async def test_whatsapp_webhook_requires_valid_signature(client: AsyncClient):
    settings.WHATSAPP_APP_SECRET = "secreto_de_prueba"
    try:
        body = json.dumps({"object": "whatsapp_business_account", "entry": []}).encode()
        unsigned = await client.post(
            "/api/v1/webhooks/whatsapp", content=body, headers={"content-type": "application/json"}
        )
        assert unsigned.status_code == 403

        signature = "sha256=" + hmac.new(b"secreto_de_prueba", body, hashlib.sha256).hexdigest()
        signed = await client.post(
            "/api/v1/webhooks/whatsapp",
            content=body,
            headers={"content-type": "application/json", "X-Hub-Signature-256": signature},
        )
        assert signed.status_code == 200
    finally:
        settings.WHATSAPP_APP_SECRET = ""


def test_production_rejects_development_secrets():
    prod = Settings(ENVIRONMENT="production", JWT_SECRET_KEY="dev-only-change-me", ALLOW_DEV_SOCIAL_LOGIN=True)
    errors = prod.production_config_errors()
    assert any("JWT_SECRET_KEY" in e for e in errors)
    assert any("ALLOW_DEV_SOCIAL_LOGIN" in e for e in errors)
    assert Settings(ENVIRONMENT="development").production_config_errors() == []
