import pyotp
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_mfa_status_public_endpoint(client: AsyncClient):
    # mfa.admin@vitarecord.com tiene MFA habilitado
    res_mfa = await client.get("/api/v1/auth/mfa-status?email=mfa.admin@vitarecord.com")
    assert res_mfa.status_code == 200
    assert res_mfa.json()["mfa_enabled"] is True

    # admin@vitarecord.com NO tiene MFA habilitado
    res_no_mfa = await client.get("/api/v1/auth/mfa-status?email=admin@vitarecord.com")
    assert res_no_mfa.status_code == 200
    assert res_no_mfa.json()["mfa_enabled"] is False

    # Correo inexistente debe retornar mfa_enabled=False
    res_not_found = await client.get("/api/v1/auth/mfa-status?email=inexistente@vitarecord.com")
    assert res_not_found.status_code == 200
    assert res_not_found.json()["mfa_enabled"] is False


@pytest.mark.anyio
async def test_login_with_mfa_in_form_body(client: AsyncClient):
    totp = pyotp.TOTP("JBSWY3DPEHPK3PXP")
    valid_code = totp.now()

    # Intento enviando el código en el cuerpo del formulario
    res = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "mfa.admin@vitarecord.com",
            "password": "Password123!",
            "mfa_code": valid_code,
        },
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data


@pytest.mark.anyio
async def test_mfa_setup_enable_disable_full_lifecycle(client: AsyncClient):
    # 1. Iniciar sesión con un usuario sin MFA (admin@vitarecord.com)
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@vitarecord.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 2. Consultar estado MFA autenticado
    status_res = await client.get("/api/v1/auth/mfa/status", headers=auth_headers)
    assert status_res.status_code == 200
    assert status_res.json()["mfa_enabled"] is False

    # 3. Solicitar setup de MFA (genera QR y clave)
    setup_res = await client.post("/api/v1/auth/mfa/setup", headers=auth_headers)
    assert setup_res.status_code == 200
    setup_data = setup_res.json()
    assert "secret" in setup_data
    assert "otpauth_url" in setup_data
    assert setup_data["qr_code"].startswith("data:image/png;base64,")
    secret = setup_data["secret"]

    # 4. Intentar activar con código erróneo
    bad_enable_res = await client.post(
        "/api/v1/auth/mfa/enable",
        json={"secret": secret, "code": "000000"},
        headers=auth_headers,
    )
    assert bad_enable_res.status_code == 400

    # 5. Activar con código TOTP válido generado
    valid_code = pyotp.TOTP(secret).now()
    good_enable_res = await client.post(
        "/api/v1/auth/mfa/enable",
        json={"secret": secret, "code": valid_code},
        headers=auth_headers,
    )
    assert good_enable_res.status_code == 200

    # 6. Verificar que ahora el estado es activo
    status_res_after = await client.get("/api/v1/auth/mfa/status", headers=auth_headers)
    assert status_res_after.json()["mfa_enabled"] is True

    # 7. Comprobar que en endpoint público ahora sale mfa_enabled=True
    pub_res = await client.get("/api/v1/auth/mfa-status?email=admin@vitarecord.com")
    assert pub_res.json()["mfa_enabled"] is True

    # 8. Intentar login sin código MFA debe fallar
    login_no_mfa = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@vitarecord.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_no_mfa.status_code == 401
    assert "MFA" in login_no_mfa.json()["detail"]

    # 9. Login con código válido debe funcionar
    new_code = pyotp.TOTP(secret).now()
    login_with_mfa = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@vitarecord.com", "password": "Password123!", "mfa_code": new_code},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_with_mfa.status_code == 200
    new_token = login_with_mfa.json()["access_token"]
    new_headers = {"Authorization": f"Bearer {new_token}"}

    # 10. Desactivar MFA con contraseña incorrecta debe fallar
    bad_disable = await client.post(
        "/api/v1/auth/mfa/disable",
        json={"password": "WrongPassword!"},
        headers=new_headers,
    )
    assert bad_disable.status_code == 400

    # 11. Desactivar MFA con contraseña correcta debe tener éxito
    good_disable = await client.post(
        "/api/v1/auth/mfa/disable",
        json={"password": "Password123!"},
        headers=new_headers,
    )
    assert good_disable.status_code == 200

    # 12. Comprobar que tras desactivar, login sin código vuelve a funcionar directamente
    login_after_disable = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@vitarecord.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_after_disable.status_code == 200
