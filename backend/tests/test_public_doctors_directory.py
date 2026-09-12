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
