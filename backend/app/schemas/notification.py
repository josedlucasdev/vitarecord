"""Esquemas Pydantic para notificaciones multicanal, webhooks y preferencias (plan/plan.md Módulo 6 y 2.B.7)."""

import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

NotificationChannelType = Literal["WHATSAPP", "SMS", "VOICE_CALL", "EMAIL", "PUSH", "WEBSOCKET"]
NotificationStatusType = Literal["PENDING", "SENT", "DELIVERED", "FAILED", "ACKNOWLEDGED"]


class NotificationPreferenceUpdate(BaseModel):
    """Actualización de canales preferidos por el usuario."""
    preferred_notification_channels: list[NotificationChannelType] = Field(
        ...,
        description="Lista ordenada de canales preferidos por el usuario",
        example=["WHATSAPP", "EMAIL"]
    )


class NotificationPreferenceResponse(BaseModel):
    user_id: str
    preferred_notification_channels: list[str]
    has_whatsapp: bool
    fallback_channels: list[str] = ["PUSH", "SMS", "VOICE_CALL", "EMAIL"]


class DeviceTokenRegisterRequest(BaseModel):
    fcm_token: str = Field(..., min_length=10, max_length=512, description="Registration token de FCM")
    platform: Literal["web", "android", "ios"] = "web"
    device_name: str | None = Field(None, max_length=128, description="Nombre descriptivo del dispositivo")


class DeviceTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    fcm_token: str
    platform: str
    device_name: str | None = None
    is_active: bool
    last_used_at: datetime.datetime | None = None
    created_at: datetime.datetime


class NotificationSendRequest(BaseModel):
    recipient_id: str | None = None
    appointment_id: str | None = None
    incident_id: str | None = None
    channel: NotificationChannelType | None = None
    phone: str | None = None
    email: str | None = None
    subject: str | None = None
    message: str = Field(..., min_length=1)
    template_name: str | None = None
    template_params: dict[str, Any] | None = None


class NotificationLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    incident_id: str | None = None
    appointment_id: str | None = None
    recipient_id: str | None = None
    recipient_name: str | None = None
    channel: str
    status: str
    attempt_number: int
    sent_at: datetime.datetime
    delivered_at: datetime.datetime | None = None
    response_time_seconds: float | None = None
    error_message: str | None = None
    external_message_id: str | None = None
    metadata_payload: dict[str, Any] | None = None
    is_read: bool = False
    read_at: datetime.datetime | None = None


class InAppNotificationSummary(BaseModel):
    unread_count: int
    notifications: list[NotificationLogPublic]

