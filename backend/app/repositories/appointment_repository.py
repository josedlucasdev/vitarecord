import datetime
from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.appointment import Appointment
from app.models.clinic import Clinic, ClinicRoom
from app.models.payment_record import PaymentRecord
from app.models.user import User

NON_CONFLICT_STATUSES = (
    "CANCELLED_BY_PATIENT",
    "CANCELLED_BY_DOCTOR",
    "CANCELLED_BY_CLINIC",
    "REJECTED_BY_PATIENT",
    "RESCHEDULED",
)


class AppointmentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def acquire_locks(self, doctor_id: str, room_id: str | None = None) -> None:
        """Adquiere cerrojos mutex pesimistas en MySQL (plan/plan.md seccion 2.B.4)."""
        # Asegurar filas mutex
        await self.db.execute(
            text("INSERT IGNORE INTO doctor_schedule_locks (doctor_id) VALUES (:doc_id)"),
            {"doc_id": doctor_id},
        )
        if room_id:
            await self.db.execute(
                text("INSERT IGNORE INTO room_schedule_locks (room_id) VALUES (:r_id)"),
                {"r_id": room_id},
            )

        # SELECT ... FOR UPDATE
        await self.db.execute(
            text("SELECT doctor_id FROM doctor_schedule_locks WHERE doctor_id = :doc_id FOR UPDATE"),
            {"doc_id": doctor_id},
        )
        if room_id:
            await self.db.execute(
                text("SELECT room_id FROM room_schedule_locks WHERE room_id = :r_id FOR UPDATE"),
                {"r_id": room_id},
            )

    async def find_conflicts(
        self,
        doctor_id: str,
        room_id: str | None,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        exclude_id: str | None = None,
    ) -> list[Appointment]:
        """Detecta citas solapadas para el mismo doctor (cualquier clinica) o consultorio fisico."""
        conditions = [
            Appointment.status.not_in(NON_CONFLICT_STATUSES),
            Appointment.start_time < end_time,
            Appointment.end_time > start_time,
        ]

        if room_id:
            conditions.append(
                or_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.room_id == room_id,
                )
            )
        else:
            conditions.append(Appointment.doctor_id == doctor_id)

        if exclude_id:
            conditions.append(Appointment.id != exclude_id)

        stmt = select(Appointment).where(*conditions)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create(self, appointment: Appointment) -> Appointment:
        self.db.add(appointment)
        await self.db.flush()
        return appointment

    async def get_by_id(self, appointment_id: str) -> Appointment | None:
        stmt = (
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .options(
                selectinload(Appointment.doctor),
                selectinload(Appointment.patient),
                selectinload(Appointment.clinic),
                selectinload(Appointment.room),
                selectinload(Appointment.dependent),
                selectinload(Appointment.payment_record),
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def update_status(
        self,
        appointment_id: str,
        new_status: str,
        cancellation_reason: str | None = None,
    ) -> Appointment | None:
        app = await self.get_by_id(appointment_id)
        if app:
            app.status = new_status
            if cancellation_reason:
                app.cancellation_reason = cancellation_reason
            await self.db.flush()
        return app

    async def list_filtered(
        self,
        clinic_id: str | None = None,
        doctor_id: str | None = None,
        patient_id: str | None = None,
        date: datetime.date | None = None,
        status: str | None = None,
    ) -> list[Appointment]:
        stmt = (
            select(Appointment)
            .options(
                selectinload(Appointment.doctor),
                selectinload(Appointment.patient),
                selectinload(Appointment.clinic),
                selectinload(Appointment.room),
                selectinload(Appointment.dependent),
                selectinload(Appointment.payment_record),
            )
            .order_by(Appointment.start_time.asc())
        )

        if clinic_id:
            stmt = stmt.where(Appointment.clinic_id == clinic_id)
        if doctor_id:
            stmt = stmt.where(Appointment.doctor_id == doctor_id)
        if patient_id:
            stmt = stmt.where(Appointment.patient_id == patient_id)
        if status:
            stmt = stmt.where(Appointment.status == status)
        if date:
            start_of_day = datetime.datetime.combine(date, datetime.time.min)
            end_of_day = datetime.datetime.combine(date, datetime.time.max)
            stmt = stmt.where(Appointment.start_time >= start_of_day, Appointment.start_time <= end_of_day)

        res = await self.db.execute(stmt)
        return list(res.scalars().all())
