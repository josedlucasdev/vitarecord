import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.clinic import RoomScheduleLock


@pytest.mark.anyio
async def test_clinic_rooms_crud_and_mutex_lock(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"

    # 1. Login como Clinic Admin
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "clinic.admin@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Crear consultorio fisico
    create_resp = await client.post(
        f"/api/v1/clinics/{clinic_id}/rooms",
        json={
            "name": "Consultorio 2 - Ecografía 4D",
            "room_number": "102",
            "description": "Equipado con ecógrafo de alta definición",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    room_data = create_resp.json()
    room_id = room_data["id"]
    assert room_data["room_number"] == "102"
    assert room_data["is_active"] is True

    # 3. Comprobar que la fila mutex se creo automaticamente en room_schedule_locks
    async with AsyncSessionLocal() as session:
        stmt = select(RoomScheduleLock).where(RoomScheduleLock.room_id == room_id)
        res = await session.execute(stmt)
        lock_row = res.scalar_one_or_none()
        assert lock_row is not None
        assert lock_row.room_id == room_id

    # 4. Actualizar consultorio
    update_resp = await client.put(
        f"/api/v1/clinics/{clinic_id}/rooms/{room_id}",
        json={"name": "Consultorio 2 - Ecografía Avanzada"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Consultorio 2 - Ecografía Avanzada"

    # 5. Listar consultorios activos
    list_resp = await client.get(f"/api/v1/clinics/{clinic_id}/rooms", headers=headers)
    assert list_resp.status_code == 200
    rooms = list_resp.json()
    assert any(r["id"] == room_id for r in rooms)

    # 6. Desactivar consultorio
    del_resp = await client.delete(f"/api/v1/clinics/{clinic_id}/rooms/{room_id}", headers=headers)
    assert del_resp.status_code == 204

    # 7. Listar de nuevo: ya no debe aparecer en activos
    list_after = await client.get(f"/api/v1/clinics/{clinic_id}/rooms", headers=headers)
    assert not any(r["id"] == room_id for r in list_after.json())
