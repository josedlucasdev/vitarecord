"""Servicio de Disponibilidad Horaria y Exclusión Mutua (plan/plan.md seccion 2.B.4)."""

from datetime import datetime, time, timedelta
import json
import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models.schedule import DoctorWeeklySchedule
from app.models.user import User
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.availability import (
    DoctorScheduleCreate,
    DoctorSchedulePublic,
    TimeSlotPublic,
)

logger = logging.getLogger("availability_service")


class AvailabilityService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.schedules = ScheduleRepository(db)
        self.users = UserRepository(db)

    async def set_doctor_schedules(
        self, doctor_id: str, payload: DoctorScheduleCreate, current_user: User
    ) -> list[DoctorSchedulePublic]:
        doctor = await self.users.get_by_id(doctor_id)
        if not doctor or doctor.role != "DOCTOR":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Médico no encontrado.")

        # Control ACL de asignacion de agenda
        if current_user.role == "DOCTOR" and current_user.id != doctor_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes modificar la agenda de otro médico.")
        if current_user.role == "CLINIC_ADMIN" and current_user.clinic_id != payload.clinic_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes configurar agendas en otra clínica.")

        models: list[DoctorWeeklySchedule] = []
        for block in payload.blocks:
            try:
                sh, sm = map(int, block.start_time.split(":"))
                eh, em = map(int, block.end_time.split(":"))
                st = time(sh, sm)
                et = time(eh, em)
            except Exception as exc:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Formato de hora inválido: {exc}") from exc

            if st >= et:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Hora de inicio ({block.start_time}) debe ser menor que la hora de fin ({block.end_time}).",
                )

            models.append(
                DoctorWeeklySchedule(
                    doctor_id=doctor_id,
                    clinic_id=payload.clinic_id,
                    day_of_week=block.day_of_week,
                    start_time=st,
                    end_time=et,
                    slot_duration_minutes=block.slot_duration_minutes,
                    is_active=True,
                )
            )

        saved = await self.schedules.replace_weekly_schedules(doctor_id, payload.clinic_id, models)
        await self.db.commit()

        # Invalidar cache en Redis para este medico y clinica
        try:
            r = get_redis()
            keys = await r.keys(f"slots:{payload.clinic_id}:{doctor_id}:*")
            if keys:
                await r.delete(*keys)
        except Exception as exc:
            logger.warning("No se pudo invalidar cache en Redis: %s", exc)

        return [
            DoctorSchedulePublic(
                id=s.id,
                doctor_id=s.doctor_id,
                clinic_id=s.clinic_id,
                day_of_week=s.day_of_week,
                start_time=s.start_time.strftime("%H:%M"),
                end_time=s.end_time.strftime("%H:%M"),
                slot_duration_minutes=s.slot_duration_minutes,
                is_active=s.is_active,
            )
            for s in saved
        ]

    async def get_doctor_schedules(
        self, doctor_id: str, clinic_id: str | None = None
    ) -> list[DoctorSchedulePublic]:
        if clinic_id:
            items = await self.schedules.list_by_doctor_and_clinic(doctor_id, clinic_id)
        else:
            items = await self.schedules.list_all_for_doctor(doctor_id)

        return [
            DoctorSchedulePublic(
                id=s.id,
                doctor_id=s.doctor_id,
                clinic_id=s.clinic_id,
                day_of_week=s.day_of_week,
                start_time=s.start_time.strftime("%H:%M"),
                end_time=s.end_time.strftime("%H:%M"),
                slot_duration_minutes=s.slot_duration_minutes,
                is_active=s.is_active,
            )
            for s in items
        ]

    async def calculate_available_slots(
        self, clinic_id: str, doctor_id: str, target_date_str: str
    ) -> list[TimeSlotPublic]:
        """Calcula slots libres con aceleracion de lectura en Redis y garantia de matricula verificada."""
        cache_key = f"slots:{clinic_id}:{doctor_id}:{target_date_str}"
        redis = get_redis()

        try:
            cached = await redis.get(cache_key)
            if cached:
                return [TimeSlotPublic(**item) for item in json.loads(cached)]
        except Exception as exc:
            logger.warning("Fallo al leer cache de Redis: %s", exc)

        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Fecha debe estar en formato YYYY-MM-DD.") from exc

        doctor = await self.users.get_by_id(doctor_id)
        if not doctor or doctor.role != "DOCTOR":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Médico no encontrado.")

        # Regla de Dominio: Un medico no verificado NUNCA muestra disponibilidad (plan/plan.md 2.B.2)
        if doctor.license_verification_status != "VERIFIED" or doctor.status != "ACTIVE":
            return []

        # Regla de Dominio: Consultar citas activas del médico en esa fecha para marcar disponibilidad
        from sqlalchemy import select
        from app.models.appointment import Appointment

        active_statuses = (
            "PENDING_PATIENT_ACCEPTANCE",
            "SCHEDULED",
            "CONFIRMED",
            "CHECKED_IN",
            "IN_CONSULTATION",
        )
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = datetime.combine(target_date, datetime.max.time())

        stmt_apps = select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.status.in_(active_statuses),
            Appointment.start_time >= day_start,
            Appointment.start_time <= day_end,
        )
        apps_res = await self.db.execute(stmt_apps)
        booked_appointments = list(apps_res.scalars().all())

        day_of_week = target_date.weekday()  # 0=Lunes, 6=Domingo
        weekly_blocks = await self.schedules.list_by_doctor_and_clinic(doctor_id, clinic_id)
        matching_blocks = [b for b in weekly_blocks if b.day_of_week == day_of_week]

        slots: list[TimeSlotPublic] = []
        for block in matching_blocks:
            current_dt = datetime.combine(target_date, block.start_time)
            end_dt = datetime.combine(target_date, block.end_time)
            slot_delta = timedelta(minutes=block.slot_duration_minutes)

            while current_dt + slot_delta <= end_dt:
                slot_start_str = current_dt.time().strftime("%H:%M")
                slot_end_str = (current_dt + slot_delta).time().strftime("%H:%M")

                is_occupied = any(
                    app.start_time < (current_dt + slot_delta) and app.end_time > current_dt
                    for app in booked_appointments
                )

                slots.append(
                    TimeSlotPublic(
                        start_time=slot_start_str,
                        end_time=slot_end_str,
                        is_available=not is_occupied,
                        clinic_id=clinic_id,
                        doctor_id=doctor_id,
                    )
                )
                current_dt += slot_delta

        # Cachear en Redis durante 60 segundos
        try:
            payload = [s.model_dump() for s in slots]
            await redis.setex(cache_key, 60, json.dumps(payload))
        except Exception as exc:
            logger.warning("Fallo al escribir en Redis: %s", exc)

        return slots
