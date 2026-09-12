import datetime
from pydantic import BaseModel, ConfigDict, Field


class EmergencySosRequest(BaseModel):
    clinic_id: str | None = None
    dependent_id: str | None = None
    chief_complaint: str = Field(..., min_length=3, max_length=255)
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    # Verificación bloqueante: debe ser True para poder activar SOS
    disclaimer_acknowledged: bool = Field(
        ...,
        description="Confirma que leyó la advertencia de que este servicio no sustituye al 911/emergencias oficiales.",
    )


class EmergencyResolveRequest(BaseModel):
    triage_notes: str = Field(..., min_length=5)


class NotificationLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    recipient_id: str | None = None
    recipient_name: str | None = None
    channel: str
    status: str
    attempt_number: int
    sent_at: datetime.datetime
    delivered_at: datetime.datetime | None = None
    response_time_seconds: float | None = None
    error_message: str | None = None


class EmergencyIncidentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    clinic_id: str
    patient_id: str
    dependent_id: str | None = None
    assigned_doctor_id: str | None = None
    status: str
    escalation_level: int
    chief_complaint: str
    triage_notes: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    # Contexto para Torre de Control
    patient_name: str | None = None
    doctor_name: str | None = None
    clinic_name: str | None = None

    disclaimer_acknowledged_at: datetime.datetime
    triggered_at: datetime.datetime
    accepted_at: datetime.datetime | None = None
    resolved_at: datetime.datetime | None = None
    response_time_seconds: float | None = None
    notification_logs: list[NotificationLogPublic] = []
