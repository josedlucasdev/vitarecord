from datetime import datetime
import uuid
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SupportChatSession(Base):
    __tablename__ = "support_chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    id_card: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now(), nullable=False)

    messages: Mapped[list["SupportChatMessage"]] = relationship("SupportChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="SupportChatMessage.created_at")


class SupportChatMessage(Base):
    __tablename__ = "support_chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("support_chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_type: Mapped[str] = mapped_column(String(16), nullable=False)  # "visitor" o "agent"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    telegram_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False)

    session: Mapped["SupportChatSession"] = relationship("SupportChatSession", back_populates="messages")
