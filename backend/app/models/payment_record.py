import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.tenant import TenantScoped
from app.models.base import Base, TimestampMixin, generate_uuid


class PaymentRecord(Base, TimestampMixin, TenantScoped):
    """Registro contable manual de cobro vinculado a una cita médica (plan/plan.md 2.B.6)."""

    __tablename__ = "payment_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    appointment_id: Mapped[str] = mapped_column(String(36), ForeignKey("appointments.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id", ondelete="RESTRICT"), nullable=False, index=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")

    # Estados: UNPAID, PAID, EXEMPT (por rechazo), VOID (por cancelacion)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="UNPAID", index=True)

    # Métodos: CASH, CARD, TRANSFER, PAGO_MOVIL, ZELLE
    payment_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    recorded_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    paid_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    # Relaciones
    appointment: Mapped["Appointment"] = relationship("Appointment", back_populates="payment_record")
    clinic: Mapped["Clinic"] = relationship("Clinic", backref="payment_records")
    recorded_by: Mapped["User"] = relationship("User", foreign_keys=[recorded_by_user_id])
