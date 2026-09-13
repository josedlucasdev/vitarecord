import datetime
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.affiliation import DoctorClinicAffiliation
from app.models.clinic import Clinic, ClinicRoom, RoomScheduleLock
from app.models.schedule import DoctorWeeklySchedule
from app.models.user import User


@pytest.mark.anyio
async def test_room_specialty_and_cross_clinic_availability(client: AsyncClient):
    """Prueba el requerimiento de dominio estricto:
    
    1. Clínica A cuenta con Consultorio 1 (Ginecología) y Consultorio 2 (Pediatría).
    2. El Dr. X (Ginecólogo) y el Dr. Z (Ginecólogo) atienden en la Clínica A los lunes.
    3. El Dr. Z también atiende en la Clínica T (que tiene consultorio de Ginecología libre).
    4. Si se reserva una cita para el Dr. X a las 08:00 AM en Clínica A, el Consultorio 1 se ocupa.
    5. La consulta de disponibilidad del Dr. Z para ese mismo horario a las 08:00 AM en Clínica A
       debe mostrar is_available = False (porque el único consultorio compatible está ocupado por el Dr. X).
    6. Sin embargo, en la Clínica T, el Dr. Z a las 08:00 AM sí tiene consultorio disponible (is_available = True).
    7. Si el consultorio de Ginecología se coloca en MAINTENANCE, no admite citas.
    """
    clinic_a_id = "c-test-clinic-a-000000000001"
    clinic_t_id = "c-test-clinic-t-000000000002"
    doc_x_id = "u-test-doctor-x-000000000001"
    doc_z_id = "u-test-doctor-z-000000000002"
    patient_id = "u-test-patient-000000000001"
    room_a_gyn_id = "r-test-room-a-gyn-00000001"
    room_a_ped_id = "r-test-room-a-ped-00000002"
    room_t_gyn_id = "r-test-room-t-gyn-00000003"

    async with AsyncSessionLocal() as session:
        from app.models.appointment import Appointment
        from sqlalchemy import delete

        # Limpiar citas previas del test para garantizar idempotencia
        await session.execute(
            delete(Appointment).where(
                Appointment.doctor_id.in_([doc_x_id, doc_z_id])
            )
        )
        await session.commit()

        # 1. Crear Clínicas
        for cid, name, slug in [
            (clinic_a_id, "Clínica A", "clinica-a-test"),
            (clinic_t_id, "Clínica T", "clinica-t-test"),
        ]:
            c = await session.get(Clinic, cid)
            if not c:
                session.add(Clinic(id=cid, name=name, slug=slug, timezone="America/Caracas", country_code="VE", is_active=True))

        # 2. Crear Consultorios
        # Clínica A: Room 1 (Ginecología), Room 2 (Pediatría)
        for rid, cid, rname, rnum, rspec, rstatus in [
            (room_a_gyn_id, clinic_a_id, "Consultorio 1 - Ginecología", "101", "Ginecología & Obstetricia", "ACTIVE"),
            (room_a_ped_id, clinic_a_id, "Consultorio 2 - Pediatría", "201", "Pediatría", "ACTIVE"),
            (room_t_gyn_id, clinic_t_id, "Consultorio 1 - Ginecología T", "101-T", "Ginecología & Obstetricia", "ACTIVE"),
        ]:
            r = await session.get(ClinicRoom, rid)
            if not r:
                session.add(ClinicRoom(
                    id=rid,
                    clinic_id=cid,
                    name=rname,
                    room_number=rnum,
                    specialty=rspec,
                    status=rstatus,
                    operating_hours={"start": "07:00", "end": "19:00"},
                    is_active=True,
                ))
            else:
                r.specialty = rspec
                r.status = rstatus
                r.operating_hours = {"start": "07:00", "end": "19:00"}
                r.is_active = True

            # Cerrojos mutex
            lock = await session.get(RoomScheduleLock, rid)
            if not lock:
                session.add(RoomScheduleLock(room_id=rid))

        # 3. Crear Médicos (Dr. X y Dr. Z, ambos ginecólogos verificados)
        pwd = hash_password("Password123!")
        for uid, email, name, spec in [
            (doc_x_id, "doctor.x@test.com", "Dr. X Ginecólogo", "Ginecología & Obstetricia"),
            (doc_z_id, "doctor.z@test.com", "Dr. Z Ginecólogo", "Ginecología & Obstetricia"),
        ]:
            u = await session.get(User, uid)
            if not u:
                session.add(User(
                    id=uid,
                    email=email,
                    hashed_password=pwd,
                    full_name=name,
                    role="DOCTOR",
                    status="ACTIVE",
                    specialty=spec,
                    license_number="LIC-12345",
                    license_verification_status="VERIFIED",
                    mfa_enabled=False,
                ))

        # Crear Paciente
        p = await session.get(User, patient_id)
        if not p:
            session.add(User(
                id=patient_id,
                email="patient.test@test.com",
                hashed_password=pwd,
                full_name="Paciente Prueba",
                role="PATIENT",
                status="ACTIVE",
                mfa_enabled=False,
            ))

        # Afiliaciones
        for doc_id, c_id in [
            (doc_x_id, clinic_a_id),
            (doc_z_id, clinic_a_id),
            (doc_z_id, clinic_t_id),
        ]:
            stmt_af = select(DoctorClinicAffiliation).where(
                DoctorClinicAffiliation.doctor_id == doc_id,
                DoctorClinicAffiliation.clinic_id == c_id,
            )
            af = (await session.execute(stmt_af)).scalar_one_or_none()
            if not af:
                session.add(DoctorClinicAffiliation(doctor_id=doc_id, clinic_id=c_id, status="ACTIVE"))

        # Horarios semanales de los médicos (Lunes a las 08:00 a 10:00, slot de 30 min)
        # 0 = Lunes
        for doc_id, c_id in [
            (doc_x_id, clinic_a_id),
            (doc_z_id, clinic_a_id),
            (doc_z_id, clinic_t_id),
        ]:
            stmt_sc = select(DoctorWeeklySchedule).where(
                DoctorWeeklySchedule.doctor_id == doc_id,
                DoctorWeeklySchedule.clinic_id == c_id,
                DoctorWeeklySchedule.day_of_week == 0,
            )
            sc = (await session.execute(stmt_sc)).scalar_one_or_none()
            if not sc:
                session.add(DoctorWeeklySchedule(
                    doctor_id=doc_id,
                    clinic_id=c_id,
                    day_of_week=0,
                    start_time=datetime.time(8, 0),
                    end_time=datetime.time(10, 0),
                    slot_duration_minutes=30,
                    is_active=True,
                ))

        await session.commit()

    # Login paciente
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "patient.test@test.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    patient_headers = {"Authorization": f"Bearer {token}"}

    # Fecha objetivo: un lunes futuro fijo (2027-01-04 es Lunes)
    target_monday = "2027-01-04"

    from app.core.redis import get_redis
    r = get_redis()
    await r.delete(f"slots:{clinic_a_id}:{doc_x_id}:{target_monday}")
    await r.delete(f"slots:{clinic_a_id}:{doc_z_id}:{target_monday}")
    await r.delete(f"slots:{clinic_t_id}:{doc_z_id}:{target_monday}")

    # PASO A: Antes de cualquier reserva, el Dr. X y el Dr. Z tienen slots libres a las 08:00 AM en Clínica A
    slots_x = (await client.get(f"/api/v1/clinics/{clinic_a_id}/doctors/{doc_x_id}/slots?date={target_monday}")).json()
    assert any(s["start_time"] == "08:00" and s["is_available"] is True for s in slots_x)

    slots_z = (await client.get(f"/api/v1/clinics/{clinic_a_id}/doctors/{doc_z_id}/slots?date={target_monday}")).json()
    assert any(s["start_time"] == "08:00" and s["is_available"] is True for s in slots_z)

    # PASO B: El Dr. X toma una cita en Clínica A a las 08:00 AM (ocupa Consultorio 1)
    book_resp = await client.post(
        "/api/v1/appointments",
        json={
            "clinic_id": clinic_a_id,
            "doctor_id": doc_x_id,
            "start_time": f"{target_monday}T08:00:00",
            "end_time": f"{target_monday}T08:30:00",
            "reason": "Control Ginecológico con Dr. X",
            "estimated_amount": 40.0,
            "currency": "USD",
        },
        headers=patient_headers,
    )
    assert book_resp.status_code == 201
    booked_app = book_resp.json()
    # El sistema debe haber auto-asignado el consultorio de ginecología (room_a_gyn_id)
    assert booked_app["room_id"] == room_a_gyn_id

    # PASO C: Consultar disponibilidad del Dr. Z a las 08:00 AM en Clínica A
    # AUNQUE el Dr. Z no tiene citas a las 08:00 AM, el Consultorio 1 está ocupado por el Dr. X,
    # y el Consultorio 2 es de Pediatría (no compatible con Ginecología).
    # Por lo tanto, el slot de las 08:00 AM para el Dr. Z en Clínica A DEBE figurar is_available = False!
    slots_z_after = (await client.get(f"/api/v1/clinics/{clinic_a_id}/doctors/{doc_z_id}/slots?date={target_monday}")).json()
    slot_0800_clinic_a = next(s for s in slots_z_after if s["start_time"] == "08:00")
    assert slot_0800_clinic_a["is_available"] is False, "El slot de las 08:00 AM debe estar ocupado por falta de consultorio compatible!"

    # Los siguientes slots donde el Consultorio 1 está libre (ej. 08:30) sí deben estar disponibles
    slot_0830_clinic_a = next(s for s in slots_z_after if s["start_time"] == "08:30")
    assert slot_0830_clinic_a["is_available"] is True

    # PASO D: Consultar disponibilidad del Dr. Z a las 08:00 AM en Clínica T
    # En Clínica T, el consultorio de Ginecología está libre a las 08:00 AM.
    # Por lo tanto, el Dr. Z en Clínica T a las 08:00 AM DEBE permitir agendar (is_available = True)!
    slots_z_clinic_t = (await client.get(f"/api/v1/clinics/{clinic_t_id}/doctors/{doc_z_id}/slots?date={target_monday}")).json()
    slot_0800_clinic_t = next(s for s in slots_z_clinic_t if s["start_time"] == "08:00")
    assert slot_0800_clinic_t["is_available"] is True, "En Clínica T el consultorio de Ginecología está libre, debe permitir cita!"

    # PASO E: Si un paciente intenta forzar la reserva con el Dr. Z a las 08:00 AM en Clínica A, debe rebotar con 409 Conflict
    conflict_booking = await client.post(
        "/api/v1/appointments",
        json={
            "clinic_id": clinic_a_id,
            "doctor_id": doc_z_id,
            "start_time": f"{target_monday}T08:00:00",
            "end_time": f"{target_monday}T08:30:00",
            "reason": "Intento de agendar sin consultorio libre",
            "estimated_amount": 40.0,
            "currency": "USD",
        },
        headers=patient_headers,
    )
    assert conflict_booking.status_code == 409

    # PASO F: Cancelar la cita del Dr. X libera de inmediato el Consultorio 1
    cancel_resp = await client.post(
        f"/api/v1/appointments/{booked_app['id']}/cancel",
        json={"cancellation_reason": "Cancelación por el paciente"},
        headers=patient_headers,
    )
    assert cancel_resp.status_code == 200

    # Ahora el slot de las 08:00 AM en Clínica A vuelve a estar libre para el Dr. Z
    slots_z_restored = (await client.get(f"/api/v1/clinics/{clinic_a_id}/doctors/{doc_z_id}/slots?date={target_monday}")).json()
    slot_0800_restored = next(s for s in slots_z_restored if s["start_time"] == "08:00")
    assert slot_0800_restored["is_available"] is True, "Al cancelarse la cita, el consultorio y el slot vuelven a estar libres!"

    # PASO G: Si el Consultorio 1 pasa a estado MAINTENANCE, no admite citas de ginecología
    async with AsyncSessionLocal() as session:
        rm = await session.get(ClinicRoom, room_a_gyn_id)
        rm.status = "MAINTENANCE"
        await session.commit()

    await r.delete(f"slots:{clinic_a_id}:{doc_z_id}:{target_monday}")

    slots_maint = (await client.get(f"/api/v1/clinics/{clinic_a_id}/doctors/{doc_z_id}/slots?date={target_monday}")).json()
    assert all(s["is_available"] is False for s in slots_maint), "Con consultorio en mantenimiento, todos los slots deben estar bloqueados!"
