"""Repositorio asíncrono para el registro y consulta de notificaciones multicanal (plan/plan.md Módulo 6 y 2.B.7)."""

import datetime
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notification_log import NotificationLog


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, log: NotificationLog) -> NotificationLog:
        self.db.add(log)
        await self.db.flush()
        return log

    async def get_by_id(self, log_id: str) -> NotificationLog | None:
        stmt = (
            select(NotificationLog)
            .options(selectinload(NotificationLog.recipient))
            .where(NotificationLog.id == log_id)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_external_id(self, external_id: str) -> NotificationLog | None:
        stmt = (
            select(NotificationLog)
            .options(selectinload(NotificationLog.recipient))
            .where(NotificationLog.external_message_id == external_id)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_appointment(self, appointment_id: str) -> list[NotificationLog]:
        stmt = (
            select(NotificationLog)
            .options(selectinload(NotificationLog.recipient))
            .where(NotificationLog.appointment_id == appointment_id)
            .order_by(desc(NotificationLog.created_at))
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def list_by_recipient(self, recipient_id: str, limit: int = 50) -> list[NotificationLog]:
        stmt = (
            select(NotificationLog)
            .options(selectinload(NotificationLog.recipient))
            .where(NotificationLog.recipient_id == recipient_id)
            .order_by(desc(NotificationLog.created_at))
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def list_by_incident(self, incident_id: str) -> list[NotificationLog]:
        stmt = (
            select(NotificationLog)
            .options(selectinload(NotificationLog.recipient))
            .where(NotificationLog.incident_id == incident_id)
            .order_by(NotificationLog.created_at.asc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def update_status(
        self,
        log_id: str,
        status: str,
        delivered_at: datetime.datetime | None = None,
        response_time_seconds: float | None = None,
        error_message: str | None = None,
    ) -> NotificationLog | None:
        log = await self.get_by_id(log_id)
        if not log:
            return None
        log.status = status
        if delivered_at is not None:
            log.delivered_at = delivered_at
        if response_time_seconds is not None:
            log.response_time_seconds = response_time_seconds
        if error_message is not None:
            log.error_message = error_message
        await self.db.flush()
        return log

    async def has_reminder_been_sent(self, appointment_id: str, reminder_stage: str) -> bool:
        """Verifica si ya se envió un recordatorio específico (ej. '24H' o '2H') para esta cita."""
        logs = await self.list_by_appointment(appointment_id)
        for log in logs:
            if log.metadata_payload and log.metadata_payload.get("reminder_stage") == reminder_stage:
                if log.status in ("SENT", "DELIVERED", "ACKNOWLEDGED"):
                    return True
        return False

    async def count_unread_for_user(self, recipient_id: str) -> int:
        from sqlalchemy import func
        stmt = (
            select(func.count(NotificationLog.id))
            .where(
                NotificationLog.recipient_id == recipient_id,
                NotificationLog.is_read.is_(False),
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one() or 0

    async def mark_as_read(self, log_id: str) -> NotificationLog | None:
        log = await self.get_by_id(log_id)
        if not log:
            return None
        log.is_read = True
        log.read_at = datetime.datetime.utcnow()
        await self.db.flush()
        return log

    async def mark_all_as_read_for_user(self, recipient_id: str) -> int:
        from sqlalchemy import update
        now = datetime.datetime.utcnow()
        stmt = (
            update(NotificationLog)
            .where(
                NotificationLog.recipient_id == recipient_id,
                NotificationLog.is_read.is_(False),
            )
            .values(is_read=True, read_at=now)
        )
        res = await self.db.execute(stmt)
        await self.db.flush()
        return res.rowcount

