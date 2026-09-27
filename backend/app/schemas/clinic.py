from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, computed_field


class ClinicCreateRequest(BaseModel):
    name: str
    slug: str
    timezone: str = "America/Caracas"
    country_code: str = "VE"
    phone: str | None = None
    address: str | None = None
    ai_enabled: bool = False
    ai_api_url: str | None = None
    ai_api_key: str | None = None
    ai_model: str | None = "gpt-4o-mini"
    ai_consultation_assistant_enabled: bool = False
    logo_url: str | None = None


class ClinicUpdateRequest(BaseModel):
    name: str | None = None
    slug: str | None = None
    timezone: str | None = None
    country_code: str | None = None
    phone: str | None = None
    address: str | None = None
    is_active: bool | None = None
    ai_enabled: bool | None = None
    ai_api_url: str | None = None
    ai_api_key: str | None = None
    ai_model: str | None = None
    ai_consultation_assistant_enabled: bool | None = None
    require_mfa_for_receptionists: bool | None = None
    emergency_doctor_attempts: int | None = None
    emergency_backup_phone: str | None = None
    modules: dict[str, bool] | None = None
    logo_url: str | None = None


DEFAULT_CLINIC_MODULES: dict[str, bool] = {
    "ai_assistant": False,
    "ai_consultation": False,
    "emergencies": True,
    "cashier": True,
    "rooms": True,
    "prescriptions": True,
    "patient_portal": True,
    "require_mfa_for_receptionists": False,
}


class ClinicPublic(BaseModel):
    id: str
    name: str
    slug: str
    timezone: str
    country_code: str
    phone: str | None = None
    address: str | None = None
    is_active: bool
    require_mfa_for_receptionists: bool = False
    emergency_doctor_attempts: int = 2
    emergency_backup_phone: str | None = None
    ai_enabled: bool = False
    ai_api_url: str | None = None
    ai_api_key: str | None = Field(default=None, exclude=True)
    ai_model: str | None = "gpt-4o-mini"
    ai_consultation_assistant_enabled: bool = False
    modules: dict[str, bool] | None = None
    logo_url: str | None = None
    created_at: datetime | None = None

    @computed_field
    @property
    def has_ai_key(self) -> bool:
        return bool(self.ai_api_key and len(self.ai_api_key.strip()) > 0)

    @computed_field
    @property
    def active_modules(self) -> dict[str, bool]:
        base = dict(DEFAULT_CLINIC_MODULES)
        if self.modules and isinstance(self.modules, dict):
            base.update({k: bool(v) for k, v in self.modules.items()})
        base["ai_assistant"] = bool(self.ai_enabled)
        base["ai_consultation"] = bool(self.ai_consultation_assistant_enabled)
        base["require_mfa_for_receptionists"] = bool(self.require_mfa_for_receptionists)
        return base

    model_config = {"from_attributes": True}


class ClinicAISettingsUpdate(BaseModel):
    ai_enabled: bool
    ai_api_url: str | None = None
    ai_api_key: str | None = None
    ai_model: str | None = None
    ai_consultation_assistant_enabled: bool = False


class ClinicModulesUpdateRequest(BaseModel):
    modules: dict[str, bool] | None = None
    ai_enabled: bool | None = None
    ai_consultation_assistant_enabled: bool | None = None
    ai_api_url: str | None = None
    ai_api_key: str | None = None
    ai_model: str | None = None
    require_mfa_for_receptionists: bool | None = None
    emergency_doctor_attempts: int | None = None
    emergency_backup_phone: str | None = None



class ClinicAIModelsQueryRequest(BaseModel):
    clinic_id: str | None = None
    ai_api_url: str
    ai_api_key: str | None = None


class ClinicAIModelsQueryResponse(BaseModel):
    models: list[str]
    detected_provider: str | None = None


class ClinicSecurityPolicyUpdate(BaseModel):
    require_mfa_for_receptionists: bool


class ClinicDoctorPublic(BaseModel):
    id: str
    full_name: str | None = None
    email: str
    specialty: str | None = None
    specialties: list[str] = []
    is_available_for_emergencies: bool = False
    contract_type: str | None = "INDEPENDENT"
    consultation_fee: Decimal | None = None
    currency: str | None = "USD"

    model_config = {"from_attributes": True}


class AcademicDegree(BaseModel):
    title: str
    institution: str
    year: int | None = None
    license_or_id: str | None = None


class WorkExperience(BaseModel):
    position: str
    workplace: str
    start_year: int | None = None
    end_year: int | None = None
    description: str | None = None


class DoctorPublicWithClinics(BaseModel):
    id: str
    full_name: str | None = None
    email: str
    phone: str | None = None
    specialty: str | None = None
    specialties: list[str] = []
    biography: str | None = None
    profile_picture_url: str | None = None
    license_number: str | None = None
    license_verification_status: str = "VERIFIED"
    is_available_for_emergencies: bool = False
    is_public_profile_enabled: bool = True
    academic_degrees: list[AcademicDegree] = []
    work_experience: list[WorkExperience] = []
    clinics: list[ClinicPublic] = []

    model_config = {"from_attributes": True}


class DoctorProfileUpdateRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    specialty: str | None = None
    specialties: list[str] | None = None
    biography: str | None = None
    profile_picture_url: str | None = None
    academic_degrees: list[AcademicDegree] | None = None
    work_experience: list[WorkExperience] | None = None
    is_public_profile_enabled: bool | None = None


class DoctorSearchResult(BaseModel):
    id: str
    full_name: str | None = None
    email: str
    phone: str | None = None
    specialty: str | None = None
    specialties: list[str] = []
    identification_number: str | None = None
    license_number: str | None = None
    profile_picture_url: str | None = None
    license_verification_status: str = "NOT_APPLICABLE"
    is_already_affiliated: bool = False
    affiliation_status: str | None = None
    status: str = "ACTIVE"
    academic_degrees: list[AcademicDegree] = []
    work_experience: list[WorkExperience] = []
