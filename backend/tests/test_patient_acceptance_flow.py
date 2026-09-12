import datetime
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_patient_acceptance_rejection_and_payment_states(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"
    doctor_id = "u2222222-2222-2222-2222-222222222222"
    room_id = "r1111111-1111-1111-1111-111111111111"

    # 1. Login Recepción
    rec_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "recepcion@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert rec_login.status_code == 200
    rec_token = rec_login.json()["access_token"]
    rec_headers = {"Authorization": f"Bearer {rec_token}"}

    # 2. Login Paciente
    pat_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert pat_login.status_code == 200
    pat_token = pat_login.json()["access_token"]
    pat_headers = {"Authorization": f"Bearer {pat_token}"}
    pat_me = await client.get("/api/v1/auth/me", headers=pat_headers)
    patient_id = pat_me.json()["id"]

    # 3. Recepción agenda cita para el paciente -> PENDING_PATIENT_ACCEPTANCE
    import random
    delta = datetime.timedelta(days=random.randint(1000, 20000), hours=9)
    start_dt = datetime.datetime.now(datetime.timezone.utc) + delta
    end_dt = start_dt + datetime.timedelta(minutes=30)

    book_resp = await client.post(
        "/api/v1/appointments",
        json={
            "clinic_id": clinic_id,
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "room_id": room_id,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "reason": "Control prenatal asignado por llamada",
            "estimated_amount": 40.00,
        },
        headers=rec_headers,
    )
    assert book_resp.status_code == 201
    app_data = book_resp.json()
    assert app_data["status"] == "PENDING_PATIENT_ACCEPTANCE"
    assert app_data["payment_status"] == "UNPAID"
    app_id = app_data["id"]

    # 4. Paciente rechaza la cita -> REJECTED_BY_PATIENT, pago a EXEMPT
    reject_resp = await client.post(
        f"/api/v1/appointments/{app_id}/reject",
        headers=pat_headers,
    )
    assert reject_resp.status_code == 200
    rejected_app = reject_resp.json()
    assert rejected_app["status"] == "REJECTED_BY_PATIENT"
    assert rejected_app["payment_status"] == "EXEMPT"

    # 5. El slot ahora está libre: volver a agendar en ese mismo horario debe ser EXITOSO
    rebook_resp = await client.post(
        "/api/v1/appointments",
        json={
            "clinic_id": clinic_id,
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "room_id": room_id,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "reason": "Re-agenda exitosa en slot liberado",
        },
        headers=rec_headers,
    )
    assert rebook_resp.status_code == 201
    app2_id = rebook_resp.json()["id"]

    # 6. Paciente acepta la nueva cita -> CONFIRMED
    accept_resp = await client.post(
        f"/api/v1/appointments/{app2_id}/accept",
        headers=pat_headers,
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "CONFIRMED"

    # 7. Paciente cancela la cita -> CANCELLED_BY_PATIENT, pago a VOID
    cancel_resp = await client.post(
        f"/api/v1/appointments/{app2_id}/cancel",
        json={"cancellation_reason": "Incompatibilidad de horario laboral"},
        headers=pat_headers,
    )
    assert cancel_resp.status_code == 200
    cancelled_app = cancel_resp.json()
    assert cancelled_app["status"] == "CANCELLED_BY_PATIENT"
    assert cancelled_app["payment_status"] == "VOID"
