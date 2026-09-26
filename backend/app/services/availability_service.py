"""Servicio de Disponibilidad Horaria y Exclusión Mutua (plan/plan.md seccion 2.B.4)."""

from datetime import datetime, time, timedelta
import json
import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models.clinic import ClinicRoom
from app.models.schedule import DoctorWeeklySchedule
from app.models.user import User
from app.repositories.room_repository import RoomRepository
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.availability import (
    DoctorScheduleCreate,
    DoctorSchedulePublic,
    TimeSlotPublic,
)

logger = logging.getLogger("availability_service")


def is_specialty_compatible(doctor_specialty: str | None, room_specialty: str | None) -> bool:
    """Determina si un consultorio físico es apto para un especialista."""
    if not room_specialty or not room_specialty.strip():
        # Consultorio polivalente / general: admite cualquier especialidad
        return True
    if not doctor_specialty or not doctor_specialty.strip():
        # Doctor sin especialidad definida: requiere consultorio polivalente
        return False

    doc_s = doctor_specialty.lower().strip()
    rm_s = room_specialty.lower().strip()
    if rm_s == doc_s or rm_s in doc_s or doc_s in rm_s:
        return True

    rm_tokens = set(rm_s.replace("&", " ").replace("/", " ").replace("-", " ").split())
    doc_tokens = set(doc_s.replace("&", " ").replace("/", " ").replace("-", " ").split())
    stopwords = {"y", "e", "de", "en", "&", "del", "la", "el", "los", "las"}
    rm_tokens = {t for t in rm_tokens if t not in stopwords and len(t) > 3}
    doc_tokens = {t for t in doc_tokens if t not in stopwords and len(t) > 3}
    return bool(rm_tokens.intersection(doc_tokens))


def is_room_open_at(room: ClinicRoom, slot_start: time, slot_end: time, day_of_week: int) -> bool:
    """Valida si el consultorio físico está operativo en el rango horario indicado."""
    if not room.operating_hours or not isinstance(room.operating_hours, dict):
        return True

    op = room.operating_hours
    day_key = str(day_of_week)
    day_config = op.get(day_key)
    if day_config is None:
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_config = op.get(day_names[day_of_week])

    if day_config is not None:
        if isinstance(day_config, dict):
            if day_config.get("closed") is True:
                return False
            st_str = day_config.get("start")
            et_str = day_config.get("end")
            if st_str and et_str:
                st = datetime.strptime(st_str, "%H:%M").time()
                et = datetime.strptime(et_str, "%H:%M").time()
                return slot_start >= st and slot_end <= et
        elif isinstance(day_config, list):
            for rng in day_config:
                st = datetime.strptime(rng["start"], "%H:%M").time()
                et = datetime.strptime(rng["end"], "%H:%M").time()
                if slot_start >= st and slot_end <= et:
                    return True
            return False

    # Chequear rango global diario
    if "start" in op and "end" in op:
        try:
            st = datetime.strptime(op["start"], "%H:%M").time()
            et = datetime.strptime(op["end"], "%H:%M").time()
            return slot_start >= st and slot_end <= et
        except Exception:
            pass

    return True


class AvailabilityService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.schedules = ScheduleRepository(db)
        self.users = UserRepository(db)
        self.rooms = RoomRepository(db)

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
            "PENDING_DOCTOR_APPROVAL",
            "PENDING_PATIENT_ACCEPTANCE",
            "SCHEDULED",
            "CONFIRMED",
            "CHECKED_IN",
            "IN_CONSULTATION",
        )
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = datetime.combine(target_date, datetime.max.time())

        # 1. Citas del médico (en cualquier clínica) para no solapar su tiempo personal
        stmt_apps = select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.status.in_(active_statuses),
            Appointment.start_time >= day_start,
            Appointment.start_time <= day_end,
        )
        # Inter-clinica a proposito (plan 2.B.4 Regla 1): el tiempo del medico es global.
        from app.core.tenant import cross_tenant
        apps_res = await self.db.execute(cross_tenant(stmt_apps))
        booked_appointments = list(apps_res.scalars().all())

        # 2. Consultorios físicos de la sede: deben estar activos y no en mantenimiento
        clinic_rooms = await self.rooms.list_by_clinic(clinic_id, active_only=True)
        active_rooms = [r for r in clinic_rooms if getattr(r, "status", "ACTIVE") == "ACTIVE"]

        # Consultorios compatibles con la especialidad del médico
        compatible_rooms = [
            r for r in active_rooms
            if is_specialty_compatible(doctor.specialty, getattr(r, "specialty", None))
        ]

        # 3. Citas de toda la clínica en esa fecha (para contabilizar consultorios ocupados)
        stmt_apps_clinic = select(Appointment).where(
            Appointment.clinic_id == clinic_id,
            Appointment.status.in_(active_statuses),
            Appointment.start_time >= day_start,
            Appointment.start_time <= day_end,
        )
        apps_clinic_res = await self.db.execute(stmt_apps_clinic)
        clinic_appointments = list(apps_clinic_res.scalars().all())

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
                slot_end_dt = current_dt + slot_delta

                # A. ¿El médico ya tiene una cita propia en este horario?
                doc_busy = any(
                    app.start_time < slot_end_dt and app.end_time > current_dt
                    for app in booked_appointments
                )

                # B. ¿Hay consultorio físico compatible disponible en la clínica?
                if not compatible_rooms:
                    room_available = False
                else:
                    open_rooms = [
                        r for r in compatible_rooms
                        if is_room_open_at(r, current_dt.time(), slot_end_dt.time(), day_of_week)
                    ]
                    occupied_room_ids = {
                        app.room_id for app in clinic_appointments
                        if app.room_id is not None
                        and app.start_time < slot_end_dt
                        and app.end_time > current_dt
                    }
                    free_rooms = [r for r in open_rooms if r.id not in occupied_room_ids]
                    unassigned_overlap_count = sum(
                        1 for app in clinic_appointments
                        if app.room_id is None
                        and app.start_time < slot_end_dt
                        and app.end_time > current_dt
                    )
                    room_available = len(free_rooms) > unassigned_overlap_count

                is_available = (not doc_busy) and room_available

                slots.append(
                    TimeSlotPublic(
                        start_time=slot_start_str,
                        end_time=slot_end_str,
                        is_available=is_available,
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
