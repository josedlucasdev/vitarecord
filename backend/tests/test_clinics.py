import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_superadmin_can_create_and_list_clinics(client: AsyncClient):
    # 1. Login como SuperAdmin
    admin_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@vitarecord.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Listar clinicas
    list_resp = await client.get("/api/v1/clinics", headers=admin_headers)
    assert list_resp.status_code == 200
    clinics = list_resp.json()
    assert isinstance(clinics, list)

    # 3. Crear nueva clinica (tenant)
    slug = f"clinica-norte-{uuid.uuid4().hex[:6]}"
    create_resp = await client.post(
        "/api/v1/clinics",
        json={
            "name": "Clínica ÍntimaSalud Norte",
            "slug": slug,
            "timezone": "America/Caracas",
            "country_code": "VE",
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["slug"] == slug
    assert data["is_active"] is True

    # Limpieza del tenant temporal de prueba para mantener la base de datos limpia
    from app.core.database import AsyncSessionLocal
    from app.models.clinic import Clinic
    async with AsyncSessionLocal() as db:
        c_obj = await db.get(Clinic, data["id"])
        if c_obj:
            await db.delete(c_obj)
            await db.commit()



@pytest.mark.anyio
async def test_non_superadmin_cannot_create_clinics(client: AsyncClient):
    from app.core.security import create_access_token
    non_admin_token = create_access_token(
        "u7777777-7777-7777-7777-777777777777",
        role="COMPLIANCE_REVIEWER",
        email="moderador@vitarecord.com",
    )
    patient_headers = {"Authorization": f"Bearer {non_admin_token}"}

    # Intento de creacion
    create_resp = await client.post(
        "/api/v1/clinics",
        json={
            "name": "Clínica No Autorizada",
            "slug": "clinica-no-autorizada",
            "timezone": "America/Caracas",
            "country_code": "VE",
        },
        headers=patient_headers,
    )
    assert create_resp.status_code == 403


@pytest.mark.anyio
async def test_clinic_lifecycle_edit_toggle_delete(client: AsyncClient):
    from datetime import datetime, timedelta, timezone
    from app.core.database import AsyncSessionLocal
    from app.core.security import hash_password
    from app.models.appointment import Appointment
    from app.models.clinic import Clinic, ClinicRoom, RoomScheduleLock
    from app.models.user import User

    # 1. Login como SuperAdmin
    admin_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@vitarecord.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Crear clínica con teléfono y dirección
    slug = f"clinica-test-{uuid.uuid4().hex[:6]}"
    create_resp = await client.post(
        "/api/v1/clinics",
        json={
            "name": "Clínica Test Vida",
            "slug": slug,
            "timezone": "America/Caracas",
            "country_code": "VE",
            "phone": "+58 412 1234567",
            "address": "Av. Principal Torre Médica Piso 4",
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    clinic_data = create_resp.json()
    clinic_id = clinic_data["id"]
    assert clinic_data["phone"] == "+58 412 1234567"
    assert clinic_data["address"] == "Av. Principal Torre Médica Piso 4"

    # 3. Editar clínica
    update_resp = await client.put(
        f"/api/v1/clinics/{clinic_id}",
        json={
            "name": "Clínica Test Vida Actualizada",
            "phone": "+58 414 7654321",
        },
        headers=admin_headers,
    )
    assert update_resp.status_code == 200
    updated_clinic = update_resp.json()
    assert updated_clinic["name"] == "Clínica Test Vida Actualizada"
    assert updated_clinic["phone"] == "+58 414 7654321"

    # 4. Crear usuarios de prueba asociados:
    # - Tenant admin
    # - Médico afiliado
    # - Paciente con cita activa
    staff_email = f"staff_{uuid.uuid4().hex[:6]}@test.com"
    doc_email = f"doc_{uuid.uuid4().hex[:6]}@test.com"
    pat_email = f"pat_{uuid.uuid4().hex[:6]}@test.com"

    async with AsyncSessionLocal() as db:
        staff_user = User(
            email=staff_email,
            hashed_password=hash_password("Password123!"),
            full_name="Secretaria Test",
            role="RECEPTIONIST",
            status="ACTIVE",
            clinic_id=clinic_id,
        )
        doc_user = User(
            email=doc_email,
            hashed_password=hash_password("Password123!"),
            full_name="Dr. Test",
            role="DOCTOR",
            status="ACTIVE",
            clinic_id=clinic_id,
        )
        pat_user = User(
            email=pat_email,
            hashed_password=hash_password("Password123!"),
            full_name="Paciente Test",
            role="PATIENT",
            status="ACTIVE",
        )
        db.add_all([staff_user, doc_user, pat_user])
        await db.flush()

        room = ClinicRoom(
            name="Consultorio 101",
            clinic_id=clinic_id,
            is_active=True,
        )
        db.add(room)
        await db.flush()

        lock = RoomScheduleLock(room_id=room.id)
        db.add(lock)

        now = datetime.now(timezone.utc)
        appt = Appointment(
            clinic_id=clinic_id,
            doctor_id=doc_user.id,
            patient_id=pat_user.id,
            room_id=room.id,
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=1),
            status="SCHEDULED",
            reason="Consulta General",
        )
        db.add(appt)
        await db.commit()
        staff_id = staff_user.id
        doc_id = doc_user.id
        pat_id = pat_user.id

    # 5. Inactivar la clínica (toggle-active)
    toggle_resp = await client.patch(
        f"/api/v1/clinics/{clinic_id}/toggle-active",
        headers=admin_headers,
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["is_active"] is False

    # Verificar que el usuario del tenant ya no puede iniciar sesión
    staff_login_fail = await client.post(
        "/api/v1/auth/login",
        data={"username": staff_email, "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert staff_login_fail.status_code == 403

    # Reactivar la clínica
    toggle_resp_2 = await client.patch(
        f"/api/v1/clinics/{clinic_id}/toggle-active",
        headers=admin_headers,
    )
    assert toggle_resp_2.status_code == 200
    assert toggle_resp_2.json()["is_active"] is True

    # Verificar que el usuario del tenant vuelve a poder iniciar sesión
    staff_login_ok = await client.post(
        "/api/v1/auth/login",
        data={"username": staff_email, "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert staff_login_ok.status_code == 200

    # 6. Eliminar la clínica definitivamente
    delete_resp = await client.delete(
        f"/api/v1/clinics/{clinic_id}",
        headers=admin_headers,
    )
    assert delete_resp.status_code == 200
    del_json = delete_resp.json()
    assert del_json["success"] is True
    assert del_json["notified_appointments"] == 1

    # Verificar en base de datos:
    async with AsyncSessionLocal() as db:
        # Clínica eliminada
        assert await db.get(Clinic, clinic_id) is None
        # Usuario staff eliminado
        assert await db.get(User, staff_id) is None
        # Doctor desvinculado (clinic_id = None), no eliminado
        doc_after = await db.get(User, doc_id)
        assert doc_after is not None
        assert doc_after.clinic_id is None
        # Paciente preservado
        pat_after = await db.get(User, pat_id)
        assert pat_after is not None
        # Limpieza de usuarios globales de prueba
        await db.delete(doc_after)
        await db.delete(pat_after)
        await db.commit()

