import pytest
from httpx import AsyncClient
from app.core.redis import get_redis


@pytest.mark.anyio
async def test_doctor_schedule_and_slots_with_redis(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"

    # 1. Login como Doctor verificado
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "doctor@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_resp = await client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    doctor_id = me_resp.json()["id"]

    # 2. Configurar horario semanal (Lunes a Sábado, cada 30 min)
    schedule_payload = {
        "clinic_id": clinic_id,
        "blocks": [
            {
                "day_of_week": 0,
                "start_time": "09:00",
                "end_time": "11:00",
                "slot_duration_minutes": 30,
            }
        ] + [
            {
                "day_of_week": day,
                "start_time": "08:00",
                "end_time": "17:00",
                "slot_duration_minutes": 30,
            }
            for day in range(1, 6)
        ],
    }

    set_resp = await client.post(
        f"/api/v1/doctors/{doctor_id}/schedules",
        json=schedule_payload,
        headers=headers,
    )
    assert set_resp.status_code == 200
    blocks = set_resp.json()
    assert len(blocks) == 6
    assert blocks[0]["day_of_week"] == 0
    assert blocks[0]["start_time"] == "09:00"

    # 3. Consultar horarios configurados
    get_sched_resp = await client.get(
        f"/api/v1/doctors/{doctor_id}/schedules?clinic_id={clinic_id}",
        headers=headers,
    )
    assert get_sched_resp.status_code == 200
    assert len(get_sched_resp.json()) == 6

    # 4. Calcular slots disponibles para un Lunes (2026-09-14 es Lunes)
    target_monday = "2026-09-14"
    slots_resp = await client.get(
        f"/api/v1/clinics/{clinic_id}/doctors/{doctor_id}/slots?date={target_monday}"
    )
    assert slots_resp.status_code == 200
    slots = slots_resp.json()
    # 09:00 a 11:00 con bloques de 30 min son 4 slots: 09:00, 09:30, 10:00, 10:30
    assert len(slots) == 4
    assert slots[0]["start_time"] == "09:00"
    assert slots[0]["end_time"] == "09:30"
    assert slots[3]["start_time"] == "10:30"
    assert slots[3]["end_time"] == "11:00"

    # 5. Verificar que Redis tiene la clave cacheada
    redis = get_redis()
    cache_key = f"slots:{clinic_id}:{doctor_id}:{target_monday}"
    cached_val = await redis.get(cache_key)
    assert cached_val is not None

    # Segunda llamada debe retornar 200 con los mismos 4 slots (desde cache)
    slots_resp2 = await client.get(
        f"/api/v1/clinics/{clinic_id}/doctors/{doctor_id}/slots?date={target_monday}"
    )
    assert slots_resp2.status_code == 200
    assert len(slots_resp2.json()) == 4

    # 6. Para un Domingo (2026-09-13 es Domingo, weekday=6), debe retornar 0 slots
    target_sunday = "2026-09-13"
    sunday_resp = await client.get(
        f"/api/v1/clinics/{clinic_id}/doctors/{doctor_id}/slots?date={target_sunday}"
    )
    assert sunday_resp.status_code == 200
    assert len(sunday_resp.json()) == 0


@pytest.mark.anyio
async def test_doctor_cannot_modify_other_doctor_schedule(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"

    # Login como Doctor
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "doctor@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Intentar modificar el horario de otro doctor ficticio
    other_doctor_id = "d9999999-9999-9999-9999-999999999999"
    resp = await client.post(
        f"/api/v1/doctors/{other_doctor_id}/schedules",
        json={"clinic_id": clinic_id, "blocks": []},
        headers=headers,
    )
    # Debe ser 404 (si no existe) o 403 (si es de otro médico)
    assert resp.status_code in [403, 404]
