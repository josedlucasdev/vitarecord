import datetime
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.models.appointment import Appointment
from app.models.audit import AuditLog
from app.models.medical_record import MedicalRecord


@pytest.mark.asyncio
async def test_mandatory_audit_read_logging_on_medical_records(client: AsyncClient):
    """Criterio de Aceptacion (DoD): Toda lectura de historias clinicas DEBE generar action='READ' en audit_logs."""
    doctor_token = create_access_token(
        subject="u2222222-2222-2222-2222-222222222222",
        clinic_id="c1111111-1111-1111-1111-111111111111",
        role="DOCTOR",
        email="doctor@intimasalud.com",
    )
    patient_token = create_access_token(
        subject="u4444444-4444-4444-4444-444444444444",
        clinic_id="c1111111-1111-1111-1111-111111111111",
        role="PATIENT",
        email="paciente@intimasalud.com",
    )

    # 1. Crear una cita previa de prueba
    appointment_id = "a5555555-5555-5555-5555-555555555555"
    async with AsyncSessionLocal() as db:
        # Limpiar previa si existiera
        existing_rec = (await db.execute(select(MedicalRecord).where(MedicalRecord.appointment_id == appointment_id))).scalar_one_or_none()
        if existing_rec:
            await db.delete(existing_rec)
        existing_app = (await db.execute(select(Appointment).where(Appointment.id == appointment_id))).scalar_one_or_none()
        if existing_app:
            await db.delete(existing_app)
        await db.commit()

        app = Appointment(
            id=appointment_id,
            clinic_id="c1111111-1111-1111-1111-111111111111",
            doctor_id="u2222222-2222-2222-2222-222222222222",
            patient_id="u4444444-4444-4444-4444-444444444444",
            start_time=datetime.datetime(2026, 10, 10, 9, 0),
            end_time=datetime.datetime(2026, 10, 10, 9, 30),
            status="CONFIRMED",
            reason="Consulta ginecológica de control",
        )
        db.add(app)
        await db.commit()

    # 2. El doctor crea la historia medica
    create_payload = {
        "appointment_id": appointment_id,
        "anamnesis": "Paciente femenina acude para control anual, sin antecedentes patologicos relevantes.",
        "physical_exam": "TA: 110/70 mmHg, FC: 72 lpm, abdomen blando, sin masas palpables.",
        "diagnosis": "Control ginecologico preventivo de rutina.",
        "plan": "Continuar con habitos saludables y control en 12 meses.",
        "icd10_code": "Z01.4",
        "icd10_description": "Examen ginecológico general",
    }
    resp_create = await client.post(
        "/api/v1/medical-records",
        json=create_payload,
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert resp_create.status_code == 201
    created_record = resp_create.json()
    record_id = created_record["id"]

    # 3. Verificar que al crear se genero auditoria CREATE
    async with AsyncSessionLocal() as db:
        stmt_create_log = select(AuditLog).where(
            AuditLog.entity_id == record_id,
            AuditLog.action == "CREATE",
        )
        create_log = (await db.execute(stmt_create_log)).scalar_one_or_none()
        assert create_log is not None
        assert create_log.user_id == "u2222222-2222-2222-2222-222222222222"

    # 4. El paciente consulta su historia medica por ID de cita
    resp_read_app = await client.get(
        f"/api/v1/medical-records/appointment/{appointment_id}",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert resp_read_app.status_code == 200
    data_app = resp_read_app.json()
    assert data_app["anamnesis"] == create_payload["anamnesis"]

    # 5. El paciente consulta su historial clinico completo
    resp_history = await client.get(
        "/api/v1/medical-records/patient/u4444444-4444-4444-4444-444444444444",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert resp_history.status_code == 200
    assert len(resp_history.json()) >= 1

    # 6. VERIFICAR QUE SE HAYAN GENERADO REGISTROS DE AUDITORIA 'READ' OBLIGATORIAMENTE
    async with AsyncSessionLocal() as db:
        stmt_reads = select(AuditLog).where(
            AuditLog.entity_id == record_id,
            AuditLog.action == "READ",
        )
        read_logs = list((await db.execute(stmt_reads)).scalars().all())
        # Hubo 2 lecturas (por cita y por listado de historial)
        assert len(read_logs) >= 2
        for log in read_logs:
            assert log.user_id == "u4444444-4444-4444-4444-444444444444"
            assert log.entity_type == "medical_record"
