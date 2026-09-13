"""Clinica, salas fisicas y su fila mutex (plan/plan.md seccion 2.B.1 y 2.B.4)."""

from sqlalchemy import Boolean, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.tenant import TenantScopedMixin
from app.models.base import Base, TimestampMixin, generate_uuid


class Clinic(Base, TimestampMixin):
    __tablename__ = "clinics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/Caracas")
    # Determina la normativa de proteccion de datos y retencion aplicable
    # (plan/plan.md seccion 2.B.11) - nunca se asume HIPAA/GDPR por defecto.
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ClinicRoom(Base, TimestampMixin, TenantScopedMixin):
    __tablename__ = "clinic_rooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    room_number: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(255))
    specialty: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    operating_hours: Mapped[dict | None] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RoomScheduleLock(Base):
    """Fila mutex sin datos de negocio (plan/plan.md seccion 2.B.4).

    Se crea una fila por consultorio (INSERT IGNORE) y se bloquea con
    SELECT ... FOR UPDATE antes de comprobar solapamientos de citas, de modo
    que la exclusion mutua no depende de que ya exista una cita en conflicto.
    """

    __tablename__ = "room_schedule_locks"

    room_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinic_rooms.id"), primary_key=True)
