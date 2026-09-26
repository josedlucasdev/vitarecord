import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship as sa_relationship

from app.core.tenant import TenantScoped
from app.models.base import Base, TimestampMixin, generate_uuid


class EmergencyIncident(Base, TimestampMixin, TenantScoped):
    """Incidente de urgencia médica remota con trazabilidad de escalamiento (plan/plan.md 2.B.7)."""

    __tablename__ = "emergency_incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id", ondelete="RESTRICT"), nullable=False, index=True)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    dependent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("patient_dependents.id", ondelete="SET NULL"), nullable=True)
    assigned_doctor_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Estados: TRIGGERED, DISPATCHED, ESCALATED_DOCTOR_<n>, ACCEPTED, ESCALATED_MODERATOR,
    # ESCALATED_BACKUP, RESOLVED, CANCELLED
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="TRIGGERED", index=True)
    escalation_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    chief_complaint: Mapped[str] = mapped_column(String(255), nullable=False)
    triage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Marca temporal de auditoría de confirmación del disclaimer legal previo
    disclaimer_acknowledged_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    triggered_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    accepted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    # Orquestador automatico de escalamiento (plan 2.B.7): momento en que se
    # entro al nivel actual; los SLA (15 s entrega, 60 s aceptacion, 2 min
    # moderador) se miden desde aqui.
    last_escalated_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    # Reconocimiento del moderador/SuperAdmin de turno (detiene el escalamiento
    # hacia la linea de respaldo de la clinica).
    acknowledged_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    acknowledged_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relaciones
    clinic: Mapped["Clinic"] = sa_relationship("Clinic", backref="emergency_incidents")
    patient: Mapped["User"] = sa_relationship("User", foreign_keys=[patient_id], backref="emergencies_requested")
    assigned_doctor: Mapped["User"] = sa_relationship("User", foreign_keys=[assigned_doctor_id], backref="emergencies_handled")
    dependent: Mapped["PatientDependent"] = sa_relationship("PatientDependent", backref="emergencies")
    notification_logs: Mapped[list["NotificationLog"]] = sa_relationship("NotificationLog", back_populates="incident", cascade="all, delete-orphan")
