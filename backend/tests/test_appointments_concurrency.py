import datetime
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_appointment_mutex_lock_and_double_booking_prevention(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"
    doctor_id = "u2222222-2222-2222-2222-222222222222"
    room_id = "r1111111-1111-1111-1111-111111111111"

    # 1. Login como Paciente
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200
    patient_token = login_resp.json()["access_token"]
    patient_headers = {"Authorization": f"Bearer {patient_token}"}

    # Definir horario de cita con fecha dinámica para idempotencia
    import random
    delta_days = 200 + random.randint(1, 10000)
    start_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=delta_days, hours=10)
    end_dt = start_dt + datetime.timedelta(minutes=30)

    booking_payload = {
        "clinic_id": clinic_id,
        "doctor_id": doctor_id,
        "room_id": room_id,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "reason": "Consulta ginecológica de rutina",
        "estimated_amount": 35.00,
        "currency": "USD",
    }

    # 2. Primera reserva -> DEBE SER EXITOSA (201)
    resp1 = await client.post(
        "/api/v1/appointments",
        json=booking_payload,
        headers=patient_headers,
    )
    assert resp1.status_code == 201
    app1 = resp1.json()
    assert app1["status"] == "CONFIRMED"
    assert app1["doctor_id"] == doctor_id
    assert app1["room_id"] == room_id
    assert app1["payment_status"] == "UNPAID"

    # 3. Segunda reserva idéntica o solapada (ej. 10:15 a 10:45) -> DEBE RETORNAR 409 CONFLICT
    overlapping_payload = {
        "clinic_id": clinic_id,
        "doctor_id": doctor_id,
        "room_id": room_id,
        "start_time": datetime.datetime(2026, 9, 20, 10, 15, 0).isoformat(),
        "end_time": datetime.datetime(2026, 9, 20, 10, 45, 0).isoformat(),
        "reason": "Intento de segunda reserva en conflicto",
    }

    resp2 = await client.post(
        "/api/v1/appointments",
        json=overlapping_payload,
        headers=patient_headers,
    )
    assert resp2.status_code == 409
    assert "Conflicto" in resp2.json()["detail"]
