import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_clinic_analytics_dashboard_metrics(client: AsyncClient):
    # 1. Login como SuperAdmin
    admin_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@vitarecord.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Consultar lista de clínicas
    clinics_resp = await client.get("/api/v1/clinics", headers=admin_headers)
    assert clinics_resp.status_code == 200
    clinics = clinics_resp.json()
    assert len(clinics) >= 1
    clinic_id = clinics[0]["id"]

    # 3. SuperAdmin consulta analytics de la clínica
    analytics_resp = await client.get(
        f"/api/v1/clinics/{clinic_id}/analytics?days=30",
        headers=admin_headers,
    )
    assert analytics_resp.status_code == 200
    data = analytics_resp.json()

    assert data["clinic_id"] == clinic_id
    assert "clinic_name" in data
    assert "kpis" in data
    assert "total_appointments" in data["kpis"]
    assert "total_revenue" in data["kpis"]
    assert "active_doctors" in data["kpis"]
    assert "attendance_rate_pct" in data["kpis"]

    assert isinstance(data["trends"], list)
    assert isinstance(data["status_distribution"], list)
    assert isinstance(data["payment_methods"], list)
    assert isinstance(data["specialties"], list)
    assert isinstance(data["top_doctors"], list)
    assert isinstance(data["room_utilization"], list)
    assert isinstance(data["today_appointments"], list)


@pytest.mark.anyio
async def test_clinic_admin_isolation_analytics(client: AsyncClient):
    # 1. Login como Clinic Admin
    staff_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "clinic.admin@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert staff_login.status_code == 200
    staff_token = staff_login.json()["access_token"]
    staff_headers = {"Authorization": f"Bearer {staff_token}"}

    # 2. Obtener perfil para conocer su clinic_id
    from app.core.security import decode_token
    payload = decode_token(staff_token)
    my_clinic_id = payload.get("clinic_id")
    assert my_clinic_id is not None

    # 3. Puede consultar sus propios datos
    own_resp = await client.get(
        f"/api/v1/clinics/{my_clinic_id}/analytics?days=30",
        headers=staff_headers,
    )
    assert own_resp.status_code == 200
    assert own_resp.json()["clinic_id"] == my_clinic_id

    # 4. Intento de consultar otra clínica ajena debe ser denegado con 403
    foreign_clinic_id = "c2222222-2222-2222-2222-222222222222"
    if my_clinic_id == foreign_clinic_id:
        foreign_clinic_id = "c1111111-1111-1111-1111-111111111111"

    forbidden_resp = await client.get(
        f"/api/v1/clinics/{foreign_clinic_id}/analytics?days=30",
        headers=staff_headers,
    )
    assert forbidden_resp.status_code == 403
