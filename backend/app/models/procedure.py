"""Modelos de procedimientos medicos y procedimientos aplicados a citas."""

from decimal import Decimal
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.core.tenant import TenantScoped
from app.models.base import Base, TimestampMixin, generate_uuid


class MedicalProcedure(Base, TimestampMixin, TenantScoped):
    """Catalogo de procedimientos clinicos (ecografias, biopsias, colposcopias, etc.)
    
    Si doctor_id es NULL: Es un procedimiento institucional regulado por la clinica (medicos contratados).
    Si doctor_id NO es NULL: Es un procedimiento propio configurado por un medico autonomo (alquiler de consultorio).
    """

    __tablename__ = "medical_procedures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relaciones
    clinic: Mapped["Clinic"] = relationship(
        "Clinic",
        backref=backref("medical_procedures", cascade="all, delete-orphan", passive_deletes=True),
        passive_deletes=True,
    )
    doctor: Mapped["User | None"] = relationship("User", foreign_keys=[doctor_id], backref="custom_procedures")


class AppointmentProcedure(Base, TimestampMixin):
    """Procedimiento clinico realizado o seleccionado para una cita medica especifica."""

    __tablename__ = "appointment_procedures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    appointment_id: Mapped[str] = mapped_column(String(36), ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True)
    procedure_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("medical_procedures.id", ondelete="SET NULL"), nullable=True, index=True)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relaciones
    appointment: Mapped["Appointment"] = relationship("Appointment", back_populates="procedures")
    procedure: Mapped["MedicalProcedure | None"] = relationship("MedicalProcedure")
