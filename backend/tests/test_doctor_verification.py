import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.audit import AuditLog
from app.models.user import User


@pytest.mark.anyio
async def test_doctor_verification_queue_permissions(client: AsyncClient):
    # 1. Login como Paciente (debe fallar con 403)
    patient_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    patient_token = patient_login.json()["access_token"]
    resp_patient = await client.get(
        "/api/v1/doctors/pending-verification",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert resp_patient.status_code == 403

    # 2. Login como SuperAdmin (debe tener acceso 200)
    admin_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    admin_token = admin_login.json()["access_token"]
    resp_admin = await client.get(
        "/api/v1/doctors/pending-verification",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_admin.status_code == 200
    assert isinstance(resp_admin.json(), list)


@pytest.mark.anyio
async def test_doctor_verification_approve_and_audit_flow(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"

    # 1. Admin login
    admin_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Crear doctor mediante el flujo de onboarding
    doc_email = f"dr.verif.{uuid.uuid4().hex[:6]}@clinica.com"
    inv_resp = await client.post(
        f"/api/v1/clinics/{clinic_id}/invitations",
        json={"email": doc_email, "full_name": "Dr. Aprobado Test", "specialty": "Urología"},
        headers=admin_headers,
    )
    token = inv_resp.json()["invitation_link"].split("token=")[1]

    # Completa onboarding -> queda en PENDING_VERIFICATION
    onb_resp = await client.post(
        "/api/v1/invitations/onboarding",
        json={
            "token": token,
            "password": "PasswordDoc123!",
            "full_name": "Dr. Aprobado Test",
            "license_number": "MP-998877",
            "specialty": "Urología",
            "biography": "Especialista urológico.",
        },
    )
    assert onb_resp.status_code == 200

    # 3. Listar pendientes y verificar que aparece
    pending_resp = await client.get(
        "/api/v1/doctors/pending-verification",
        headers=admin_headers,
    )
    assert pending_resp.status_code == 200
    pending_list = pending_resp.json()
    matched_doc = next((d for d in pending_list if d["email"] == doc_email), None)
    assert matched_doc is not None
    assert matched_doc["license_verification_status"] == "PENDING_VERIFICATION"
    doctor_id = matched_doc["id"]

    # 4. Intentar activar disponibilidad para emergencias ANTES de ser verificado (debe fallar con 400)
    doc_login = await client.post(
        "/api/v1/auth/login",
        data={"username": doc_email, "password": "PasswordDoc123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert doc_login.status_code == 200
    doc_token = doc_login.json()["access_token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    emerg_fail = await client.patch(
        f"/api/v1/doctors/{doctor_id}/emergency-availability",
        json={"is_available": True},
        headers=doc_headers,
    )
    assert emerg_fail.status_code == 400
    assert "Bloqueo de seguridad" in emerg_fail.json()["detail"]

    # 5. SuperAdmin aprueba la matricula formalmente
    verify_resp = await client.post(
        f"/api/v1/doctors/{doctor_id}/verify",
        json={
            "action": "APPROVE",
            "reason": "Matrícula validada en el registro médico oficial.",
            "document_url": "https://storage.intimasalud.com/licenses/mp998877.pdf",
        },
        headers=admin_headers,
    )
    assert verify_resp.status_code == 200
    verif_data = verify_resp.json()
    assert verif_data["status"] == "ACTIVE"
    assert verif_data["license_verification_status"] == "VERIFIED"

    # 6. Comprobar que el evento de auditoria inmutable se registro en audit_logs
    async with AsyncSessionLocal() as session:
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.action == "DOCTOR_VERIFICATION_APPROVE",
                AuditLog.entity_id == doctor_id,
            )
        )
        res = await session.execute(stmt)
        audit_entry = res.scalar_one_or_none()
        assert audit_entry is not None
        assert audit_entry.details["action"] == "APPROVE"
        assert audit_entry.details["license_number"] == "MP-998877"

    # 7. Ahora que esta VERIFIED, el medico SI puede activar disponibilidad para emergencias
    emerg_ok = await client.patch(
        f"/api/v1/doctors/{doctor_id}/emergency-availability",
        json={"is_available": True},
        headers=doc_headers,
    )
    assert emerg_ok.status_code == 200
    assert emerg_ok.json()["is_available_for_emergencies"] is True


@pytest.mark.anyio
async def test_doctor_verification_reject_flow(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"

    # 1. Admin login
    admin_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Onboarding de nuevo medico
    doc_email = f"dr.rechazado.{uuid.uuid4().hex[:6]}@clinica.com"
    inv_resp = await client.post(
        f"/api/v1/clinics/{clinic_id}/invitations",
        json={"email": doc_email, "full_name": "Dr. Rechazado Test"},
        headers=admin_headers,
    )
    token = inv_resp.json()["invitation_link"].split("token=")[1]

    await client.post(
        "/api/v1/invitations/onboarding",
        json={
            "token": token,
            "password": "PasswordDoc123!",
            "full_name": "Dr. Rechazado Test",
            "license_number": "MP-FALSO-000",
        },
    )

    # 3. Obtener doctor_id
    pending_resp = await client.get("/api/v1/doctors/pending-verification", headers=admin_headers)
    matched_doc = next(d for d in pending_resp.json() if d["email"] == doc_email)
    doctor_id = matched_doc["id"]

    # 4. SuperAdmin rechaza la matricula con motivo
    reject_resp = await client.post(
        f"/api/v1/doctors/{doctor_id}/verify",
        json={
            "action": "REJECT",
            "reason": "La matrícula MP-FALSO-000 no se encuentra registrada en el Colegio de Médicos.",
        },
        headers=admin_headers,
    )
    assert reject_resp.status_code == 200
    reject_data = reject_resp.json()
    assert reject_data["license_verification_status"] == "REJECTED"

    # 5. Comprobar auditoria
    async with AsyncSessionLocal() as session:
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.action == "DOCTOR_VERIFICATION_REJECT",
                AuditLog.entity_id == doctor_id,
            )
        )
        res = await session.execute(stmt)
        audit_entry = res.scalar_one_or_none()
        assert audit_entry is not None
        assert audit_entry.details["action"] == "REJECT"
        assert "no se encuentra registrada" in audit_entry.details["reason"]
