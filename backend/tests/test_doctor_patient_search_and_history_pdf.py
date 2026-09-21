import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.models.audit import AuditLog
from app.models.medical_record import MedicalRecord


@pytest.mark.asyncio
async def test_doctor_search_attended_patients_and_download_history_pdf(client: AsyncClient):
    """Verifica la búsqueda de pacientes atendidos por el médico y la exportación de historia clínica en PDF."""
    clinic_id = "c1111111-1111-1111-1111-111111111111"
    doctor_id = "u2222222-2222-2222-2222-222222222222"
    other_doctor_id = "u2222222-2222-2222-2222-222222222223"

    doctor_token = create_access_token(
        subject=doctor_id,
        clinic_id=clinic_id,
        role="DOCTOR",
        email="doctor@intimasalud.com",
    )
    other_doctor_token = create_access_token(
        subject=other_doctor_id,
        clinic_id=clinic_id,
        role="DOCTOR",
        email="dra.castillo@intimasalud.com",
    )
    doctor_headers = {"Authorization": f"Bearer {doctor_token}"}
    other_headers = {"Authorization": f"Bearer {other_doctor_token}"}

    # 1. Listar pacientes atendidos por el médico
    resp = await client.get("/api/v1/medical-records/doctor/my-patients", headers=doctor_headers)
    assert resp.status_code == 200
    patients = resp.json()
    assert len(patients) >= 1

    # Verificar estructura del payload
    first_patient = patients[0]
    assert "patient_id" in first_patient
    assert "full_name" in first_patient
    assert "total_consultations" in first_patient
    assert first_patient["total_consultations"] >= 1

    # 2. Búsqueda con filtro textual (q)
    target_name_part = first_patient["full_name"][:4]
    resp_q = await client.get(
        f"/api/v1/medical-records/doctor/my-patients?q={target_name_part}",
        headers=doctor_headers,
    )
    assert resp_q.status_code == 200
    q_results = resp_q.json()
    assert len(q_results) >= 1
    assert any(target_name_part.lower() in p["full_name"].lower() for p in q_results)

    # 3. Filtro por tipo: TITULAR y DEPENDENT
    resp_titular = await client.get(
        "/api/v1/medical-records/doctor/my-patients?filter=TITULAR",
        headers=doctor_headers,
    )
    assert resp_titular.status_code == 200
    for p in resp_titular.json():
        assert p["is_dependent"] is False
        assert p["relationship"] == "TITULAR"

    resp_dep = await client.get(
        "/api/v1/medical-records/doctor/my-patients?filter=DEPENDENT",
        headers=doctor_headers,
    )
    assert resp_dep.status_code == 200
    for p in resp_dep.json():
        assert p["is_dependent"] is True

    # 4. Generación y descarga de la historia clínica en PDF
    target_patient_id = first_patient["patient_id"]
    pdf_url = f"/api/v1/medical-records/patient/{target_patient_id}/pdf"
    if first_patient["dependent_id"]:
        pdf_url += f"?dependent_id={first_patient['dependent_id']}"

    resp_pdf = await client.get(pdf_url, headers=doctor_headers)
    assert resp_pdf.status_code == 200
    assert resp_pdf.headers["content-type"] == "application/pdf"
    assert resp_pdf.content.startswith(b"%PDF-1.4")
    assert len(resp_pdf.content) > 1000

    # 5. Verificar auditoría inmutable de la descarga
    async with AsyncSessionLocal() as db:
        audit_stmt = (
            select(AuditLog)
            .where(
                AuditLog.action == "DOWNLOAD_PDF",
                AuditLog.entity_type == "medical_history",
                AuditLog.user_id == doctor_id,
            )
            .order_by(AuditLog.created_at.desc())
        )
        audit_entry = (await db.execute(audit_stmt)).scalars().first()
        assert audit_entry is not None
        assert audit_entry.details.get("patient_id") == target_patient_id
