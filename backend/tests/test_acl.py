import pytest
from httpx import AsyncClient

from app.core.acl import DEFAULT_ROLE_PERMISSIONS, Permission, has_permission


def test_acl_permissions_matrix_sanity():
    # Superadmin tiene control de tenants y rooms
    assert has_permission("SUPERADMIN", Permission.TENANTS_MANAGE)
    assert has_permission("SUPERADMIN", Permission.ROOMS_MANAGE)

    # Clinic Admin no puede crear tenants pero si salas
    assert not has_permission("CLINIC_ADMIN", Permission.TENANTS_MANAGE)
    assert has_permission("CLINIC_ADMIN", Permission.ROOMS_MANAGE)

    # Recepcionista no puede crear salas ni verificar medicos
    assert not has_permission("RECEPTIONIST", Permission.ROOMS_MANAGE)
    assert not has_permission("RECEPTIONIST", Permission.COMPLIANCE_VERIFY_DOCTOR)

    # Paciente no puede gestionar salas ni invitar medicos
    assert not has_permission("PATIENT", Permission.ROOMS_MANAGE)
    assert not has_permission("PATIENT", Permission.DOCTORS_INVITE)

    # Medico no puede crear salas ni tenants
    assert not has_permission("DOCTOR", Permission.ROOMS_MANAGE)
    assert not has_permission("DOCTOR", Permission.TENANTS_MANAGE)
    assert has_permission("DOCTOR", Permission.DOCTORS_SCHEDULE_MANAGE)


@pytest.mark.anyio
async def test_endpoint_acl_enforcement(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"

    # 1. Login como Paciente intentando crear una sala fisica
    pat_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    pat_token = pat_login.json()["access_token"]
    resp_pat = await client.post(
        f"/api/v1/clinics/{clinic_id}/rooms",
        json={"name": "Sala No Autorizada", "room_number": "999"},
        headers={"Authorization": f"Bearer {pat_token}"},
    )
    assert resp_pat.status_code == 403
    assert "Permisos insuficientes" in resp_pat.json()["detail"]

    # 2. Login como Recepcionista intentando crear una sala fisica
    rec_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "recepcion@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    rec_token = rec_login.json()["access_token"]
    resp_rec = await client.post(
        f"/api/v1/clinics/{clinic_id}/rooms",
        json={"name": "Sala No Autorizada Rec", "room_number": "998"},
        headers={"Authorization": f"Bearer {rec_token}"},
    )
    assert resp_rec.status_code == 403

    # 3. Login como Clinic Admin intentando crear sala en OTRA clinica ajena
    admin_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "clinic.admin@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    admin_token = admin_login.json()["access_token"]
    resp_other_clinic = await client.post(
        "/api/v1/clinics/c2222222-2222-2222-2222-222222222222/rooms",
        json={"name": "Sala Clínica Ajena", "room_number": "100"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_other_clinic.status_code == 403
