"""Repositorio para Urgencias Médicas y Logs de Notificación (plan/plan.md 2.B.7)."""

import datetime
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.emergency_incident import EmergencyIncident
from app.models.notification_log import NotificationLog
from app.models.user import User

ACTIVE_STATUSES = (
    "TRIGGERED",
    "DISPATCHED",
    "ESCALATED_DOCTOR_2",
    "ESCALATED_MODERATOR",
    "ESCALATED_BACKUP",
    "ACCEPTED",
)


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
            .where(EmergencyIncident.status.in_(ACTIVE_STATUSES))
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
        """Busca médicos activos con cédula/licencia VERIFIED y disponibilidad de urgencia activada."""
        stmt = (
            select(User)
            .where(
                User.role == "DOCTOR",
                User.status == "ACTIVE",
                User.license_verification_status == "VERIFIED",
                User.is_available_for_emergencies.is_(True),
            )
        )
        if clinic_id:
            stmt = stmt.where(or_(User.clinic_id == clinic_id, User.clinic_id.is_(None)))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
