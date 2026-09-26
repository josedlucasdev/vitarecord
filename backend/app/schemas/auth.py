from pydantic import BaseModel, EmailStr


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class FacebookLoginRequest(BaseModel):
    access_token: str


class GoogleLoginRequest(BaseModel):
    credential: str


class MFAVerifyRequest(BaseModel):
    email: EmailStr
    code: str


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None = None
    phone: str | None = None
    role: str
    status: str
    mfa_enabled: bool
    profile_picture_url: str | None = None
    recovery_email: str | None = None
    recovery_phone: str | None = None
    preferred_notification_channels: list[str] | None = None
    notification_preferences: dict | None = None
    clinic_id: str | None = None

    model_config = {"from_attributes": True}


class UserProfileUpdateRequest(BaseModel):
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None


class UserRecoveryMethodsResponse(BaseModel):
    recovery_email: str | None = None
    recovery_phone: str | None = None
    has_recovery_codes: bool = False
    recovery_codes_count: int = 0


class UserRecoveryMethodsUpdateRequest(BaseModel):
    recovery_email: EmailStr | None = None
    recovery_phone: str | None = None


class UserRecoveryCodesGenerateResponse(BaseModel):
    codes: list[str]
    message: str


class NotificationSettingsResponse(BaseModel):
    channels: list[str]
    categories: dict[str, dict[str, bool]]


class NotificationSettingsUpdateRequest(BaseModel):
    channels: list[str] | None = None
    categories: dict[str, dict[str, bool]] | None = None


class UserDeleteAccountRequest(BaseModel):
    password: str | None = None
    confirmation_phrase: str | None = None
    reason: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
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


class MFAStatusResponse(BaseModel):
    mfa_enabled: bool


class MFASetupResponse(BaseModel):
    secret: str
    otpauth_url: str
    qr_code: str


class MFAEnableRequest(BaseModel):
    secret: str
    code: str


class MFADisableRequest(BaseModel):
    password: str

