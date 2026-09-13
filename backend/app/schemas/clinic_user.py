from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, computed_field


ALLOWED_CLINIC_ROLES = ("CLINIC_ADMIN", "RECEPTIONIST", "PATIENT", "DOCTOR")
TENANT_ROLES = ("CLINIC_ADMIN", "RECEPTIONIST")
GLOBAL_ROLES = ("DOCTOR", "PATIENT")


class ClinicUserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: str | None = Field(None, max_length=32)
    role: str
    specialty: str | None = Field(None, max_length=100)
    license_number: str | None = Field(None, max_length=100)


class ClinicUserRoleUpdate(BaseModel):
    role: str


class ClinicUserPublic(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    phone: str | None = None
    role: str
    status: str
    clinic_id: str | None = None
    specialty: str | None = None
    license_number: str | None = None
    created_at: datetime | None = None

    @computed_field
    @property
    def is_tenant_user(self) -> bool:
        return self.role in TENANT_ROLES

    model_config = {"from_attributes": True}

