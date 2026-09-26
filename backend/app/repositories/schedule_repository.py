from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import cross_tenant
from app.models.schedule import DoctorWeeklySchedule


class ScheduleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_by_doctor_and_clinic(
        self, doctor_id: str, clinic_id: str
    ) -> list[DoctorWeeklySchedule]:
        stmt = (
            select(DoctorWeeklySchedule)
            .where(
                DoctorWeeklySchedule.doctor_id == doctor_id,
                DoctorWeeklySchedule.clinic_id == clinic_id,
                DoctorWeeklySchedule.is_active.is_(True),
            )
            .order_by(DoctorWeeklySchedule.day_of_week.asc(), DoctorWeeklySchedule.start_time.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_all_for_doctor(self, doctor_id: str) -> list[DoctorWeeklySchedule]:
        stmt = (
            select(DoctorWeeklySchedule)
            .where(
                DoctorWeeklySchedule.doctor_id == doctor_id,
                DoctorWeeklySchedule.is_active.is_(True),
            )
            .order_by(DoctorWeeklySchedule.day_of_week.asc(), DoctorWeeklySchedule.start_time.asc())
        )
        # Inter-clinica a proposito: la agenda semanal completa del medico
        # (todas sus sedes) se usa para evitar bloques solapados entre clinicas.
        result = await self.db.execute(cross_tenant(stmt))
        return list(result.scalars().all())

    async def replace_weekly_schedules(
        self, doctor_id: str, clinic_id: str, new_schedules: list[DoctorWeeklySchedule]
    ) -> list[DoctorWeeklySchedule]:
        # Eliminar anteriores para este medico en esta clinica
        stmt = delete(DoctorWeeklySchedule).where(
            DoctorWeeklySchedule.doctor_id == doctor_id,
            DoctorWeeklySchedule.clinic_id == clinic_id,
        )
        await self.db.execute(stmt)

        # Insertar nuevos
        for sch in new_schedules:
            sch.doctor_id = doctor_id
            sch.clinic_id = clinic_id
            self.db.add(sch)

        await self.db.flush()
        return new_schedules
