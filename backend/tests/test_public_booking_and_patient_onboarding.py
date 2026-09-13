"""Pruebas para el agendamiento público con triage biométrico y activación de paciente en VitaRecord."""

import datetime
from decimal import Decimal
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, create_patient_invitation_token


@pytest.mark.asyncio
async def test_public_booking_creates_appointment_with_triage_intake(client: AsyncClient):
    """Verifica que un visitante sin sesión pueda reservar una cita con medidas biométricas y triage."""
    # 1. Obtener un médico y clínica desde el directorio público
    dir_resp = await client.get("/api/v1/doctors/public-directory")
    assert dir_resp.status_code == 200
    doctors = dir_resp.json()
    assert len(doctors) >= 1
    doctor = doctors[0]
    doctor_id = doctor["id"]
    clinic_id = doctor["clinics"][0]["id"]

    # 2. Fecha futura dinámica para evitar solapamientos
    import random
    delta_days = 300 + random.randint(1, 20000)
    start_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=delta_days, hours=10)
    end_dt = start_dt + datetime.timedelta(minutes=30)

    unique_email = f"paciente_nuevo_{int(datetime.datetime.now().timestamp())}_{random.randint(100, 999)}@gmail.com"

    payload = {
        "clinic_id": clinic_id,
        "doctor_id": doctor_id,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "full_name": "María González López",
        "email": unique_email,
        "phone": "+584129876543",
        "id_document": "V-20123456",
        "birth_date": "1994-08-20",
        "gender": "Femenino",
        "country": "Venezuela",
        "city": "Caracas",
        "address": "Av. Francisco de Miranda, Edif. Parque Cristal, Piso 8",
        "height_cm": 165.0,
        "weight_kg": 62.0,
        "blood_type": "O+",
        "allergies": "Penicilina y AINES",
        "chronic_conditions": "Rinitis alérgica",
        "current_medications": "Loratadina 10mg ocasional",
        "reason": "Consulta ginecológica preventiva anual y citología",
    }

    resp = await client.post("/api/v1/appointments/public-book", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["status"] == "PENDING_DOCTOR_APPROVAL"
    assert data["clinic_id"] == clinic_id
    assert data["doctor_id"] == doctor_id
    assert data["reason"] == "Consulta ginecológica preventiva anual y citología"
    assert data["patient_email"] == unique_email

    # Verificar datos de triage e IMC calculado
    intake = data.get("intake_data")
    assert intake is not None
    assert intake["height_cm"] == 165.0
    assert intake["weight_kg"] == 62.0
    assert intake["allergies"] == "Penicilina y AINES"
    assert intake["blood_type"] == "O+"
    assert intake["bmi"] == pytest.approx(22.77, 0.05)
    assert intake["bmi_category"] == "Peso normal"


@pytest.mark.asyncio
async def test_public_booking_prevents_double_booking_conflict(client: AsyncClient):
    """Verifica que la exclusión mutua rechace con 409 una reserva concurrente en el mismo slot."""
    dir_resp = await client.get("/api/v1/doctors/public-directory")
    doctor = dir_resp.json()[0]
    doctor_id = doctor["id"]
    clinic_id = doctor["clinics"][0]["id"]

    import random
    delta_days = 400 + random.randint(1, 20000)
    start_dt = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=delta_days)).replace(hour=10, minute=0, second=0, microsecond=0)
    end_dt = start_dt + datetime.timedelta(minutes=30)

    payload = {
        "clinic_id": clinic_id,
        "doctor_id": doctor_id,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "full_name": "Paciente Uno",
        "email": f"paciente_conflict1_{int(datetime.datetime.now().timestamp())}_{random.randint(100, 999)}@test.com",
        "phone": "+584141112233",
        "reason": "Primera cita",
    }

    # Primera reserva -> éxito
    resp1 = await client.post("/api/v1/appointments/public-book", json=payload)
    assert resp1.status_code == 201

    # Segunda reserva para el mismo médico y horario -> 409 Conflict
    payload["email"] = f"paciente_conflict2_{int(datetime.datetime.now().timestamp())}_{random.randint(100, 999)}@test.com"
    payload["full_name"] = "Paciente Dos"
    resp2 = await client.post("/api/v1/appointments/public-book", json=payload)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_doctor_accept_appointment_and_patient_onboarding(client: AsyncClient):
    """Verifica que el médico apruebe la cita, se genere el token y el paciente complete su onboarding."""
    # 1. Crear cita pública
    dir_resp = await client.get("/api/v1/doctors/public-directory")
    doctor = dir_resp.json()[0]
    doctor_id = doctor["id"]
    clinic_id = doctor["clinics"][0]["id"]

    import random
    delta_days = 500 + random.randint(1, 20000)
    start_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=delta_days, hours=9)
    end_dt = start_dt + datetime.timedelta(minutes=30)
    email = f"paciente_flujo_completo_{int(datetime.datetime.now().timestamp())}_{random.randint(100, 999)}@test.com"

    book_resp = await client.post(
        "/api/v1/appointments/public-book",
        json={
            "clinic_id": clinic_id,
            "doctor_id": doctor_id,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "full_name": "Valeria Rojas",
            "email": email,
            "phone": "+584245556677",
            "height_cm": 170.0,
            "weight_kg": 65.0,
            "reason": "Revisión ginecológica",
        },
    )
    assert book_resp.status_code == 201
    app_data = book_resp.json()
    appointment_id = app_data["id"]
    patient_id = app_data["patient_id"]
    assert app_data["status"] == "PENDING_DOCTOR_APPROVAL"

    # 2. El médico se autentica y acepta la cita
    doctor_token = create_access_token(
        subject=doctor_id,
        clinic_id=clinic_id,
        role="DOCTOR",
        email=doctor["email"],
    )

    accept_resp = await client.post(
        f"/api/v1/appointments/{appointment_id}/doctor-accept",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert accept_resp.status_code == 200
    accepted_app = accept_resp.json()
    assert accepted_app["status"] == "CONFIRMED"

    # 3. El paciente recibe su token de invitación y valida el enlace
    token = create_patient_invitation_token(
        subject=patient_id,
        clinic_id=clinic_id,
        appointment_id=appointment_id,
    )

    val_resp = await client.get(f"/api/v1/auth/patient-onboarding/validate?token={token}")
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["valid"] is True
    assert val_data["email"] == email
    assert val_data["full_name"] == "Valeria Rojas"

    # 4. El paciente establece su contraseña y completa el onboarding
    comp_resp = await client.post(
        "/api/v1/auth/patient-onboarding/complete",
        json={
            "token": token,
            "password": "PasswordPacienteSeguro123!",
        },
    )
    assert comp_resp.status_code == 200
    tokens = comp_resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # 5. El paciente puede identificarse y consultar su perfil y citas
    patient_access_token = tokens["access_token"]
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {patient_access_token}"},
    )
    assert me_resp.status_code == 200
    user_data = me_resp.json()
    assert user_data["email"] == email
    assert user_data["role"] == "PATIENT"
    assert user_data["status"] == "ACTIVE"
