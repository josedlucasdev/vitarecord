import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_case_a_invitation_flow_existing_doctor(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"

    # 1. Login como Admin para invitar
    admin_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Crear un segundo médico registrado para probar invitación y aceptación
    unique_email = f"dr.registrado.{uuid.uuid4().hex[:6]}@intimasalud.com"

    # Se envía invitación como nuevo médico primero para registrarlo
    inv_create = await client.post(
        f"/api/v1/clinics/{clinic_id}/invitations",
        json={"email": unique_email, "full_name": "Dr. Existente", "specialty": "Cardiología"},
        headers=headers,
    )
    assert inv_create.status_code == 200
    inv_data = inv_create.json()
    assert inv_data["is_new_user"] is True
    token = inv_data["invitation_link"].split("token=")[1]

    # Completa onboarding inicial
    onb_resp = await client.post(
        "/api/v1/invitations/onboarding",
        json={
            "token": token,
            "password": "DoctorPassword123!",
            "full_name": "Dr. Existente Registrado",
            "license_number": "MP-98765",
            "specialty": "Cardiología",
        },
    )
    assert onb_resp.status_code == 200

    # Ahora invitamos a este mismo médico registrado a otra clínica (o reinvitamos)
    inv_case_a = await client.post(
        f"/api/v1/clinics/{clinic_id}/invitations",
        json={"email": unique_email},
        headers=headers,
    )
    assert inv_case_a.status_code == 200
    data_a = inv_case_a.json()
    assert data_a["is_new_user"] is False
    token_a = data_a["invitation_link"].split("token=")[1]

    # 3. Validar token
    val_resp = await client.get(f"/api/v1/invitations/validate?token={token_a}")
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["valid"] is True
    assert val_data["doctor_email"] == unique_email
    assert val_data["is_new_user"] is False

    # 4. Responder invitación: ACCEPT
    resp_action = await client.post(
        "/api/v1/invitations/respond",
        json={"token": token_a, "action": "ACCEPT"},
    )
    assert resp_action.status_code == 200
    # Como el médico no tiene matrícula verificada formalmente, pasa a INVITED_PENDING_VERIFICATION
    assert resp_action.json()["status"] in ("ACTIVE", "INVITED_PENDING_VERIFICATION")

    # 5. Reusar el mismo token debe ser rechazado
    reuse_resp = await client.post(
        "/api/v1/invitations/respond",
        json={"token": token_a, "action": "ACCEPT"},
    )
    assert reuse_resp.status_code == 400


@pytest.mark.anyio
async def test_case_b_invitation_flow_new_doctor(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"

    # 1. Login como Admin
    admin_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    admin_token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Invitar médico no existente en el sistema
    new_doc_email = f"dr.nuevo.{uuid.uuid4().hex[:6]}@clinica.com"
    inv_resp = await client.post(
        f"/api/v1/clinics/{clinic_id}/invitations",
        json={
            "email": new_doc_email,
            "full_name": "Dra. María González",
            "specialty": "Ginecología y Obstetricia",
        },
        headers=headers,
    )
    assert inv_resp.status_code == 200
    data = inv_resp.json()
    assert data["is_new_user"] is True
    assert "token=" in data["invitation_link"]
    token = data["invitation_link"].split("token=")[1]

    # 3. Validar token
    val_resp = await client.get(f"/api/v1/invitations/validate?token={token}")
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["valid"] is True
    assert val_data["is_new_user"] is True
    assert val_data["doctor_email"] == new_doc_email

    # 4. Completar Onboarding (Caso B)
    onb_resp = await client.post(
        "/api/v1/invitations/onboarding",
        json={
            "token": token,
            "password": "SecurePassword999!",
            "full_name": "Dra. María González",
            "license_number": "MP-554433",
            "specialty": "Ginecología y Obstetricia",
            "biography": "Especialista con 10 años de experiencia.",
        },
    )
    assert onb_resp.status_code == 200
    assert onb_resp.json()["status"] == "PENDING_VERIFICATION"

    # 5. El médico ahora puede iniciar sesión con sus nuevas credenciales
    doc_login = await client.post(
        "/api/v1/auth/login",
        data={"username": new_doc_email, "password": "SecurePassword999!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert doc_login.status_code == 200
    assert "access_token" in doc_login.json()

    # 6. Reusar token de onboarding debe fallar
    reuse_resp = await client.post(
        "/api/v1/invitations/onboarding",
        json={
            "token": token,
            "password": "AnotherPassword!",
        },
    )
    assert reuse_resp.status_code == 400
