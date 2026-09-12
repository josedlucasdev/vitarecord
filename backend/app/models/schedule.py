"""Modelado de reglas de horario y bloques de disponibilidad medica (plan/plan.md seccion 2.B.4)."""

from datetime import time

from sqlalchemy import Boolean, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.core.tenant import TenantScopedMixin
from app.models.base import Base, TimestampMixin, generate_uuid


class DoctorWeeklySchedule(Base, TimestampMixin, TenantScopedMixin):
    """Regla recurrente de atencion semanal de un medico en una clinica."""

    __tablename__ = "doctor_weekly_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    # clinic_id provisto por TenantScopedMixin (ForeignKey a clinics.id)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Lunes, 6=Domingo
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
