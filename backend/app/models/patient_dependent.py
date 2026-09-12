import datetime
from sqlalchemy import Date, ForeignKey, String
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

    # Relacion con el paciente titular
    guardian: Mapped["User"] = sa_relationship("User", backref="dependents")
