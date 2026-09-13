import datetime
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship as sa_relationship


from app.models.base import Base, TimestampMixin, generate_uuid


class NotificationLog(Base, TimestampMixin):
    """Registro inmutable de intentos de notificación y entrega multicanal (plan/plan.md 2.B.7)."""

    __tablename__ = "notification_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    incident_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("emergency_incidents.id", ondelete="CASCADE"), nullable=True, index=True)
    appointment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("appointments.id", ondelete="CASCADE"), nullable=True, index=True)
    recipient_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    # Canal: WEBSOCKET, PUSH, WHATSAPP, VOICE_CALL, SMS, EMAIL
    channel: Mapped[str] = mapped_column(String(32), nullable=False)

    # Estado: PENDING, SENT, DELIVERED, FAILED, ACKNOWLEDGED
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SENT")

    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sent_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    delivered_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    response_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)

    external_message_id: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    metadata_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    incident: Mapped["EmergencyIncident"] = sa_relationship("EmergencyIncident", back_populates="notification_logs")

    appointment: Mapped["Appointment"] = sa_relationship("Appointment", back_populates="notification_logs")
    recipient: Mapped["User"] = sa_relationship("User", foreign_keys=[recipient_id])

