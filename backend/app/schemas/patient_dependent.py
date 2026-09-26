import datetime
from pydantic import BaseModel, ConfigDict, Field


class PatientDependentCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=128)
    relationship: str = Field(..., description="HIJO, PADRE, CONYUGE, HERMANO, OTRO")
    birth_date: datetime.date
    id_document: str | None = None
    gender: str | None = None

    # Datos clínicos basales
    blood_type: str | None = None
    height_cm: float | None = Field(None, ge=20, le=260)
    allergies: str | None = None
    chronic_conditions: str | None = None

    # Contacto adicional y observaciones
    email: str | None = None
    phone: str | None = None
    notes: str | None = None


class PatientDependentUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=128)
    relationship: str | None = None
    birth_date: datetime.date | None = None
    id_document: str | None = None
    gender: str | None = None

    blood_type: str | None = None
    height_cm: float | None = Field(None, ge=20, le=260)
    allergies: str | None = None
    chronic_conditions: str | None = None

    email: str | None = None
    phone: str | None = None
    notes: str | None = None


class PatientDependentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    guardian_user_id: str
    full_name: str
    relationship: str
    birth_date: datetime.date
    id_document: str | None = None
    gender: str | None = None
    emancipation_status: str
    is_emancipated: bool = False
    emancipated_at: datetime.datetime | None = None
    linked_user_id: str | None = None

    # Datos clínicos basales
    blood_type: str | None = None
    height_cm: float | None = None
    allergies: str | None = None
    chronic_conditions: str | None = None

    # Contacto, observaciones y foto
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    profile_picture_url: str | None = None
    age: int | None = None
    is_profile_complete: bool = False

    created_at: datetime.datetime
