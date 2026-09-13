"""Pruebas del worker de tareas asíncronas y programador de recordatorios (plan/plan.md Módulo 6)."""

import datetime
import pytest
from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.appointment import Appointment
from app.models.notification_log import NotificationLog
from app.tasks.reminders import process_appointment_reminders


@pytest.mark.anyio
async def test_appointment_reminders_worker_and_deduplication(client: AsyncClient):
    """Verifica que el worker de recordatorios detecte citas a 24h y 2h, y prevenga envíos duplicados."""
    clinic_id = "c1111111-1111-1111-1111-111111111111"
    doctor_id = "u2222222-2222-2222-2222-222222222222"
    patient_id = "u3333333-3333-3333-3333-333333333333"
    room_id = "r1111111-1111-1111-1111-111111111111"

    now = datetime.datetime.utcnow()

    # Cita 1: Exactamente dentro de la ventana de 24 horas (ej. 23h 55m en el futuro)
    start_24h = now + datetime.timedelta(hours=23, minutes=55)
    end_24h = start_24h + datetime.timedelta(minutes=30)

    # Cita 2: Exactamente dentro de la ventana de 2 horas (ej. 1h 55m en el futuro)
    start_2h = now + datetime.timedelta(hours=1, minutes=55)
    end_2h = start_2h + datetime.timedelta(minutes=30)

    # Cita 3: Lejana (ej. 96 horas en el futuro, no debe recibir recordatorio hoy)
    start_far = now + datetime.timedelta(hours=96)
    end_far = start_far + datetime.timedelta(minutes=30)

    async with AsyncSessionLocal() as db:
        app_24h = Appointment(
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            patient_id=patient_id,
            room_id=room_id,
            start_time=start_24h,
            end_time=end_24h,
            status="CONFIRMED",
            reason="Control de rutina para recordatorio 24h",
        )
        app_2h = Appointment(
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            patient_id=patient_id,
            room_id=room_id,
            start_time=start_2h,
            end_time=end_2h,
            status="CONFIRMED",
            reason="Control de rutina para recordatorio 2h",
        )
        app_far = Appointment(
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            patient_id=patient_id,
            room_id=room_id,
            start_time=start_far,
            end_time=end_far,
            status="CONFIRMED",
            reason="Control lejano sin recordatorio",
        )
        db.add_all([app_24h, app_2h, app_far])
        await db.commit()
        await db.refresh(app_24h)
        await db.refresh(app_2h)
        await db.refresh(app_far)
        app_24h_id = app_24h.id
        app_2h_id = app_2h.id
        app_far_id = app_far.id

    # 1. Primera ejecución del worker de recordatorios
    result1 = await process_appointment_reminders()
    assert result1["dispatched_24h"] >= 1
    assert result1["dispatched_2h"] >= 1

    # Comprobar que en notification_logs existen los registros con sus etapas correspondientes
    async with AsyncSessionLocal() as db:
        from app.repositories.notification_repository import NotificationRepository
        repo = NotificationRepository(db)

        has_24h = await repo.has_reminder_been_sent(app_24h_id, "24H")
        assert has_24h is True

        has_2h = await repo.has_reminder_been_sent(app_2h_id, "2H")
        assert has_2h is True

        has_far = await repo.has_reminder_been_sent(app_far_id, "24H")
        assert has_far is False

    # 2. Segunda ejecución consecutiva del worker
    # La idempotencia y deduplicación deben evitar que se vuelvan a enviar
    result2 = await process_appointment_reminders()
    assert result2["dispatched_24h"] == 0
    assert result2["dispatched_2h"] == 0
