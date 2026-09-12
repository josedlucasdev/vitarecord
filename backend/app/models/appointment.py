import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class Appointment(Base, TimestampMixin):
    """Cita médica programada con soporte de salas físicas y familiares (plan/plan.md 2.B.4 y 2.B.5)."""

    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id", ondelete="RESTRICT"), nullable=False, index=True)
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    dependent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("patient_dependents.id", ondelete="SET NULL"), nullable=True, index=True)
    room_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("clinic_rooms.id", ondelete="SET NULL"), nullable=True, index=True)

    start_time: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_time: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, index=True)

    # Estados según máquina de estados del plan:
    # PENDING_DOCTOR_APPROVAL, PENDING_PATIENT_ACCEPTANCE, SCHEDULED, CONFIRMED, CHECKED_IN, IN_CONSULTATION,
    # COMPLETED, CANCELLED_BY_PATIENT, CANCELLED_BY_DOCTOR, CANCELLED_BY_CLINIC,
    # REJECTED_BY_PATIENT, REJECTED_BY_DOCTOR, NO_SHOW, RESCHEDULED
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SCHEDULED", index=True)

    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    intake_data: Mapped[dict | None] = mapped_column(JSON, default=dict)

    # Relaciones
    clinic: Mapped["Clinic"] = relationship("Clinic", backref="appointments")
    doctor: Mapped["User"] = relationship("User", foreign_keys=[doctor_id], backref="doctor_appointments")
    patient: Mapped["User"] = relationship("User", foreign_keys=[patient_id], backref="patient_appointments")
    dependent: Mapped["PatientDependent"] = relationship("PatientDependent", backref="appointments")
    room: Mapped["ClinicRoom"] = relationship("ClinicRoom", backref="appointments")
    payment_record: Mapped["PaymentRecord"] = relationship("PaymentRecord", back_populates="appointment", uselist=False)
