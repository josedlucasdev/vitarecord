import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class RecordPaymentRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    payment_method: str = Field(..., description="CASH, CARD, TRANSFER, PAGO_MOVIL, ZELLE")
    reference: str | None = Field(default=None, max_length=64)
    notes: str | None = None


class PaymentRecordPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    appointment_id: str
    clinic_id: str
    amount: Decimal
    currency: str
    status: str
    payment_method: str | None = None
    reference: str | None = None
    notes: str | None = None
    paid_at: datetime.datetime | None = None
    created_at: datetime.datetime

    # Info contextual
    patient_name: str | None = None
    doctor_name: str | None = None


class CashierDailySummary(BaseModel):
    date: datetime.date
    clinic_id: str
    total_collected: Decimal
    currency: str = "USD"
    by_method: dict[str, Decimal]
    paid_count: int
    exempt_count: int
    void_count: int
    unpaid_count: int
