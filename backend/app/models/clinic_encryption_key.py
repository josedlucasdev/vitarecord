from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class ClinicEncryptionKey(Base, TimestampMixin):
    """Llave de cifrado de datos (DEK) por clinica protegida con KEK en Vault (plan/plan.md 2.B.8)."""

    __tablename__ = "clinic_encryption_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    encrypted_dek: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    clinic: Mapped["Clinic"] = relationship("Clinic", backref="encryption_keys")
