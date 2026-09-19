"""Vinculacion medico-clinica (plan/plan.md seccion 2.B.2)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_uuid

AFFILIATION_STATUSES = ("INVITED", "INVITED_PENDING_VERIFICATION", "ACTIVE", "REJECTED", "SUSPENDED", "DISAFFILIATED")
AFFILIATION_CONTRACT_TYPES = ("INDEPENDENT", "EMPLOYED")


class DoctorClinicAffiliation(Base, TimestampMixin):
    __tablename__ = "doctor_clinic_affiliations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="INVITED")
    invitation_token: Mapped[str | None] = mapped_column(String(500))
    invitation_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Modalidad de contratación y arancel de consulta en esta sede
    # INDEPENDENT: Médico autónomo (alquiler de consultorio) -> el médico fija su precio de consulta y procedimientos
    # EMPLOYED: Contratado por la clínica -> la clínica fija el precio de consulta y procedimientos
    contract_type: Mapped[str] = mapped_column(String(32), nullable=False, default="INDEPENDENT")
    consultation_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("30.00"))
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")


class PatientClinicAffiliation(Base, TimestampMixin):
    """Vinculación paciente-clínica para padrón de pacientes y atención en sedes."""

    __tablename__ = "patient_clinic_affiliations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

