import datetime
from sqlalchemy import Date, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship as sa_relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class PatientDependent(Base, TimestampMixin):
    """Familiar / Dependiente registrado por el paciente titular (plan/plan.md 2.B.5)."""

    __tablename__ = "patient_dependents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    guardian_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    relationship: Mapped[str] = mapped_column(String(32), nullable=False, default="HIJO")
    birth_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    id_document: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    emancipation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="MINOR")

    # Ficha clínica basal del familiar
    blood_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    allergies: Mapped[str | None] = mapped_column(String(500), nullable=True)
    chronic_conditions: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Contacto adicional y notas
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    profile_picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Emancipación y vinculación a cuenta propia independiente
    linked_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    emancipated_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    # Relaciones
    guardian: Mapped["User"] = sa_relationship("User", foreign_keys=[guardian_user_id], backref="dependents")
    linked_user: Mapped["User | None"] = sa_relationship("User", foreign_keys=[linked_user_id])

