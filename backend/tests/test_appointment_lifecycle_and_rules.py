import datetime
import random
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User


@pytest.mark.anyio
async def test_appointment_lifecycle_transitions_and_rules(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"
    doctor_id = "u2222222-2222-2222-2222-222222222222"
    room_id = "r1111111-1111-1111-1111-111111111111"

    # Logins
    rec_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "recepcion@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert rec_login.status_code == 200
    rec_headers = {"Authorization": f"Bearer {rec_login.json()['access_token']}"}

    doc_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "doctor@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert doc_login.status_code == 200
    doc_headers = {"Authorization": f"Bearer {doc_login.json()['access_token']}"}

    pat_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert pat_login.status_code == 200
    pat_headers = {"Authorization": f"Bearer {pat_login.json()['access_token']}"}

    # 1. Crear una cita en horario hábil diurno (14:00) en fecha futura única
    base_date = datetime.date.today() + datetime.timedelta(days=300 + random.randint(1, 5000))
    start_dt = datetime.datetime.combine(base_date, datetime.time(14, 0))
    end_dt = datetime.datetime.combine(base_date, datetime.time(14, 30))

    create_resp = await client.post(
        "/api/v1/appointments",
        json={
            "clinic_id": clinic_id,
            "doctor_id": doctor_id,
            "room_id": room_id,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "reason": "Control de rutina y chequeo",
        },
        headers=pat_headers,
    )
    assert create_resp.status_code == 201
    appt = create_resp.json()
    appt_id = appt["id"]
    assert appt["status"] == "CONFIRMED"

    # 2. Check-in por parte de recepción
    checkin_resp = await client.post(f"/api/v1/appointments/{appt_id}/check-in", headers=rec_headers)
    assert checkin_resp.status_code == 200
    assert checkin_resp.json()["status"] == "CHECKED_IN"

    # 3. Inicio de consulta por parte del médico
    start_resp = await client.post(f"/api/v1/appointments/{appt_id}/start-consultation", headers=doc_headers)
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "IN_CONSULTATION"


@pytest.mark.anyio
async def test_appointment_reschedule_and_cancellation_2h_rule(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"
    doctor_id = "u2222222-2222-2222-2222-222222222222"
    room_id = "r1111111-1111-1111-1111-111111111111"

    pat_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    pat_headers = {"Authorization": f"Bearer {pat_login.json()['access_token']}"}

    # 1. Crear cita a fecha futura en horario hábil (10:00)
    base_date = datetime.date.today() + datetime.timedelta(days=600 + random.randint(1, 5000))
    start_dt = datetime.datetime.combine(base_date, datetime.time(10, 0))
    end_dt = datetime.datetime.combine(base_date, datetime.time(10, 30))

    create_resp = await client.post(
        "/api/v1/appointments",
        json={
            "clinic_id": clinic_id,
            "doctor_id": doctor_id,
            "room_id": room_id,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "reason": "Cita para reprogramar",
        },
        headers=pat_headers,
    )
    assert create_resp.status_code == 201
    appt_id = create_resp.json()["id"]

    # 2. Reprogramar a las 15:00 del mismo día
    resched_start = datetime.datetime.combine(base_date, datetime.time(15, 0))
    resched_resp = await client.post(
        f"/api/v1/appointments/{appt_id}/reschedule",
        json={
            "new_start_time": resched_start.isoformat(),
            "reason": "Cambio por viaje de trabajo",
        },
        headers=pat_headers,
    )
    assert resched_resp.status_code == 200
    resched_data = resched_resp.json()
    assert resched_data["status"] == "RESCHEDULED"

    # 3. Probar regla de cancelación < 2h:
    # Modificar fecha de inicio de la cita directamente a dentro de 45 minutos
    soon_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=45)
    async with AsyncSessionLocal() as session:
        from app.models.appointment import Appointment

        db_appt = (await session.execute(select(Appointment).where(Appointment.id == appt_id))).scalar_one()
        db_appt.start_time = soon_time
        await session.commit()

    # Intentar cancelar por el paciente debe ser rechazado con 400 por la regla de 2 horas
    bad_cancel = await client.post(
        f"/api/v1/appointments/{appt_id}/cancel",
        json={"cancellation_reason": "No podré asistir a última hora"},
        headers=pat_headers,
    )
    assert bad_cancel.status_code == 400
    assert "2 horas" in bad_cancel.json()["detail"]


@pytest.mark.anyio
async def test_no_show_fair_use_restriction(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"
    doctor_id = "u2222222-2222-2222-2222-222222222222"
    room_id = "r1111111-1111-1111-1111-111111111111"

    rec_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "recepcion@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    rec_headers = {"Authorization": f"Bearer {rec_login.json()['access_token']}"}

    # Crear un paciente de prueba específico para probar strikes de no-show
    pat_email = f"noshow_test_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncSessionLocal() as session:
        from app.core.security import hash_password

        test_pat = User(
            email=pat_email,
            full_name="Paciente Falton",
            hashed_password=hash_password("Password123!"),
            role="PATIENT",
            status="ACTIVE",
            no_show_strikes=0,
            is_restricted_booking=False,
        )
        session.add(test_pat)
        await session.commit()
        pat_id = test_pat.id

    pat_login = await client.post(
        "/api/v1/auth/login",
        data={"username": pat_email, "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    pat_headers = {"Authorization": f"Bearer {pat_login.json()['access_token']}"}

    # Strike 1: Crear cita en horario hábil (11:00) y marcar NO_SHOW
    b_date1 = datetime.date.today() + datetime.timedelta(days=1000 + random.randint(1, 2000))
    s1 = datetime.datetime.combine(b_date1, datetime.time(11, 0))
    e1 = datetime.datetime.combine(b_date1, datetime.time(11, 30))
    c1 = await client.post(
        "/api/v1/appointments",
        json={
            "clinic_id": clinic_id,
            "doctor_id": doctor_id,
            "room_id": room_id,
            "start_time": s1.isoformat(),
            "end_time": e1.isoformat(),
        },
        headers=pat_headers,
    )
    assert c1.status_code == 201
    appt1_id = c1.json()["id"]

    ns1 = await client.post(f"/api/v1/appointments/{appt1_id}/no-show", json={"reason": "Inasistencia 1"}, headers=rec_headers)
    assert ns1.status_code == 200
    assert ns1.json()["status"] == "NO_SHOW"

    # Strike 2: Crear segunda cita en horario hábil y marcar NO_SHOW -> Bloqueo fair use
    b_date2 = datetime.date.today() + datetime.timedelta(days=1000 + random.randint(2001, 4000))
    s2 = datetime.datetime.combine(b_date2, datetime.time(12, 0))
    e2 = datetime.datetime.combine(b_date2, datetime.time(12, 30))
    c2 = await client.post(
        "/api/v1/appointments",
        json={
            "clinic_id": clinic_id,
            "doctor_id": doctor_id,
            "room_id": room_id,
            "start_time": s2.isoformat(),
            "end_time": e2.isoformat(),
        },
        headers=pat_headers,
    )
    assert c2.status_code == 201
    appt2_id = c2.json()["id"]

    ns2 = await client.post(f"/api/v1/appointments/{appt2_id}/no-show", json={"reason": "Inasistencia 2"}, headers=rec_headers)
    assert ns2.status_code == 200
    assert ns2.json()["status"] == "NO_SHOW"

    # Comprobar que en DB el paciente ahora tiene 2 strikes y restricción activa
    async with AsyncSessionLocal() as session:
        u = (await session.execute(select(User).where(User.id == pat_id))).scalar_one()
        assert u.no_show_strikes >= 2
        assert u.is_restricted_booking is True

    # El paciente intenta agendar una tercera cita en línea -> Debe ser rechazado con 403 Forbidden
    b_date3 = datetime.date.today() + datetime.timedelta(days=1000 + random.randint(4001, 6000))
    s3 = datetime.datetime.combine(b_date3, datetime.time(16, 0))
    e3 = datetime.datetime.combine(b_date3, datetime.time(16, 30))
    blocked_create = await client.post(
        "/api/v1/appointments",
        json={
            "clinic_id": clinic_id,
            "doctor_id": doctor_id,
            "room_id": room_id,
            "start_time": s3.isoformat(),
            "end_time": e3.isoformat(),
        },
        headers=pat_headers,
    )
    assert blocked_create.status_code == 403
    assert "no-show" in blocked_create.json()["detail"].lower()
