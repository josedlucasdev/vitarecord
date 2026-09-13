import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.affiliation import DoctorClinicAffiliation, PatientClinicAffiliation
from app.models.user import DoctorScheduleLock, User


@pytest.mark.anyio
async def test_clinic_users_provisioning_tenant_vs_global(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"
    suffix = uuid.uuid4().hex[:6]

    # 1. Login como Clinic Admin
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "clinic.admin@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Crear una secretaria (RECEPTIONIST) - Usuario de Tenant
    sec_email = f"secretaria.{suffix}@intimasalud.com"
    sec_resp = await client.post(
        f"/api/v1/clinics/{clinic_id}/users",
        json={
            "email": sec_email,
            "full_name": f"Secretaria Sede {suffix}",
            "phone": "+584120000001",
            "role": "RECEPTIONIST",
        },
        headers=headers,
    )
    assert sec_resp.status_code == 201
    sec_data = sec_resp.json()
    sec_id = sec_data["id"]
    assert sec_data["role"] == "RECEPTIONIST"
    assert sec_data["is_tenant_user"] is True
    assert sec_data["status"] == "PENDING_ONBOARDING"
    assert sec_data["clinic_id"] == clinic_id

    # 3. Correo duplicado para usuario de tenant (debe fallar con 409 Conflict)
    duplicate_resp = await client.post(
        f"/api/v1/clinics/{clinic_id}/users",
        json={
            "email": sec_email.upper(),
            "full_name": "Intento Duplicado",
            "role": "CLINIC_ADMIN",
        },
        headers=headers,
    )
    assert duplicate_resp.status_code == 409
    assert "ya se encuentra registrado" in duplicate_resp.json()["detail"]

    # 4. Cambiar rol de usuario tenant (RECEPTIONIST -> CLINIC_ADMIN)
    role_change_resp = await client.patch(
        f"/api/v1/clinics/{clinic_id}/users/{sec_id}/role",
        json={"role": "CLINIC_ADMIN"},
        headers=headers,
    )
    assert role_change_resp.status_code == 200
    assert role_change_resp.json()["role"] == "CLINIC_ADMIN"

    # Inactivar usuario de tenant (debe pasar a DEACTIVATED)
    toggle_resp = await client.delete(
        f"/api/v1/clinics/{clinic_id}/users/{sec_id}",
        headers=headers,
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["status"] == "DEACTIVATED"

    # Reactivar usuario de tenant
    toggle_resp2 = await client.delete(
        f"/api/v1/clinics/{clinic_id}/users/{sec_id}",
        headers=headers,
    )
    assert toggle_resp2.status_code == 200
    assert toggle_resp2.json()["status"] == "ACTIVE"

    # 5. Crear un Médico (DOCTOR) - Entidad Global
    doc_email = f"dr.nuevo.{suffix}@intimasalud.com"
    doc_resp = await client.post(
        f"/api/v1/clinics/{clinic_id}/users",
        json={
            "email": doc_email,
            "full_name": f"Dr. MultiSede {suffix}",
            "phone": "+584140000002",
            "role": "DOCTOR",
            "specialty": "Ginecología y Obstetricia",
            "license_number": f"MPPS-{suffix}",
        },
        headers=headers,
    )
    assert doc_resp.status_code == 201
    doc_data = doc_resp.json()
    doc_id = doc_data["id"]
    assert doc_data["role"] == "DOCTOR"
    assert doc_data["is_tenant_user"] is False

    # Verificar que el médico tiene DoctorClinicAffiliation activa y mutex lock
    async with AsyncSessionLocal() as session:
        aff = await session.scalar(
            select(DoctorClinicAffiliation).where(
                DoctorClinicAffiliation.doctor_id == doc_id,
                DoctorClinicAffiliation.clinic_id == clinic_id,
            )
        )
        assert aff is not None
        assert aff.status == "ACTIVE"

    # 6. Desvincular al Médico de la clínica
    disaff_resp = await client.post(
        f"/api/v1/clinics/{clinic_id}/users/{doc_id}/disaffiliate",
        headers=headers,
    )
    assert disaff_resp.status_code == 200
    assert "ha sido desvinculado" in disaff_resp.json()["message"]

    # Comprobar que el usuario sigue ACTIVO en la base de datos (NO fue inactivado ni eliminado)
    async with AsyncSessionLocal() as session:
        doc_user = await session.get(User, doc_id)
        assert doc_user is not None
        assert doc_user.status in ("ACTIVE", "PENDING_ONBOARDING")  # NO DEACTIVATED
        
        aff = await session.scalar(
            select(DoctorClinicAffiliation).where(
                DoctorClinicAffiliation.doctor_id == doc_id,
                DoctorClinicAffiliation.clinic_id == clinic_id,
            )
        )
        assert aff.status == "DISAFFILIATED"

    # 7. Volver a vincular al mismo médico (que ya existe globalmente en la plataforma)
    reaff_resp = await client.post(
        f"/api/v1/clinics/{clinic_id}/users",
        json={
            "email": doc_email,
            "full_name": f"Dr. MultiSede {suffix}",
            "role": "DOCTOR",
        },
        headers=headers,
    )
    assert reaff_resp.status_code == 201
    assert reaff_resp.json()["id"] == doc_id

    # 8. Crear un Paciente (PATIENT) - Entidad Global
    pat_email = f"paciente.global.{suffix}@gmail.com"
    pat_resp = await client.post(
        f"/api/v1/clinics/{clinic_id}/users",
        json={
            "email": pat_email,
            "full_name": f"Paciente Global {suffix}",
            "phone": "+584160000003",
            "role": "PATIENT",
        },
        headers=headers,
    )
    assert pat_resp.status_code == 201
    pat_data = pat_resp.json()
    pat_id = pat_data["id"]
    assert pat_data["role"] == "PATIENT"
    assert pat_data["is_tenant_user"] is False

    # Verificar que el paciente tiene PatientClinicAffiliation activa
    async with AsyncSessionLocal() as session:
        p_aff = await session.scalar(
            select(PatientClinicAffiliation).where(
                PatientClinicAffiliation.patient_id == pat_id,
                PatientClinicAffiliation.clinic_id == clinic_id,
            )
        )
        assert p_aff is not None
        assert p_aff.status == "ACTIVE"

    # 9. Desvincular al Paciente de la clínica
    del_pat_resp = await client.delete(
        f"/api/v1/clinics/{clinic_id}/users/{pat_id}",
        headers=headers,
    )
    assert del_pat_resp.status_code == 200
    assert "ha sido desvinculado" in del_pat_resp.json()["message"]

    # Comprobar que la cuenta del paciente sigue ACTIVA en la plataforma
    async with AsyncSessionLocal() as session:
        pat_user = await session.get(User, pat_id)
        assert pat_user is not None
        assert pat_user.status in ("ACTIVE", "PENDING_ONBOARDING")  # NO DEACTIVATED
        
        p_aff = await session.scalar(
            select(PatientClinicAffiliation).where(
                PatientClinicAffiliation.patient_id == pat_id,
                PatientClinicAffiliation.clinic_id == clinic_id,
            )
        )
        assert p_aff.status == "DISAFFILIATED"
