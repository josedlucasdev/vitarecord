"""Pruebas para el directorio médico público y gestión de perfil profesional en VitaRecord."""

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_public_clinics_endpoint_no_auth(client: AsyncClient):
    """Verifica que el listado público de clínicas no requiera autenticación."""
    resp = await client.get("/api/v1/clinics/public")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "name" in data[0]
    assert "slug" in data[0]


@pytest.mark.asyncio
async def test_public_doctors_directory_no_auth(client: AsyncClient):
    """Verifica que cualquier visitante pueda consultar el directorio médico sin token."""
    resp = await client.get("/api/v1/doctors/public-directory")
    assert resp.status_code == 200
    doctors = resp.json()
    assert isinstance(doctors, list)
    assert len(doctors) >= 1

    first_doc = doctors[0]
    assert "full_name" in first_doc
    assert "specialty" in first_doc
    assert "clinics" in first_doc
    assert "academic_degrees" in first_doc
    assert "work_experience" in first_doc


@pytest.mark.asyncio
async def test_public_doctors_directory_filters(client: AsyncClient):
    """Verifica el filtrado por especialidad y búsqueda por texto."""
    # Filtrar por especialidad
    resp_spec = await client.get("/api/v1/doctors/public-directory?specialty=Ginecolog")
    assert resp_spec.status_code == 200
    doctors_spec = resp_spec.json()
    assert len(doctors_spec) >= 1
    for doc in doctors_spec:
        assert "ginec" in doc["specialty"].lower() or "obstetricia" in doc["specialty"].lower()

    # Búsqueda por texto (Dr. Alejandro Morales)
    resp_search = await client.get("/api/v1/doctors/public-directory?search=Alejandro")
    assert resp_search.status_code == 200
    doctors_search = resp_search.json()
    assert len(doctors_search) >= 1
    assert any("Alejandro" in d["full_name"] for d in doctors_search)


@pytest.mark.asyncio
async def test_doctor_profile_self_management(client: AsyncClient):
    """Verifica que un médico pueda consultar y actualizar sus títulos y experiencia."""
    doctor_token = create_access_token(
        "u2222222-2222-2222-2222-222222222222",
        role="DOCTOR",
        email="doctor@intimasalud.com",
    )
    headers = {"Authorization": f"Bearer {doctor_token}"}

    # 1. Obtener mi perfil
    get_resp = await client.get("/api/v1/doctors/me/profile", headers=headers)
    assert get_resp.status_code == 200
    profile = get_resp.json()
    assert profile["email"] == "doctor@intimasalud.com"

    # 2. Actualizar perfil con nuevos títulos y experiencia
    update_payload = {
        "biography": "Especialista senior en cirugía robótica y salud reproductiva.",
        "phone": "+584129998877",
        "specialty": "Ginecología Avanzada",
        "is_public_profile_enabled": True,
        "academic_degrees": [
            {"title": "Médico Cirujano", "institution": "Universidad Central de Venezuela", "year": 2011, "license_or_id": "MPPS-12948"},
            {"title": "Magister en Cirugía Ginecológica", "institution": "Universidad de Barcelona", "year": 2019, "license_or_id": "UB-4029"},
        ],
        "work_experience": [
            {"position": "Director de Unidad Ginecológica", "workplace": "Clínica ÍntimaSalud Central", "start_year": 2019, "end_year": None, "description": "Atención especializada y docencia."},
        ],
    }

    put_resp = await client.put("/api/v1/doctors/me/profile", json=update_payload, headers=headers)
    assert put_resp.status_code == 200
    updated = put_resp.json()
    assert updated["biography"] == "Especialista senior en cirugía robótica y salud reproductiva."
    assert len(updated["academic_degrees"]) == 2
    assert updated["academic_degrees"][1]["title"] == "Magister en Cirugía Ginecológica"
    assert len(updated["work_experience"]) == 1


@pytest.mark.asyncio
async def test_doctor_avatar_upload_and_delete(client: AsyncClient):
    """Verifica la subida, consulta y eliminación de la foto de perfil del médico."""
    doctor_token = create_access_token(
        "u2222222-2222-2222-2222-222222222222",
        role="DOCTOR",
        email="doctor@intimasalud.com",
    )
    headers = {"Authorization": f"Bearer {doctor_token}"}

    # 1. Subir imagen válida (PNG mínimo)
    dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    files = {"file": ("avatar.png", dummy_png, "image/png")}

    upload_resp = await client.post("/api/v1/doctors/me/avatar", files=files, headers=headers)
    assert upload_resp.status_code == 200
    assert "profile_picture_url" in upload_resp.json()
    assert "/api/v1/doctors/u2222222-2222-2222-2222-222222222222/avatar" in upload_resp.json()["profile_picture_url"]

    # 2. Consultar avatar públicamente
    get_avatar = await client.get("/api/v1/doctors/u2222222-2222-2222-2222-222222222222/avatar")
    assert get_avatar.status_code == 200
    assert get_avatar.headers["content-type"] == "image/png"

    # 3. Eliminar avatar
    del_resp = await client.delete("/api/v1/doctors/me/avatar", headers=headers)
    assert del_resp.status_code == 200

    # 4. Verificar que se eliminó
    get_avatar_after = await client.get("/api/v1/doctors/u2222222-2222-2222-2222-222222222222/avatar")
    assert get_avatar_after.status_code == 404


@pytest.mark.asyncio
async def test_doctor_change_password(client: AsyncClient):
    """Verifica el flujo de cambio de contraseña autenticado."""
    doctor_token = create_access_token(
        "u2222222-2222-2222-2222-222222222222",
        role="DOCTOR",
        email="doctor@intimasalud.com",
    )
    headers = {"Authorization": f"Bearer {doctor_token}"}

    # 1. Intento con contraseña actual incorrecta
    bad_resp = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "WrongPassword123!", "new_password": "NewSecretPassword123!"},
        headers=headers,
    )
    assert bad_resp.status_code == 400
    assert "actual no es correcta" in bad_resp.json()["detail"]

    # 2. Intento con nueva contraseña demasiado corta
    short_resp = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Password123!", "new_password": "short"},
        headers=headers,
    )
    assert short_resp.status_code == 400
    assert "al menos 8 caracteres" in short_resp.json()["detail"]

    # 3. Cambio exitoso
    ok_resp = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Password123!", "new_password": "NewValidPassword2026!"},
        headers=headers,
    )
    assert ok_resp.status_code == 200
    assert "exitosamente" in ok_resp.json()["message"]

    # 4. Restaurar contraseña para no romper otras pruebas posteriores
    restore_resp = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "NewValidPassword2026!", "new_password": "Password123!"},
        headers=headers,
    )
    assert restore_resp.status_code == 200


@pytest.mark.asyncio
async def test_doctor_clinic_disaffiliation(client: AsyncClient):
    """Verifica que el médico pueda desvincularse de una sede clínica y notificar a administración."""
    doctor_token = create_access_token(
        "u2222222-2222-2222-2222-222222222222",
        role="DOCTOR",
        email="doctor@intimasalud.com",
    )
    headers = {"Authorization": f"Bearer {doctor_token}"}

    # 1. Obtener clínicas actuales
    prof_resp = await client.get("/api/v1/doctors/me/profile", headers=headers)
    assert prof_resp.status_code == 200
    clinics = prof_resp.json().get("clinics", [])
    if not clinics:
        pytest.skip("No hay clínicas afiliadas en datos de prueba")

    target_clinic = clinics[0]
    clinic_id = target_clinic["id"]

    # 2. Desvincularse
    disaff_resp = await client.post(f"/api/v1/doctors/me/clinics/{clinic_id}/disaffiliate", headers=headers)
    assert disaff_resp.status_code == 200
    assert "desvinculado exitosamente" in disaff_resp.json()["message"]

    # 3. Verificar que ya no está en el listado activo
    prof_after = await client.get("/api/v1/doctors/me/profile", headers=headers)
    remaining_ids = [c["id"] for c in prof_after.json().get("clinics", [])]
    assert clinic_id not in remaining_ids

    # 4. Restaurar afiliación para no afectar otras suites de pruebas
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.affiliation import DoctorClinicAffiliation
    async with AsyncSessionLocal() as session:
        aff = await session.scalar(
            select(DoctorClinicAffiliation).where(
                DoctorClinicAffiliation.doctor_id == "u2222222-2222-2222-2222-222222222222",
                DoctorClinicAffiliation.clinic_id == clinic_id,
            )
        )
        if aff:
            aff.status = "ACTIVE"
            await session.commit()
