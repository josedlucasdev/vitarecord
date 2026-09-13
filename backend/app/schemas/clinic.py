from datetime import datetime
from pydantic import BaseModel


class ClinicCreateRequest(BaseModel):
    name: str
    slug: str
    timezone: str = "America/Caracas"
    country_code: str = "VE"


class ClinicPublic(BaseModel):
    id: str
    name: str
    slug: str
    timezone: str
    country_code: str
    is_active: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ClinicDoctorPublic(BaseModel):
    id: str
    full_name: str | None = None
    email: str
    specialty: str | None = None
    is_available_for_emergencies: bool = False

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
    identification_number: str | None = None
    license_number: str | None = None
    profile_picture_url: str | None = None
    license_verification_status: str = "NOT_APPLICABLE"
    is_already_affiliated: bool = False
    affiliation_status: str | None = None
    status: str = "ACTIVE"
    academic_degrees: list[AcademicDegree] = []
    work_experience: list[WorkExperience] = []
