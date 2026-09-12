import datetime
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_patient_dependent_registration_and_emancipation(client: AsyncClient):
    # 1. Login como Paciente
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Registrar dependiente menor de edad (hija de 6 años)
    minor_birth = datetime.date.today() - datetime.timedelta(days=6 * 365)
    minor_resp = await client.post(
        "/api/v1/patients/me/dependents",
        json={
            "full_name": "Sofía López",
            "relationship": "HIJO",
            "birth_date": minor_birth.isoformat(),
            "gender": "F",
        },
        headers=headers,
    )
    assert minor_resp.status_code == 201
    minor_data = minor_resp.json()
    assert minor_data["full_name"] == "Sofía López"
    assert minor_data["emancipation_status"] == "MINOR"
    assert minor_data["is_emancipated"] is False

    # 3. Registrar dependiente mayor de edad (madre de 55 años)
    adult_birth = datetime.date.today() - datetime.timedelta(days=55 * 365)
    adult_resp = await client.post(
        "/api/v1/patients/me/dependents",
        json={
            "full_name": "Carmen de López",
            "relationship": "PADRE",
            "birth_date": adult_birth.isoformat(),
            "gender": "F",
        },
        headers=headers,
    )
    assert adult_resp.status_code == 201
    adult_data = adult_resp.json()
    assert adult_data["emancipation_status"] == "EMANCIPATED"
    assert adult_data["is_emancipated"] is True

    # 4. Listar dependientes del paciente titular
    list_resp = await client.get("/api/v1/patients/me/dependents", headers=headers)
    assert list_resp.status_code == 200
    deps = list_resp.json()
    assert len(deps) >= 2
    assert any(d["full_name"] == "Sofía López" for d in deps)
    assert any(d["full_name"] == "Carmen de López" for d in deps)
