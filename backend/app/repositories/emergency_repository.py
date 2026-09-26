"""Repositorio para Urgencias Médicas y Logs de Notificación (plan/plan.md 2.B.7)."""

import datetime
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.emergency_incident import EmergencyIncident
from app.models.notification_log import NotificationLog
from app.models.user import User

CLOSED_STATUSES = ("RESOLVED", "CANCELLED", "EXPIRED")
# Estados en los que el orquestador automatico sigue escalando (nadie tomo el caso).
UNATTENDED_STATUSES_PREFIXES = ("TRIGGERED", "DISPATCHED", "ESCALATED_")


def is_unattended(status: str) -> bool:
    return status.startswith(UNATTENDED_STATUSES_PREFIXES)


class EmergencyRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_incident(self, incident: EmergencyIncident) -> EmergencyIncident:
        self.db.add(incident)
        await self.db.flush()
        await self.db.refresh(incident)
        return incident

    async def get_by_id(self, incident_id: str) -> EmergencyIncident | None:
        stmt = (
            select(EmergencyIncident)
            .options(
                selectinload(EmergencyIncident.patient),
                selectinload(EmergencyIncident.assigned_doctor),
                selectinload(EmergencyIncident.clinic),
                selectinload(EmergencyIncident.notification_logs),
            )
            .where(EmergencyIncident.id == incident_id)
            # Refresca las relaciones aunque el objeto ya este en la sesion
            # (expire_on_commit=False): la bitacora cambia en cada escalamiento.
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_active(self, clinic_id: str | None = None) -> list[EmergencyIncident]:
        stmt = (
            select(EmergencyIncident)
            .options(
                selectinload(EmergencyIncident.patient),
                selectinload(EmergencyIncident.assigned_doctor),
                selectinload(EmergencyIncident.clinic),
                selectinload(EmergencyIncident.notification_logs),
            )
            .where(EmergencyIncident.status.not_in(CLOSED_STATUSES))
        )
        if clinic_id:
            stmt = stmt.where(
                or_(
                    EmergencyIncident.clinic_id == clinic_id,
                    EmergencyIncident.clinic_id.is_(None),
                )
            )
        stmt = stmt.order_by(desc(EmergencyIncident.created_at))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_patient_incidents(self, patient_id: str) -> list[EmergencyIncident]:
        stmt = (
            select(EmergencyIncident)
            .options(
                selectinload(EmergencyIncident.assigned_doctor),
                selectinload(EmergencyIncident.clinic),
                selectinload(EmergencyIncident.notification_logs),
            )
            .where(EmergencyIncident.patient_id == patient_id)
            .order_by(desc(EmergencyIncident.created_at))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def add_notification_log(self, log: NotificationLog) -> NotificationLog:
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def list_logs_for_incident(self, incident_id: str) -> list[NotificationLog]:
        stmt = (
            select(NotificationLog)
            .options(selectinload(NotificationLog.recipient))
            .where(NotificationLog.incident_id == incident_id)
            .order_by(NotificationLog.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def find_eligible_doctors(self, clinic_id: str | None = None) -> list[User]:
        """Lista ORDENADA de medicos de guardia (plan 2.B.7).

        Solo medicos ACTIVE, con matricula VERIFIED y guardia activada. Primero
        los afiliados (ACTIVE) a la clinica del incidente, por antiguedad de la
        afiliacion; si la clinica no tiene ninguno de guardia, se recurre a la
        lista global de guardia para no dejar al paciente sin respuesta.
        """
        base_filters = (
            User.role == "DOCTOR",
            User.status == "ACTIVE",
            User.license_verification_status == "VERIFIED",
            User.is_available_for_emergencies.is_(True),
        )
        if clinic_id:
            from app.models.affiliation import DoctorClinicAffiliation

            stmt = (
                select(User)
                .join(DoctorClinicAffiliation, DoctorClinicAffiliation.doctor_id == User.id)
                .where(
                    *base_filters,
                    DoctorClinicAffiliation.clinic_id == clinic_id,
                    DoctorClinicAffiliation.status == "ACTIVE",
                )
                .order_by(DoctorClinicAffiliation.created_at.asc(), User.id.asc())
            )
            doctors = list((await self.db.execute(stmt)).scalars().unique().all())
            if doctors:
                return doctors
        stmt = select(User).where(*base_filters).order_by(User.created_at.asc(), User.id.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_unattended(self) -> list[EmergencyIncident]:
        """Incidentes que el orquestador debe evaluar (nadie los ha tomado)."""
        stmt = (
            select(EmergencyIncident)
            .options(selectinload(EmergencyIncident.clinic), selectinload(EmergencyIncident.notification_logs))
            .where(
                or_(
                    EmergencyIncident.status.in_(("TRIGGERED", "DISPATCHED")),
                    EmergencyIncident.status.like("ESCALATED_%"),
                )
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_for_update(self, incident_id: str) -> EmergencyIncident | None:
        """Bloquea la fila del incidente (evita que dos medicos tomen el mismo caso
        o que el orquestador escale mientras un medico acepta)."""
        stmt = select(EmergencyIncident).where(EmergencyIncident.id == incident_id).with_for_update()
        result = await self.db.execute(stmt)
        return result.scalars().first()
