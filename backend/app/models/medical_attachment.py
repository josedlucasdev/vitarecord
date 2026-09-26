from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.tenant import TenantScoped
from app.models.base import Base, TimestampMixin, generate_uuid


class MedicalAttachment(Base, TimestampMixin, TenantScoped):
    """Metadatos de anexos y estudios clinicos almacenados en S3 (plan/plan.md 2.B.8)."""

    __tablename__ = "medical_attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    medical_record_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("medical_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    clinic_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clinics.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)

    medical_record: Mapped["MedicalRecord"] = relationship("MedicalRecord", back_populates="attachments")
