import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_superadmin_can_create_and_list_clinics(client: AsyncClient):
    # 1. Login como SuperAdmin
    admin_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Listar clinicas
    list_resp = await client.get("/api/v1/clinics", headers=admin_headers)
    assert list_resp.status_code == 200
    clinics = list_resp.json()
    assert len(clinics) >= 1

    # 3. Crear nueva clinica (tenant)
    slug = f"clinica-norte-{uuid.uuid4().hex[:6]}"
    create_resp = await client.post(
        "/api/v1/clinics",
        json={
            "name": "Clínica ÍntimaSalud Norte",
            "slug": slug,
            "timezone": "America/Caracas",
            "country_code": "VE",
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["slug"] == slug
    assert data["is_active"] is True

    # Limpieza del tenant temporal de prueba para mantener la base de datos limpia
    from app.core.database import AsyncSessionLocal
    from app.models.clinic import Clinic
    async with AsyncSessionLocal() as db:
        c_obj = await db.get(Clinic, data["id"])
        if c_obj:
            await db.delete(c_obj)
            await db.commit()



@pytest.mark.anyio
async def test_non_superadmin_cannot_create_clinics(client: AsyncClient):
    # Login como Paciente
    patient_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    patient_token = patient_login.json()["access_token"]
    patient_headers = {"Authorization": f"Bearer {patient_token}"}

    # Intento de creacion
    create_resp = await client.post(
        "/api/v1/clinics",
        json={
            "name": "Clínica No Autorizada",
            "slug": "clinica-no-autorizada",
            "timezone": "America/Caracas",
            "country_code": "VE",
        },
        headers=patient_headers,
    )
    assert create_resp.status_code == 403
