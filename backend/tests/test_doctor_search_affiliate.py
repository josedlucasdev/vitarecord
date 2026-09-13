import uuid
import pytest
from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.clinic import Clinic
from app.models.user import User
from app.core.security import hash_password, create_access_token


@pytest.mark.anyio
async def test_search_and_affiliate_existing_doctor(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    clinic_id = f"c-search-{suffix}"
    admin_id = f"u-admin-{suffix}"
    doctor_id = f"u-doc-{suffix}"

    async with AsyncSessionLocal() as db:
        clinic = Clinic(id=clinic_id, name=f"Clínica Search {suffix}", slug=f"clinica-search-{suffix}", country_code="VE")
        admin = User(
            id=admin_id,
            email=f"admin.{suffix}@intimasalud.com",
            role="CLINIC_ADMIN",
            status="ACTIVE",
            clinic_id=clinic_id,
            hashed_password=hash_password("Password123!"),
        )
        doctor = User(
            id=doctor_id,
            email=f"dr.especialista.{suffix}@intimasalud.com",
            full_name=f"Dr. Carlos Mendoza {suffix}",
            role="DOCTOR",
            status="ACTIVE",
            license_number=f"MP-{suffix}",
            identification_number=f"V-{suffix[:7]}",
            specialty="Ginecología & Obstetricia",
            license_verification_status="VERIFIED",
            hashed_password=hash_password("Password123!"),
        )
        db.add_all([clinic, admin, doctor])
        await db.commit()

    token = create_access_token(admin_id, clinic_id=clinic_id, role="CLINIC_ADMIN")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Búsqueda por nombre
    resp_name = await client.get(
        f"/api/v1/clinics/{clinic_id}/doctors/search-to-affiliate?q=Carlos",
        headers=headers,
    )
    assert resp_name.status_code == 200
    results = resp_name.json()
    assert any(d["id"] == doctor_id for d in results)
    doc_found = next(d for d in results if d["id"] == doctor_id)
    assert doc_found["is_already_affiliated"] is False

    # 2. Búsqueda por cédula / documento
    resp_id = await client.get(
        f"/api/v1/clinics/{clinic_id}/doctors/search-to-affiliate?q={suffix[:7]}",
        headers=headers,
    )
    assert resp_id.status_code == 200
    assert any(d["id"] == doctor_id for d in resp_id.json())

    # 3. Búsqueda por matrícula
    resp_lic = await client.get(
        f"/api/v1/clinics/{clinic_id}/doctors/search-to-affiliate?q=MP-{suffix}",
        headers=headers,
    )
    assert resp_lic.status_code == 200
    assert any(d["id"] == doctor_id for d in resp_lic.json())

    # 4. Afiliar directamente
    aff_resp = await client.post(
        f"/api/v1/clinics/{clinic_id}/doctors/{doctor_id}/affiliate",
        json={"mode": "DIRECT"},
        headers=headers,
    )
    assert aff_resp.status_code == 200
    assert aff_resp.json()["status"] == "ACTIVE"

    # 5. Volver a buscar y comprobar que ahora is_already_affiliated es True
    resp_after = await client.get(
        f"/api/v1/clinics/{clinic_id}/doctors/search-to-affiliate?q=Carlos",
        headers=headers,
    )
    assert resp_after.status_code == 200
    doc_after = next(d for d in resp_after.json() if d["id"] == doctor_id)
    assert doc_after["is_already_affiliated"] is True

    # 6. Crear un segundo médico para probar el flujo de invitación con query param (sin body JSON)
    suffix2 = uuid.uuid4().hex[:6]
    doc2_id = f"u-doc2-{suffix2}"
    async with AsyncSessionLocal() as db:
        doctor2 = User(
            id=doc2_id,
            email=f"beatriz_{suffix2}@vitarecord.com",
            full_name=f"Dra. Beatriz Gomez {suffix2}",
            role="DOCTOR",
            status="ACTIVE",
            license_number=f"MP2-{suffix2}",
            specialty="Mastología",
            hashed_password=hash_password("Password123!"),
        )
        db.add(doctor2)
        await db.commit()

    try:
        # Invitar médico con query param y sin body JSON (debe responder 200 sin error 422)
        invite_resp = await client.post(
            f"/api/v1/clinics/{clinic_id}/doctors/{doc2_id}/affiliate?mode=INVITE",
            headers=headers,
        )
        assert invite_resp.status_code == 200
        assert invite_resp.json()["success"] is True
        assert invite_resp.json()["mode"] == "INVITE"
        assert "invitation_link" in invite_resp.json()
    finally:
        from sqlalchemy import delete
        from app.models.affiliation import DoctorClinicAffiliation
        from app.models.schedule import DoctorWeeklySchedule
        from app.models.user import DoctorScheduleLock
        async with AsyncSessionLocal() as db:
            await db.execute(delete(DoctorWeeklySchedule).where(DoctorWeeklySchedule.clinic_id == clinic_id))
            await db.execute(delete(DoctorClinicAffiliation).where(DoctorClinicAffiliation.clinic_id == clinic_id))
            await db.execute(delete(DoctorScheduleLock).where(DoctorScheduleLock.doctor_id.in_([doctor_id, doc2_id])))
            await db.execute(delete(User).where(User.id.in_([admin_id, doctor_id, doc2_id])))
            await db.execute(delete(Clinic).where(Clinic.id == clinic_id))
            await db.commit()
