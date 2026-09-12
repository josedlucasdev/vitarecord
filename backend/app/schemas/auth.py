from pydantic import BaseModel, EmailStr


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class MFAVerifyRequest(BaseModel):
    email: EmailStr
    code: str


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    role: str
    status: str
    mfa_enabled: bool

    model_config = {"from_attributes": True}


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class SessionPublic(BaseModel):
    id: str
    device_info: str | None = None
    ip_address: str | None = None
    issued_at: str | None = None
    expires_at: str | None = None
    is_current: bool = False


class PatientOnboardingCompleteRequest(BaseModel):
    token: str
    password: str


class PatientOnboardingValidateResponse(BaseModel):
    valid: bool
    email: EmailStr
    full_name: str | None = None
    doctor_name: str | None = None
    clinic_name: str | None = None
    appointment_id: str | None = None
    start_time: str | None = None

