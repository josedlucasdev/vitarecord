from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class MedicalProcedurePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    clinic_id: str
    doctor_id: str | None = None
    name: str
    description: str | None = None
    price: Decimal
    currency: str = "USD"
    duration_minutes: int = 15
    category: str | None = None
    is_active: bool = True
    created_at: datetime | None = None


class MedicalProcedureCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: str | None = Field(None, max_length=255)
    price: Decimal = Field(..., ge=0)
    currency: str = Field("USD", max_length=8)
    duration_minutes: int = Field(15, ge=5, le=480)
    category: str | None = Field(None, max_length=64)
    is_active: bool = True


class MedicalProcedureUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    description: str | None = Field(None, max_length=255)
    price: Decimal | None = Field(None, ge=0)
    currency: str | None = Field(None, max_length=8)
    duration_minutes: int | None = Field(None, ge=5, le=480)
    category: str | None = Field(None, max_length=64)
    is_active: bool | None = None


class AppointmentProcedurePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    appointment_id: str
    procedure_id: str | None = None
    name: str
    price: Decimal
    currency: str = "USD"
    notes: str | None = None


class AppointmentProcedureCreate(BaseModel):
    procedure_id: str | None = None
    name: str | None = None
    price: Decimal | None = Field(None, ge=0)
    currency: str = "USD"
    notes: str | None = None


class DoctorAffiliationPricingPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    clinic_id: str
    clinic_name: str
    contract_type: str  # 'EMPLOYED' | 'INDEPENDENT'
    consultation_fee: Decimal
    currency: str = "USD"
    can_edit_fee: bool = False


class DoctorAffiliationPricingUpdate(BaseModel):
    consultation_fee: Decimal = Field(..., ge=0)
    currency: str = Field("USD", max_length=8)


class ClinicDoctorContractUpdate(BaseModel):
    contract_type: str = Field(..., pattern="^(EMPLOYED|INDEPENDENT)$")
    consultation_fee: Decimal = Field(..., ge=0)
    currency: str = Field("USD", max_length=8)
