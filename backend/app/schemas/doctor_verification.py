from datetime import datetime
from pydantic import BaseModel, EmailStr


class DoctorPendingVerificationPublic(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None = None
    specialty: str | None = None
    license_number: str | None = None
    license_document_url: str | None = None
    license_verification_status: str
    status: str
    phone: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class VerifyDoctorRequest(BaseModel):
    action: str  # "APPROVE" | "REJECT"
    reason: str | None = None
    document_url: str | None = None


class VerifyDoctorResponse(BaseModel):
    doctor_id: str
    status: str
    license_verification_status: str
    action: str
    message: str


class EmergencyAvailabilityToggleRequest(BaseModel):
    is_available: bool
