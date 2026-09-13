import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class UserDeviceToken(Base, TimestampMixin):
    """Tokens de dispositivos (Firebase Cloud Messaging / Web Push) para notificaciones push móviles y de navegador."""

    __tablename__ = "user_device_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    fcm_token: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, default="web")  # "web", "android", "ios"
    device_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="device_tokens")
