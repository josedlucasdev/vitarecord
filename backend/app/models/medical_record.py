from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class MedicalRecord(Base, TimestampMixin):
    """Expediente clinico individualizado y cifrado en reposo con Envelope Encryption (plan/plan.md 2.B.8)."""

    __tablename__ = "medical_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    appointment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("appointments.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
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

    # Campos confidenciales cifrados en reposo (AES-256-GCM Base64)
    encrypted_anamnesis: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_physical_exam: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_plan: Mapped[str] = mapped_column(Text, nullable=False)

    # Diagnostico estandarizado CIE-10 / ICD-10 (no PHI identificable, para clasificacion y auditoria)
    icd10_code: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    icd10_description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Version de la clave DEK usada en el cifrado para permitir rotacion progresiva
    encryption_key_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="COMPLETED", index=True)

    # Relaciones
    appointment: Mapped["Appointment"] = relationship("Appointment", backref="medical_record")
    clinic: Mapped["Clinic"] = relationship("Clinic", backref="medical_records")
    doctor: Mapped["User"] = relationship("User", foreign_keys=[doctor_id])
    patient: Mapped["User"] = relationship("User", foreign_keys=[patient_id])
    dependent: Mapped["PatientDependent"] = relationship("PatientDependent", foreign_keys=[dependent_id])
    prescriptions: Mapped[list["Prescription"]] = relationship("Prescription", back_populates="medical_record")
    attachments: Mapped[list["MedicalAttachment"]] = relationship("MedicalAttachment", back_populates="medical_record")
