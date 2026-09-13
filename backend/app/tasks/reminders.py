"""Worker y programador de recordatorios automáticos de citas (plan/plan.md Módulo 6 y 2.B.5)."""

import asyncio
import datetime
import logging
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.core.broker import broker
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis

from app.models.appointment import Appointment
from app.models.clinic import Clinic, ClinicRoom
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.services.notification_service import NotificationService

logger = logging.getLogger("reminder_worker")


@broker.task
async def check_and_send_appointment_reminders_task() -> dict[str, int]:
    """Tarea Taskiq ejecutable por el worker en background."""
    return await process_appointment_reminders()


async def process_appointment_reminders() -> dict[str, int]:
    """Escanea citas próximas y despacha recordatorios multicanal a 24 horas y 2 horas del turno."""
    now = datetime.datetime.utcnow()
    dispatched_24h = 0
    dispatched_2h = 0

    # Ventanas de tiempo para detección
    window_24h_start = now + datetime.timedelta(hours=23)
    window_24h_end = now + datetime.timedelta(hours=25)

    window_2h_start = now + datetime.timedelta(minutes=90)
    window_2h_end = now + datetime.timedelta(minutes=150)

    async with AsyncSessionLocal() as db:
        repo = NotificationRepository(db)
        notif_service = NotificationService(db)

        # 1. Citas candidatas a recordatorio de 24 horas
        stmt_24h = (
            select(Appointment)
            .options(
                selectinload(Appointment.patient),
                selectinload(Appointment.doctor),
                selectinload(Appointment.clinic),
                selectinload(Appointment.room),
            )
            .where(
                Appointment.status.in_(("CONFIRMED", "SCHEDULED", "PENDING_PATIENT_ACCEPTANCE")),
                Appointment.start_time >= window_24h_start,
                Appointment.start_time <= window_24h_end,
            )
        )
        res_24h = await db.execute(stmt_24h)
        apps_24h = res_24h.scalars().all()

        for app in apps_24h:
            already_sent = await repo.has_reminder_been_sent(app.id, "24H")
            if not already_sent and app.patient and app.doctor:
                clinic_name = app.clinic.name if app.clinic else "ÍntimaSalud"
                room_name = app.room.name if app.room else None
                await notif_service.send_appointment_reminder(
                    appointment=app,
                    patient=app.patient,
                    doctor=app.doctor,
                    clinic_name=clinic_name,
                    room_name=room_name,
                    reminder_stage="24H",
                )
                dispatched_24h += 1
                logger.info("Recordatorio 24H enviado para cita %s (%s)", app.id, app.start_time)

        # 2. Citas candidatas a recordatorio de 2 horas
        stmt_2h = (
            select(Appointment)
            .options(
                selectinload(Appointment.patient),
                selectinload(Appointment.doctor),
                selectinload(Appointment.clinic),
                selectinload(Appointment.room),
            )
            .where(
                Appointment.status.in_(("CONFIRMED", "SCHEDULED")),
                Appointment.start_time >= window_2h_start,
                Appointment.start_time <= window_2h_end,
            )
        )
        res_2h = await db.execute(stmt_2h)
        apps_2h = res_2h.scalars().all()

        for app in apps_2h:
            already_sent = await repo.has_reminder_been_sent(app.id, "2H")
            if not already_sent and app.patient and app.doctor:
                clinic_name = app.clinic.name if app.clinic else "ÍntimaSalud"
                room_name = app.room.name if app.room else None
                await notif_service.send_appointment_reminder(
                    appointment=app,
                    patient=app.patient,
                    doctor=app.doctor,
                    clinic_name=clinic_name,
                    room_name=room_name,
                    reminder_stage="2H",
                )
                dispatched_2h += 1
                logger.info("Recordatorio 2H enviado para cita %s (%s)", app.id, app.start_time)

    return {"dispatched_24h": dispatched_24h, "dispatched_2h": dispatched_2h}


async def start_reminder_scheduler(interval_seconds: int | None = None) -> None:
    """Bucle programador periódico con cerrojo distribuido en Redis."""
    interval = interval_seconds or settings.REMINDER_CHECK_INTERVAL_SECONDS
    logger.info("Iniciando programador periódico de recordatorios (intervalo: %ds)", interval)

    while True:
        try:
            r = get_redis()
            # Candado distribuido para que un solo worker procese el escaneo si hay varios uvicorns
            lock_acquired = await r.set("lock:appointment_reminders_scan", "1", nx=True, ex=interval - 2)

            if lock_acquired:
                await process_appointment_reminders()
        except asyncio.CancelledError:
            logger.info("Programador de recordatorios cancelado.")
            break
        except Exception as exc:
            logger.warning("Error en ciclo de programador de recordatorios: %s", exc)

        await asyncio.sleep(interval)
