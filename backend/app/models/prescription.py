import datetime
from typing import Any
from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class Prescription(Base, TimestampMixin):
    """Receta medica con token criptografico SHA-256 y codigo QR verificable en farmacias (plan/plan.md 2.B.8)."""

    __tablename__ = "prescriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    medical_record_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("medical_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    appointment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    clinic_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clinics.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    doctor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    dependent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("patient_dependents.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Hash SHA-256 determinista y firmado para el enlace publico del codigo QR
    verification_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    prescription_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)

    # Items farmacologicos estructurados: list[dict]
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)

    # Diagnostico o indicacion resumida para farmacia (sin antecedentes intimos)
    diagnosis_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    issued_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)

    # Estados: ACTIVE, DISPENSED, EXPIRED, REVOKED
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE", index=True)

    # Relaciones
    medical_record: Mapped["MedicalRecord"] = relationship("MedicalRecord", back_populates="prescriptions")
    appointment: Mapped["Appointment"] = relationship("Appointment")
    clinic: Mapped["Clinic"] = relationship("Clinic")
    doctor: Mapped["User"] = relationship("User", foreign_keys=[doctor_id])
    patient: Mapped["User"] = relationship("User", foreign_keys=[patient_id])
    dependent: Mapped["PatientDependent"] = relationship("PatientDependent", foreign_keys=[dependent_id])
