import datetime
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.models.appointment import Appointment
from app.models.medical_record import MedicalRecord
from app.models.prescription import Prescription


@pytest.mark.asyncio
async def test_prescription_generation_qr_verification_and_pdf(client: AsyncClient):
    """Criterio de Aceptacion (DoD): Verificacion publica de QR y generacion de PDF con codigo QR."""
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

    appointment_id = "a7777777-7777-7777-7777-777777777777"
    async with AsyncSessionLocal() as db:
        # Limpiar
        existing_presc = (await db.execute(select(Prescription).where(Prescription.appointment_id == appointment_id))).scalar_one_or_none()
        if existing_presc:
            await db.delete(existing_presc)
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
            start_time=datetime.datetime(2026, 10, 12, 11, 0),
            end_time=datetime.datetime(2026, 10, 12, 11, 30),
            status="CONFIRMED",
            reason="Dolor pélvico persistente",
        )
        db.add(app)
        await db.commit()

    # 1. Crear historia con receta medica
    prescription_data = {
        "items": [
            {
                "medication": "Ibuprofeno",
                "dosage": "600 mg",
                "frequency": "Cada 8 horas",
                "duration": "5 días",
                "instructions": "Tomar después de los alimentos",
            },
            {
                "medication": "Anticonceptivo Oral Combinado",
                "dosage": "1 comprimido",
                "frequency": "Diario a la misma hora",
                "duration": "28 días",
                "instructions": "Iniciar el primer día del ciclo",
            },
        ],
        "diagnosis_summary": "Manejo de Dismenorrea y Planificación Familiar",
        "notes": "Acudir a reevaluación en 30 días si el dolor no cede.",
        "duration_days": 30,
    }

    create_payload = {
        "appointment_id": appointment_id,
        "anamnesis": "Paciente con dismenorrea severa incapacitante en los primeros dos días.",
        "physical_exam": "Abdomen no doloroso a la descompresion.",
        "diagnosis": "Dismenorrea primaria moderada-severa.",
        "plan": "Terapia con AINEs y regulacion de ciclo.",
        "icd10_code": "N94.4",
        "icd10_description": "Dismenorrea primaria",
        "prescription": prescription_data,
    }

    resp = await client.post(
        "/api/v1/medical-records",
        json=create_payload,
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["prescriptions"]) == 1
    presc = data["prescriptions"][0]
    presc_id = presc["id"]
    verification_hash = presc["verification_hash"]
    assert len(verification_hash) == 64

    # 2. VERIFICACION PUBLICA SIN AUTENTICACION (Para Farmacias via Codigo QR)
    resp_verify = await client.get(f"/api/v1/medical-records/prescriptions/verify/{verification_hash}")
    assert resp_verify.status_code == 200
    verify_data = resp_verify.json()
    assert verify_data["is_valid"] is True
    assert verify_data["doctor_name"] == "Dr. Alejandro Morales"
    assert verify_data["patient_name"] is not None
    assert len(verify_data["items"]) == 2
    assert verify_data["items"][0]["medication"] == "Ibuprofeno"
    # Asegurar que NO se exponga la anamnesis intima en el endpoint publico
    assert "anamnesis" not in verify_data
    assert "dismenorrea severa incapacitante" not in str(verify_data)

    # 3. DESCARGA DEL PDF OFICIAL DE LA RECETA CON QR INCRUSTADO
    resp_pdf = await client.get(
        f"/api/v1/medical-records/prescriptions/{presc_id}/pdf",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert resp_pdf.status_code == 200
    assert resp_pdf.headers["content-type"] == "application/pdf"
    assert resp_pdf.content.startswith(b"%PDF")
    assert len(resp_pdf.content) > 1000  # PDF valido con estructura y QR binario
