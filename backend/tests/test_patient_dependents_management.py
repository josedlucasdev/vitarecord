import datetime
import io
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_patient_dependents_management(client: AsyncClient):
    # 1. Login como Paciente
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Registrar nuevo familiar con ficha clínica completa
    today = datetime.date.today()
    minor_birth = datetime.date(today.year - 7, today.month, today.day)
    create_payload = {
        "full_name": "Lucas Pérez",
        "relationship": "HIJO",
        "birth_date": minor_birth.isoformat(),
        "id_document": "V-33112233",
        "gender": "Masculino",
        "blood_type": "O+",
        "height_cm": 122.5,
        "allergies": "Amoxicilina",
        "chronic_conditions": "Rinitis alérgica",
        "phone": "+584120001122",
        "notes": "Alérgico a picaduras de abejas",
    }
    post_resp = await client.post("/api/v1/patients/me/dependents", json=create_payload, headers=headers)
    assert post_resp.status_code == 201
    dep_data = post_resp.json()
    dep_id = dep_data["id"]
    assert dep_data["full_name"] == "Lucas Pérez"
    assert dep_data["relationship"] == "HIJO"
    assert dep_data["blood_type"] == "O+"
    assert dep_data["height_cm"] == 122.5
    assert dep_data["allergies"] == "Amoxicilina"
    assert dep_data["is_profile_complete"] is True
    assert dep_data["age"] == 7

    # 3. Consultar detalle del familiar
    get_resp = await client.get(f"/api/v1/patients/me/dependents/{dep_id}", headers=headers)
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["notes"] == "Alérgico a picaduras de abejas"

    # 4. Actualizar ficha del familiar
    update_payload = {
        "height_cm": 124.0,
        "notes": "Control pediátrico al día",
    }
    put_resp = await client.put(f"/api/v1/patients/me/dependents/{dep_id}", json=update_payload, headers=headers)
    assert put_resp.status_code == 200
    updated = put_resp.json()
    assert updated["height_cm"] == 124.0
    assert updated["notes"] == "Control pediátrico al día"

    # 5. Subida de foto para el familiar
    avatar_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    avatar_file = io.BytesIO(avatar_bytes)
    upload_resp = await client.post(
        f"/api/v1/patients/me/dependents/{dep_id}/avatar",
        files={"file": ("lucas.png", avatar_file, "image/png")},
        headers=headers,
    )
    assert upload_resp.status_code == 200
    assert f"/api/v1/patients/dependents/{dep_id}/avatar" in upload_resp.json()["profile_picture_url"]

    # 6. Eliminar familiar
    del_resp = await client.delete(f"/api/v1/patients/me/dependents/{dep_id}", headers=headers)
    assert del_resp.status_code == 204

    # 7. Verificar que ya no existe
    get_after_del = await client.get(f"/api/v1/patients/me/dependents/{dep_id}", headers=headers)
    assert get_after_del.status_code == 404
