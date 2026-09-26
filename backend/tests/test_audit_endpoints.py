import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_audit_logs_query_and_permissions(client: AsyncClient):
    # 1. Login como Paciente: No debe tener acceso a /api/v1/audit/logs
    pat_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert pat_login.status_code == 200
    pat_token = pat_login.json()["access_token"]
    pat_headers = {"Authorization": f"Bearer {pat_token}"}

    forbidden_resp = await client.get("/api/v1/audit/logs", headers=pat_headers)
    assert forbidden_resp.status_code == 403

    # 2. Login como Compliance Reviewer (moderador)
    comp_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "moderador@vitarecord.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert comp_login.status_code == 200
    comp_token = comp_login.json()["access_token"]
    comp_headers = {"Authorization": f"Bearer {comp_token}"}

    # 3. Consultar pistas de auditoría
    audit_resp = await client.get("/api/v1/audit/logs?limit=20", headers=comp_headers)
    assert audit_resp.status_code == 200
    data = audit_resp.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert data["limit"] == 20
    assert data["offset"] == 0

    # 4. Login como Médico y realizar búsqueda de pacientes para generar pista
    doc_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "doctor@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert doc_login.status_code == 200
    doc_token = doc_login.json()["access_token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    search_resp = await client.get("/api/v1/medical-records/doctor/my-patients?q=Ana", headers=doc_headers)
    assert search_resp.status_code == 200

    # 5. Compliance consulta filtrando por acción SEARCH_PATIENTS
    filtered_resp = await client.get("/api/v1/audit/logs?action=SEARCH_PATIENTS", headers=comp_headers)
    assert filtered_resp.status_code == 200
    filtered_data = filtered_resp.json()
    assert filtered_data["total"] >= 1
    assert any(item["action"] == "SEARCH_PATIENTS" for item in filtered_data["items"])
