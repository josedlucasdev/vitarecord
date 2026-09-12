import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class PatientConsentGrant(Base, TimestampMixin):
    """Consentimiento informado y delegación de acceso a historial médico (plan/plan.md 2.B.5)."""

    __tablename__ = "patient_consent_grants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_to_clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    scope: Mapped[str] = mapped_column(String(64), nullable=False, default="READ_MEDICAL_RECORDS")
    granted_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    granted_until: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    patient: Mapped["User"] = relationship("User", foreign_keys=[patient_id], backref="consents_given")
    clinic: Mapped["Clinic"] = relationship("Clinic", backref="consents_received")
    granted_by: Mapped["User"] = relationship("User", foreign_keys=[granted_by_user_id])
