import io
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_patient_profile_management_and_appointment_auto_merge(client: AsyncClient):
    # 1. Login como Paciente
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Consultar perfil inicial
    get_resp = await client.get("/api/v1/patients/me/profile", headers=headers)
    assert get_resp.status_code == 200
    initial_profile = get_resp.json()
    assert initial_profile["email"] == "paciente@intimasalud.com"

    # 3. Actualizar perfil clínico permanente y contacto de emergencia
    update_payload = {
        "full_name": "Paciente Ana Pérez",
        "identification_number": "V-19876543",
        "phone": "+584129876543",
        "birth_date": "1995-05-15",
        "gender": "Femenino",
        "city": "Caracas",
        "blood_type": "O+",
        "height_cm": 165.0,
        "allergies": "Penicilina, Sulfas",
        "chronic_conditions": "Asma estacional",
        "emergency_contact_name": "Carlos Pérez",
        "emergency_contact_phone": "+584141112233",
        "emergency_contact_relationship": "Hermano",
    }
    put_resp = await client.put("/api/v1/patients/me/profile", json=update_payload, headers=headers)
    assert put_resp.status_code == 200
    updated = put_resp.json()
    assert updated["full_name"] == "Paciente Ana Pérez"
    assert updated["identification_number"] == "V-19876543"
    assert updated["blood_type"] == "O+"
    assert updated["height_cm"] == 165.0
    assert updated["allergies"] == "Penicilina, Sulfas"
    assert updated["emergency_contact_name"] == "Carlos Pérez"
    assert updated["is_profile_complete"] is True

    # 4. Subida y obtención de avatar de paciente
    avatar_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    avatar_file = io.BytesIO(avatar_bytes)
    upload_resp = await client.post(
        "/api/v1/patients/me/avatar",
        files={"file": ("profile.png", avatar_file, "image/png")},
        headers=headers,
    )
    assert upload_resp.status_code == 200
    avatar_url = upload_resp.json()["profile_picture_url"]
    assert f"/api/v1/patients/{updated['id']}/avatar" in avatar_url

    # Consultar avatar subido
    get_avatar_resp = await client.get(f"/api/v1/patients/{updated['id']}/avatar")
    assert get_avatar_resp.status_code == 200
    assert get_avatar_resp.headers["content-type"] == "image/png"

    # 5. Agendar cita enviando SOLO peso actual (sin especificar talla ni tipo de sangre)
    # y verificar que la cita consolida automáticamente los datos del perfil
    import datetime
    import random
    clinic_id = "c1111111-1111-1111-1111-111111111111"
    doctor_id = "u2222222-2222-2222-2222-222222222222"
    room_id = "r1111111-1111-1111-1111-111111111111"
    delta = datetime.timedelta(days=random.randint(1000, 20000), hours=10)
    start_dt = datetime.datetime.now(datetime.timezone.utc) + delta
    end_dt = start_dt + datetime.timedelta(minutes=30)

    appointment_payload = {
        "clinic_id": clinic_id,
        "doctor_id": doctor_id,
        "room_id": room_id,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "reason": "Control ginecológico anual",
        "intake_data": {
            "weight_kg": 60.0,
            "current_medications": "Vitaminas",
        },
    }
    app_resp = await client.post("/api/v1/appointments", json=appointment_payload, headers=headers)
    assert app_resp.status_code == 201, f"Error: {app_resp.status_code} - {app_resp.text}"
    app_data = app_resp.json()
    assert app_data["intake_data"]["weight_kg"] == 60.0
    assert app_data["intake_data"]["blood_type"] == "O+"
    assert app_data["intake_data"]["height_cm"] == 165.0
    assert app_data["intake_data"]["allergies"] == "Penicilina, Sulfas"
    assert app_data["intake_data"]["chronic_conditions"] == "Asma estacional"
    # IMC: 60 / (1.65 * 1.65) = 22.04
    assert app_data["intake_data"]["bmi"] == 22.04
    assert app_data["intake_data"]["bmi_category"] == "Peso normal"
