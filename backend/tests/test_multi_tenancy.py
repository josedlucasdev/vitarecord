"""Aislamiento multi-tenant (plan/plan.md seccion 2.B.1, Principio Operativo 3).

Cubre:
- La cabecera X-Clinic-ID no puede usarse para saltar a otra clinica.
- El personal de sede queda filtrado a su clinica aunque no envie cabecera.
- El filtro ORM se aplica a los modelos TenantScoped y se puede omitir solo
  con `cross_tenant()` (consultas inter-clinica justificadas).
- Un medico no puede quedar doble-reservado en dos clinicas distintas aunque
  quien agenda sea personal de una sola sede (con el filtro de tenant activo).
- Una cita no es legible por otro paciente (IDOR).
"""

import datetime
import random

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal, engine
from app.core.tenant import cross_tenant, reset_tenant_context, set_tenant_context
from app.models.clinic import ClinicRoom

CLINIC_1 = "c1111111-1111-1111-1111-111111111111"
CLINIC_2 = "c2222222-2222-2222-2222-222222222222"
CLINIC_3 = "c3333333-3333-3333-3333-333333333333"
DOCTOR_ID = "u2222222-2222-2222-2222-222222222222"  # afiliado a clinicas 1, 2 y 5
PATIENT_ID = "u4444444-4444-4444-4444-444444444444"


async def _login(client: AsyncClient, email: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.anyio
async def test_staff_cannot_spoof_other_clinic_header(client: AsyncClient):
    headers = await _login(client, "recepcion@intimasalud.com")

    spoofed = await client.get("/api/v1/appointments", headers={**headers, "X-Clinic-ID": CLINIC_2})
    assert spoofed.status_code == 403

    own = await client.get("/api/v1/appointments", headers={**headers, "X-Clinic-ID": CLINIC_1})
    assert own.status_code == 200
    assert all(a["clinic_id"] == CLINIC_1 for a in own.json())


@pytest.mark.anyio
async def test_staff_is_scoped_to_own_clinic_without_header(client: AsyncClient):
    headers = await _login(client, "recepcion@intimasalud.com")

    own_rooms = await client.get(f"/api/v1/clinics/{CLINIC_1}/rooms", headers=headers)
    assert own_rooms.status_code == 200
    assert len(own_rooms.json()) > 0

    # Sin cabecera, el filtro ORM igual limita al personal a su propia clinica.
    other_rooms = await client.get(f"/api/v1/clinics/{CLINIC_2}/rooms", headers=headers)
    assert other_rooms.status_code in (200, 403)
    if other_rooms.status_code == 200:
        assert other_rooms.json() == []

    appts = await client.get("/api/v1/appointments", params={"clinic_id": CLINIC_2}, headers=headers)
    assert appts.status_code == 200
    assert all(a["clinic_id"] == CLINIC_1 for a in appts.json())


@pytest.mark.anyio
async def test_doctor_header_requires_active_affiliation(client: AsyncClient):
    headers = await _login(client, "doctor@intimasalud.com")

    not_affiliated = await client.get("/api/v1/appointments", headers={**headers, "X-Clinic-ID": CLINIC_3})
    assert not_affiliated.status_code == 403

    affiliated = await client.get("/api/v1/appointments", headers={**headers, "X-Clinic-ID": CLINIC_1})
    assert affiliated.status_code == 200


@pytest.mark.anyio
async def test_orm_filter_and_explicit_cross_tenant_bypass():
    try:
        set_tenant_context(clinic_id=CLINIC_1, role="RECEPTIONIST")
        async with AsyncSessionLocal() as session:
            scoped = (await session.execute(select(ClinicRoom))).scalars().all()
            assert scoped, "La semilla debe tener consultorios en la clinica 1"
            assert {r.clinic_id for r in scoped} == {CLINIC_1}

            bypass = (await session.execute(cross_tenant(select(ClinicRoom)))).scalars().all()
            assert len({r.clinic_id for r in bypass}) > 1

        set_tenant_context(clinic_id=CLINIC_1, role="SUPERADMIN")
        async with AsyncSessionLocal() as session:
            global_view = (await session.execute(select(ClinicRoom))).scalars().all()
            assert len({r.clinic_id for r in global_view}) > 1
    finally:
        reset_tenant_context()
        # Este test no usa el fixture `client` (que libera el pool): evitar que
        # conexiones ligadas a este event loop se reutilicen en el siguiente test.
        await engine.dispose()


def _future_slot() -> tuple[datetime.datetime, datetime.datetime]:
    days = 400 + random.randint(1, 20000)
    base = datetime.datetime.now(datetime.timezone.utc).replace(hour=14, minute=0, second=0, microsecond=0)
    start = base + datetime.timedelta(days=days)
    return start, start + datetime.timedelta(minutes=30)


@pytest.mark.anyio
async def test_doctor_cannot_be_double_booked_across_clinics_by_scoped_staff(client: AsyncClient):
    patient_headers = await _login(client, "paciente@intimasalud.com")
    reception_headers = await _login(client, "recepcion@intimasalud.com")  # clinica 1

    start, end = _future_slot()

    # 1. El paciente reserva al medico en la CLINICA 2.
    first = await client.post(
        "/api/v1/appointments",
        json={
            "clinic_id": CLINIC_2,
            "doctor_id": DOCTOR_ID,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "reason": "Reserva en clinica 2",
        },
        headers=patient_headers,
    )
    assert first.status_code == 201, first.text

    # 2. Recepcion de la CLINICA 1 (filtro de tenant activo) intenta el mismo
    #    horario para el mismo medico: debe ver el conflicto de la otra clinica.
    second = await client.post(
        "/api/v1/appointments",
        json={
            "clinic_id": CLINIC_1,
            "doctor_id": DOCTOR_ID,
            "patient_id": PATIENT_ID,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "reason": "Intento de doble reserva inter-clinica",
        },
        headers=reception_headers,
    )
    assert second.status_code == 409, second.text


@pytest.mark.anyio
async def test_staff_cannot_book_in_other_clinic(client: AsyncClient):
    reception_headers = await _login(client, "recepcion@intimasalud.com")  # clinica 1
    start, end = _future_slot()
    resp = await client.post(
        "/api/v1/appointments",
        json={
            "clinic_id": CLINIC_2,
            "doctor_id": DOCTOR_ID,
            "patient_id": PATIENT_ID,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=reception_headers,
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_appointment_is_not_readable_by_other_patient_or_other_clinic(client: AsyncClient):
    patient_headers = await _login(client, "paciente@intimasalud.com")
    start, end = _future_slot()
    booked = await client.post(
        "/api/v1/appointments",
        json={
            "clinic_id": CLINIC_2,
            "doctor_id": DOCTOR_ID,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=patient_headers,
    )
    assert booked.status_code == 201, booked.text
    appointment_id = booked.json()["id"]

    # El propio paciente si puede verla.
    own = await client.get(f"/api/v1/appointments/{appointment_id}", headers=patient_headers)
    assert own.status_code == 200

    # Otro paciente (registrado al vuelo con login social emulado) no.
    other = await client.post(
        "/api/v1/auth/google", json={"credential": f"dev_google_{random.randint(10**8, 10**9)}"}
    )
    assert other.status_code == 200, other.text
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    resp = await client.get(f"/api/v1/appointments/{appointment_id}", headers=other_headers)
    assert resp.status_code == 404

    # Recepcion de la clinica 1 tampoco (la cita es de la clinica 2).
    reception_headers = await _login(client, "recepcion@intimasalud.com")
    resp = await client.get(f"/api/v1/appointments/{appointment_id}", headers=reception_headers)
    assert resp.status_code == 404
