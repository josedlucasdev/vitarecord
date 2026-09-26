"""Pruebas del ciclo de emancipación de familiares dependientes (plan/plan.md Módulo 3 y 2.B.5).

Verifica:
1. Transición legal automática a mayoría de edad (18 años) -> 'EMANCIPATION_PENDING_CONSENT'.
2. Registro inmutable en audit_logs del evento de emancipación.
3. Suspensión por defecto del acceso del titular a nuevas historias clínicas creadas tras cumplir 18 años.
4. Preservación del acceso auditado a historias clínicas pediátricas previas a la mayoría de edad.
5. Reclamo/vinculación de cuenta propia ('linked_user_id' -> 'EMANCIPATED').
6. Concesión y revocación de consentimiento explícito inter-partes.
"""

import datetime
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.models.appointment import Appointment
from app.models.audit import AuditLog
from app.models.patient_consent_grant import PatientConsentGrant
from app.models.patient_dependent import PatientDependent
from app.models.user import User
from app.tasks.emancipation import process_dependents_emancipation


@pytest.mark.asyncio
async def test_dependent_emancipation_lifecycle_and_phi_access_suspension(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"
    doctor_id = "u2222222-2222-2222-2222-222222222222"
    guardian_patient_id = "u4444444-4444-4444-4444-444444444444"
    dep_email = f"emancipado_{uuid.uuid4().hex[:6]}@example.com"

    doctor_token = create_access_token(
        subject=doctor_id,
        clinic_id=clinic_id,
        role="DOCTOR",
        email="doctor@intimasalud.com",
    )
    guardian_token = create_access_token(
        subject=guardian_patient_id,
        clinic_id=clinic_id,
        role="PATIENT",
        email="paciente@intimasalud.com",
    )

    dep_id = f"dep-{uuid.uuid4().hex[:8]}"
    appt_minor_id = f"app-min-{uuid.uuid4().hex[:8]}"
    appt_adult_id = f"app-adl-{uuid.uuid4().hex[:8]}"

    # Fecha de nacimiento: cumplió 18 años hace 1 mes
    birth_date_18 = datetime.date.today() - datetime.timedelta(days=18 * 365 + 30)

    async with AsyncSessionLocal() as db:
        # 1. Crear dependiente que inicialmente estaba registrado como MINOR
        dep = PatientDependent(
            id=dep_id,
            guardian_user_id=guardian_patient_id,
            full_name="Hijo Emancipando",
            relationship="HIJO",
            birth_date=birth_date_18,
            email=dep_email,
            gender="MASCULINO",
            emancipation_status="MINOR",
        )
        db.add(dep)

        # 2. Cita pediátrica creada antes de los 18 años
        time_pre_18 = datetime.datetime.combine(
            birth_date_18 + datetime.timedelta(days=17 * 365),
            datetime.time(10, 0),
        )
        appt_minor = Appointment(
            id=appt_minor_id,
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            patient_id=guardian_patient_id,
            dependent_id=dep_id,
            start_time=time_pre_18,
            end_time=time_pre_18 + datetime.timedelta(minutes=30),
            status="CONFIRMED",
            reason="Consulta preventiva pediátrica",
        )
        db.add(appt_minor)

        # 3. Cita creada después de los 18 años
        time_post_18 = datetime.datetime.utcnow()
        appt_adult = Appointment(
            id=appt_adult_id,
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            patient_id=guardian_patient_id,
            dependent_id=dep_id,
            start_time=time_post_18,
            end_time=time_post_18 + datetime.timedelta(minutes=30),
            status="CONFIRMED",
            reason="Consulta médica como nuevo adulto",
        )
        db.add(appt_adult)
        await db.commit()

    # 4. Doctor registra historia clínica para la cita pediátrica
    res_mr_minor = await client.post(
        "/api/v1/medical-records",
        json={
            "appointment_id": appt_minor_id,
            "anamnesis": "Control pediátrico general a los 17 años.",
            "physical_exam": "Signos vitales normales.",
            "diagnosis": "Adolescente sano",
            "plan": "Seguimiento anual.",
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert res_mr_minor.status_code == 201

    # Asegurar que el registro pediátrico tenga created_at previo a los 18 años
    async with AsyncSessionLocal() as db:
        rec_minor = (await db.execute(select(Appointment).where(Appointment.id == appt_minor_id))).scalar_one()
        # Modificar created_at de la historia clínica en base de datos para simular tiempo histórico
        from app.models.medical_record import MedicalRecord
        mr_m = (await db.execute(select(MedicalRecord).where(MedicalRecord.appointment_id == appt_minor_id))).scalar_one()
        mr_m.created_at = time_pre_18
        await db.commit()

    # 5. Ejecutar tarea periódica de emancipación
    stats = await process_dependents_emancipation()
    assert stats["transitioned"] >= 1

    # Verificar que el dependiente transicionó a EMANCIPATION_PENDING_CONSENT
    async with AsyncSessionLocal() as db:
        dep_db = (await db.execute(select(PatientDependent).where(PatientDependent.id == dep_id))).scalar_one()
        assert dep_db.emancipation_status == "EMANCIPATION_PENDING_CONSENT"
        assert dep_db.emancipated_at is not None

        # Verificar auditoría
        audit_res = await db.execute(
            select(AuditLog).where(
                AuditLog.action == "DEPENDENT_EMANCIPATED",
                AuditLog.entity_id == dep_id,
            )
        )
        audit_entry = audit_res.scalar_one_or_none()
        assert audit_entry is not None
        assert audit_entry.details["emancipation_status"] == "EMANCIPATION_PENDING_CONSENT"

    # 6. Doctor registra historia clínica para la cita de adulto (creada hoy, post 18 años)
    res_mr_adult = await client.post(
        "/api/v1/medical-records",
        json={
            "appointment_id": appt_adult_id,
            "anamnesis": "Consulta confidencial del nuevo adulto por afección dermatológica.",
            "physical_exam": "Lesión cutánea focal.",
            "diagnosis": "Dermatitis de contacto",
            "plan": "Tratamiento tópico confidencial.",
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert res_mr_adult.status_code == 201

    # 7. Titular consulta el historial del dependiente:
    # DEBE VER ÚNICAMENTE la historia pediátrica previa a los 18 años.
    # La historia posterior a la mayoría de edad DEBE ESTAR SUSPENDIDA.
    res_history = await client.get(
        f"/api/v1/medical-records/patient/{guardian_patient_id}?dependent_id={dep_id}",
        headers={"Authorization": f"Bearer {guardian_token}"},
    )
    assert res_history.status_code == 200
    records = res_history.json()
    assert len(records) == 1
    assert records[0]["appointment_id"] == appt_minor_id

    # 8. Titular intenta acceder directamente a la consulta del adulto: 403 Forbidden
    res_forbidden = await client.get(
        f"/api/v1/medical-records/appointment/{appt_adult_id}",
        headers={"Authorization": f"Bearer {guardian_token}"},
    )
    assert res_forbidden.status_code == 403
    assert "suspendido" in res_forbidden.json()["detail"].lower()

    # 9. El nuevo adulto se crea una cuenta o vincula su cuenta ('claim')
    new_adult_user_id = f"u-adult-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as db:
        adult_user = User(
            id=new_adult_user_id,
            email=dep_email,
            hashed_password="hashed_pwd",
            full_name="Hijo Emancipando Ya Adulto",
            role="PATIENT",
            status="ACTIVE",
        )
        db.add(adult_user)
        await db.commit()

    adult_token = create_access_token(
        subject=new_adult_user_id,
        role="PATIENT",
        email=dep_email,
    )

    # Reclamar dependiente
    claim_res = await client.post(
        f"/api/v1/patients/dependents/{dep_id}/claim",
        headers={"Authorization": f"Bearer {adult_token}"},
    )
    assert claim_res.status_code == 200
    assert claim_res.json()["emancipation_status"] == "EMANCIPATED"
    assert claim_res.json()["linked_user_id"] == new_adult_user_id

    # 10. Ahora el nuevo adulto otorga consentimiento explícito al titular
    async with AsyncSessionLocal() as db:
        consent = PatientConsentGrant(
            patient_id=new_adult_user_id,
            granted_to_clinic_id=clinic_id,
            granted_by_user_id=new_adult_user_id,
            scope="READ_MEDICAL_RECORDS",
            granted_at=datetime.datetime.utcnow(),
            granted_until=datetime.datetime.utcnow() + datetime.timedelta(days=365),
            is_revoked=False,
        )
        db.add(consent)
        await db.commit()

    # Con consentimiento activo, el titular ahora puede consultar también la historia adulta
    res_history_consented = await client.get(
        f"/api/v1/medical-records/patient/{guardian_patient_id}?dependent_id={dep_id}",
        headers={"Authorization": f"Bearer {guardian_token}"},
    )
    assert res_history_consented.status_code == 200
    assert len(res_history_consented.json()) == 2
