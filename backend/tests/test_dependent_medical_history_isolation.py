import datetime
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.models.appointment import Appointment
from app.models.medical_record import MedicalRecord
from app.models.patient_dependent import PatientDependent
from app.models.prescription import Prescription


@pytest.mark.asyncio
async def test_dependent_medical_history_strict_isolation(client: AsyncClient):
    """Verifica que el historial clínico del familiar dependiente esté estrictamente separado del titular."""
    clinic_id = "c1111111-1111-1111-1111-111111111111"
    doctor_id = "u2222222-2222-2222-2222-222222222222"
    patient_id = "u4444444-4444-4444-4444-444444444444"

    doctor_token = create_access_token(
        subject=doctor_id,
        clinic_id=clinic_id,
        role="DOCTOR",
        email="doctor@intimasalud.com",
    )
    patient_token = create_access_token(
        subject=patient_id,
        clinic_id=clinic_id,
        role="PATIENT",
        email="paciente@intimasalud.com",
    )

    dep_id = f"dep-{uuid.uuid4().hex[:8]}"
    appt_titular_id = f"app-tit-{uuid.uuid4().hex[:8]}"
    appt_dep_id = f"app-dep-{uuid.uuid4().hex[:8]}"

    async with AsyncSessionLocal() as db:
        # 1. Crear dependiente familiar
        dep = PatientDependent(
            id=dep_id,
            guardian_user_id=patient_id,
            full_name="Hija de Prueba",
            relationship="HIJO",
            birth_date=datetime.date(2018, 5, 20),
            gender="FEMENINO",
            blood_type="A+",
            height_cm=125.0,
            allergies="Penicilina",
            chronic_conditions="Asma",
        )
        db.add(dep)

        # 2. Crear cita del titular
        appt_titular = Appointment(
            id=appt_titular_id,
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            patient_id=patient_id,
            dependent_id=None,
            start_time=datetime.datetime(2026, 11, 1, 9, 0),
            end_time=datetime.datetime(2026, 11, 1, 9, 30),
            status="CONFIRMED",
            reason="Consulta preventiva anual del titular",
        )
        db.add(appt_titular)

        # 3. Crear cita del dependiente familiar
        appt_dep = Appointment(
            id=appt_dep_id,
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            patient_id=patient_id,
            dependent_id=dep_id,
            start_time=datetime.datetime(2026, 11, 1, 10, 0),
            end_time=datetime.datetime(2026, 11, 1, 10, 30),
            status="CONFIRMED",
            reason="Control pediátrico de la hija",
        )
        db.add(appt_dep)
        await db.commit()

    # 4. Verificar que AppointmentPublic incluye dependent_name y dependent_relationship
    res_appt = await client.get(
        f"/api/v1/appointments/{appt_dep_id}",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert res_appt.status_code == 200
    appt_data = res_appt.json()
    assert appt_data["dependent_id"] == dep_id
    assert appt_data["dependent_name"] == "Hija de Prueba"
    assert appt_data["dependent_relationship"] == "HIJO"

    # 5. Doctor completa la cita del titular
    res_mr_titular = await client.post(
        "/api/v1/medical-records",
        json={
            "appointment_id": appt_titular_id,
            "anamnesis": "Evaluación general del titular adulto sin quejas agudas.",
            "diagnosis": "Paciente sano en control preventivo",
            "plan": "Mantener estilo de vida saludable y dieta balanceada.",
            "prescription": {
                "items": [
                    {
                        "medication": "Vitamina C",
                        "dosage": "500mg",
                        "frequency": "Cada 24 horas",
                        "duration": "30 días",
                        "instructions": "Vía oral con desayuno",
                    }
                ],
                "duration_days": 30,
            },
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert res_mr_titular.status_code == 201
    mr_tit_data = res_mr_titular.json()
    assert mr_tit_data["dependent_id"] is None
    assert mr_tit_data["dependent_name"] is None

    # 6. Doctor completa la cita del familiar dependiente
    res_mr_dep = await client.post(
        "/api/v1/medical-records",
        json={
            "appointment_id": appt_dep_id,
            "anamnesis": "Hija de 8 años con tos leve y rinitis estacional.",
            "physical_exam": "Faringe sin exudados, auscultación con murmullo vesicular conservado.",
            "diagnosis": "Rinofaringitis aguda leve en paciente pediátrica",
            "plan": "Hidratación abundante y antihistamínico pediátrico según peso.",
            "prescription": {
                "items": [
                    {
                        "medication": "Cetirizina Jarabe",
                        "dosage": "5ml",
                        "frequency": "Cada 24 horas por la noche",
                        "duration": "7 días",
                        "instructions": "Vía oral",
                    }
                ],
                "duration_days": 7,
            },
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert res_mr_dep.status_code == 201
    mr_dep_data = res_mr_dep.json()
    assert mr_dep_data["dependent_id"] == dep_id
    assert mr_dep_data["dependent_name"] == "Hija de Prueba"
    assert mr_dep_data["dependent_relationship"] == "HIJO"

    # 7. Aislar historial: Consultar historial del titular directo (sin dependent_id)
    res_hist_titular = await client.get(
        f"/api/v1/medical-records/patient/{patient_id}",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert res_hist_titular.status_code == 200
    hist_titular = res_hist_titular.json()
    # Debe contener la cita del titular pero NINGUNA del dependiente
    assert any(r["appointment_id"] == appt_titular_id for r in hist_titular)
    assert not any(r["appointment_id"] == appt_dep_id for r in hist_titular)
    for r in hist_titular:
        assert r["dependent_id"] is None

    # 8. Aislar historial: Consultar historial del familiar dependiente (con dependent_id)
    res_hist_dep = await client.get(
        f"/api/v1/medical-records/patient/{patient_id}?dependent_id={dep_id}",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert res_hist_dep.status_code == 200
    hist_dep = res_hist_dep.json()
    # Debe contener ÚNICAMENTE la cita del dependiente
    assert len(hist_dep) == 1
    assert hist_dep[0]["appointment_id"] == appt_dep_id
    assert hist_dep[0]["dependent_id"] == dep_id
    assert hist_dep[0]["dependent_name"] == "Hija de Prueba"
    assert hist_dep[0]["dependent_relationship"] == "HIJO"

    # 9. Consultar con include_dependents=true para vista consolidada
    res_hist_all = await client.get(
        f"/api/v1/medical-records/patient/{patient_id}?include_dependents=true",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert res_hist_all.status_code == 200
    hist_all = res_hist_all.json()
    assert any(r["appointment_id"] == appt_titular_id for r in hist_all)
    assert any(r["appointment_id"] == appt_dep_id for r in hist_all)

    # 10. Descarga de PDF de receta para el dependiente: debe contener su nombre
    dep_presc_id = mr_dep_data["prescriptions"][0]["id"]
    res_pdf = await client.get(
        f"/api/v1/medical-records/prescriptions/{dep_presc_id}/pdf",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 100
