from pydantic import BaseModel, EmailStr


class CreateInvitationRequest(BaseModel):
    email: EmailStr
    phone: str | None = None
    full_name: str | None = None
    specialty: str | None = None
    specialties: list[str] | None = None


class InvitationResponse(BaseModel):
    affiliation_id: str
    doctor_id: str
    clinic_id: str
    status: str
    is_new_user: bool
    invitation_link: str | None = None
    expires_at: str | None = None


class ValidateTokenResponse(BaseModel):
    valid: bool
    is_new_user: bool
    clinic_name: str
    clinic_id: str
    doctor_email: str
    doctor_id: str
    full_name: str | None = None
    specialty: str | None = None
    specialties: list[str] = []


class RespondInvitationRequest(BaseModel):
    token: str
    action: str  # "ACCEPT" | "REJECT"


class CompleteOnboardingRequest(BaseModel):
    token: str
    password: str
    full_name: str | None = None
    license_number: str | None = None
    specialty: str | None = None
    specialties: list[str] | None = None
    biography: str | None = None
    is_available_for_emergencies: bool = False
