import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class AppointmentCreate(BaseModel):
    clinic_id: str
    doctor_id: str
    patient_id: str | None = None  # Si es null, se asigna al usuario autenticado
    dependent_id: str | None = None
    room_id: str | None = None
    start_time: datetime.datetime
    end_time: datetime.datetime
    reason: str | None = None
    estimated_amount: Decimal = Field(default=Decimal("30.00"), ge=0)
    currency: str = Field(default="USD", max_length=8)


class AppointmentCancelRequest(BaseModel):
    cancellation_reason: str = Field(..., min_length=3, max_length=255)


class AppointmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    clinic_id: str
    doctor_id: str
    patient_id: str
    dependent_id: str | None = None
    room_id: str | None = None
    start_time: datetime.datetime
    end_time: datetime.datetime
    status: str
    reason: str | None = None
    cancellation_reason: str | None = None

    # Campos enriquecidos para la UI
    doctor_name: str | None = None
    patient_name: str | None = None
    clinic_name: str | None = None
    room_name: str | None = None
    payment_status: str | None = None
    payment_amount: Decimal | None = None
    currency: str | None = None

    created_at: datetime.datetime
