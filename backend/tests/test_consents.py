"""Consentimientos inter-clinica (plan/plan.md Principio Operativo 3).

- El paciente otorga, lista y revoca; otorgar/revocar quedan en audit_logs.
- Un medico sin relacion asistencial con el paciente no puede leer su historia.
- Un medico que atiende al paciente en la clinica B no ve lo generado en la
  clinica A hasta que el paciente autoriza a la clinica B; al revocar, deja de verlo.
"""

import datetime
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.crypto import encrypt_field, get_or_create_clinic_dek
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.appointment import Appointment
from app.models.audit import AuditLog
from app.models.medical_record import MedicalRecord
from app.models.user import User

FORM = {"content-type": "application/x-www-form-urlencoded"}
CLINIC_A = "c1111111-1111-1111-1111-111111111111"
CLINIC_B = "c2222222-2222-2222-2222-222222222222"
DOCTOR_A = "u2222222-2222-2222-2222-222222222223"  # dra.castillo: clinicas 1, 2, 3
DOCTOR_B = "u2222222-2222-2222-2222-222222222222"  # doctor@: clinicas 1, 2, 5


async def _headers(client: AsyncClient, email: str) -> dict:
    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": "Password123!"}, headers=FORM)
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _new_patient() -> tuple[str, str]:
    email = f"consent_{uuid.uuid4().hex[:10]}@example.com"
    async with AsyncSessionLocal() as db:
        user = User(
            email=email, full_name="Paciente Consentimiento", hashed_password=hash_password("Password123!"),
            role="PATIENT", status="ACTIVE",
        )
        db.add(user)
        await db.commit()
        return user.id, email


async def _record_in_clinic(patient_id: str, doctor_id: str, clinic_id: str, text: str) -> str:
    """Crea una cita COMPLETED y su historia cifrada en la clinica indicada."""
    async with AsyncSessionLocal() as db:
        start = datetime.datetime(2027, 1, 1, 9, 0) + datetime.timedelta(minutes=uuid.uuid4().int % 50000)
        appt = Appointment(
            clinic_id=clinic_id, doctor_id=doctor_id, patient_id=patient_id,
            start_time=start, end_time=start + datetime.timedelta(minutes=30), status="COMPLETED",
            reason="Consulta de prueba de consentimientos",
        )
        db.add(appt)
        await db.flush()
        dek, version = await get_or_create_clinic_dek(db, clinic_id)
        record = MedicalRecord(
            appointment_id=appt.id, clinic_id=clinic_id, doctor_id=doctor_id, patient_id=patient_id,
            encrypted_anamnesis=encrypt_field(text, dek),
            encrypted_diagnosis=encrypt_field("Diagnostico de prueba", dek),
            encrypted_plan=encrypt_field("Plan de prueba", dek),
            encryption_key_version=version,
        )
        db.add(record)
        await db.commit()
        return record.id


async def _open_appointment(patient_id: str, doctor_id: str, clinic_id: str) -> None:
    async with AsyncSessionLocal() as db:
        start = datetime.datetime(2028, 1, 1, 9, 0) + datetime.timedelta(minutes=uuid.uuid4().int % 50000)
        db.add(Appointment(
            clinic_id=clinic_id, doctor_id=doctor_id, patient_id=patient_id,
            start_time=start, end_time=start + datetime.timedelta(minutes=30), status="CONFIRMED",
        ))
        await db.commit()


async def _history_ids(client: AsyncClient, headers: dict, patient_id: str):
    resp = await client.get(f"/api/v1/medical-records/patient/{patient_id}", headers=headers)
    return resp.status_code, [r["id"] for r in resp.json()] if resp.status_code == 200 else []


@pytest.mark.anyio
async def test_consent_grant_list_revoke_and_audit(client: AsyncClient):
    patient_id, email = await _new_patient()
    headers = await _headers(client, email)

    granted = await client.post("/api/v1/consents", json={"granted_to_clinic_id": CLINIC_B, "granted_days": 30}, headers=headers)
    assert granted.status_code == 201, granted.text
    grant = granted.json()
    assert grant["status"] == "ACTIVE" and grant["clinic_name"]

    listed = await client.get("/api/v1/consents/my", headers=headers)
    assert [c["id"] for c in listed.json()] == [grant["id"]]

    revoked = await client.post(f"/api/v1/consents/{grant['id']}/revoke", headers=headers)
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "REVOKED"
    assert revoked.json()["revoked_at"] is not None

    async with AsyncSessionLocal() as db:
        actions = (await db.execute(
            select(AuditLog.action).where(AuditLog.entity_id == grant["id"])
        )).scalars().all()
    assert "CONSENT_GRANTED" in actions and "CONSENT_REVOKED" in actions

    # Otro usuario no puede revocar ni un medico otorgar.
    doctor = await _headers(client, "doctor@intimasalud.com")
    assert (await client.post(f"/api/v1/consents/{grant['id']}/revoke", headers=doctor)).status_code == 403


@pytest.mark.anyio
async def test_cross_clinic_history_requires_consent(client: AsyncClient):
    patient_id, email = await _new_patient()
    patient_headers = await _headers(client, email)
    record_a = await _record_in_clinic(patient_id, DOCTOR_A, CLINIC_A, "Anamnesis sensible en clinica A")

    doctor_b = await _headers(client, "doctor@intimasalud.com")

    # Sin relacion asistencial: 403.
    code, _ = await _history_ids(client, doctor_b, patient_id)
    assert code == 403

    # El medico B atiende al paciente en la clinica B: aun no ve lo de la clinica A.
    await _open_appointment(patient_id, DOCTOR_B, CLINIC_B)
    code, ids = await _history_ids(client, doctor_b, patient_id)
    assert code == 200 and record_a not in ids

    # El paciente autoriza a la clinica B -> ahora si.
    grant = await client.post("/api/v1/consents", json={"granted_to_clinic_id": CLINIC_B}, headers=patient_headers)
    assert grant.status_code == 201
    code, ids = await _history_ids(client, doctor_b, patient_id)
    assert code == 200 and record_a in ids

    # Revoca -> deja de verlo de inmediato.
    await client.post(f"/api/v1/consents/{grant.json()['id']}/revoke", headers=patient_headers)
    code, ids = await _history_ids(client, doctor_b, patient_id)
    assert code == 200 and record_a not in ids
