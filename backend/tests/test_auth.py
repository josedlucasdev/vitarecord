import pyotp
import pytest
from httpx import AsyncClient

from app.core.security import create_password_reset_token


@pytest.mark.anyio
async def test_login_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@vitarecord.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_login_wrong_password(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@vitarecord.com", "password": "WrongPassword!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_login_with_mfa(client: AsyncClient):
    # mfa.admin@vitarecord.com tiene MFA habilitado con secreto JBSWY3DPEHPK3PXP
    totp = pyotp.TOTP("JBSWY3DPEHPK3PXP")
    valid_code = totp.now()

    # Intento sin codigo MFA
    response_no_mfa = await client.post(
        "/api/v1/auth/login",
        data={"username": "mfa.admin@vitarecord.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert response_no_mfa.status_code == 401
    assert "MFA" in response_no_mfa.json()["detail"]

    # Intento con codigo MFA valido
    response_with_mfa = await client.post(
        "/api/v1/auth/login?mfa_code=" + valid_code,
        data={"username": "mfa.admin@vitarecord.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert response_with_mfa.status_code == 200
    assert "access_token" in response_with_mfa.json()


@pytest.mark.anyio
async def test_refresh_token_rotation_and_reuse_detection(client: AsyncClient):
    # 1. Login
    # 1. Login
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@vitarecord.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200
    tokens1 = login_resp.json()
    r1 = tokens1["refresh_token"]

    # 2. Refresh r1 -> r2
    ref_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": r1})
    assert ref_resp.status_code == 200
    tokens2 = ref_resp.json()
    r2 = tokens2["refresh_token"]
    assert r2 != r1

    # 3. Intentar reusar r1 (debe fallar y activar deteccion de reuso)
    reuse_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": r1})
    assert reuse_resp.status_code == 401

    # 4. Una vez detectado reuso, r2 tambien queda revocado por sospecha de robo
    ref_after_reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": r2})
    assert ref_after_reuse.status_code == 401


@pytest.mark.anyio
async def test_sessions_list_and_revoke(client: AsyncClient):
    # 1. Login para obtener token
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@vitarecord.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded", "user-agent": "TestDevice/1.0"},
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Listar sesiones
    sess_resp = await client.get("/api/v1/auth/sessions", headers=headers)
    assert sess_resp.status_code == 200
    sessions = sess_resp.json()
    assert len(sessions) >= 1
    session_id = sessions[0]["id"]

    # 3. Revocar sesion especifica
    del_resp = await client.delete(f"/api/v1/auth/sessions/{session_id}", headers=headers)
    assert del_resp.status_code == 204


@pytest.mark.anyio
async def test_forgot_and_reset_password_flow(client: AsyncClient):
    # 1. Solicitar enlace de recuperacion
    forgot_resp = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "admin@vitarecord.com"},
    )
    assert forgot_resp.status_code == 200

    # 2. Crear token de reset para admin (id: u1111111-1111-1111-1111-111111111111)
    token = create_password_reset_token("u1111111-1111-1111-1111-111111111111")

    # 3. Resetear contraseña
    reset_resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewPassword456!"},
    )
    assert reset_resp.status_code == 200

    # 4. Probar login con nueva contrasena
    new_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@vitarecord.com", "password": "NewPassword456!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert new_login.status_code == 200

    # Restaurar password original para evitar alterar otros tests
    reset_back_token = create_password_reset_token("u1111111-1111-1111-1111-111111111111")
    await client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_back_token, "new_password": "Password123!"},
        headers={"content-type": "application/json"},
    )
