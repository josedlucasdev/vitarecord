"""Esquemas Pydantic para el perfil clínico y personal del paciente."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PatientProfilePublic(BaseModel):
    """Representación pública del perfil completo del paciente."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str | None = None
    phone: str | None = None
    role: str
    status: str
    profile_picture_url: str | None = None

    # Datos demográficos
    identification_number: str | None = None
    birth_date: datetime | str | None = None
    gender: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = "Venezuela"

    # Datos clínicos permanentes / basales
    blood_type: str | None = None
    height_cm: float | None = None
    allergies: str | None = None
    chronic_conditions: str | None = None

    # Contacto de emergencia
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    emergency_contact_relationship: str | None = None

    # Indicador de completitud clínica
    is_profile_complete: bool = False


class PatientProfileUpdateRequest(BaseModel):
    """Payload para actualizar el perfil personal y clínico del paciente."""

    full_name: str | None = Field(None, min_length=2, max_length=255)
    phone: str | None = Field(None, max_length=32)
    identification_number: str | None = Field(None, max_length=32)
    birth_date: str | None = Field(None, description="Fecha de nacimiento en formato YYYY-MM-DD")
    gender: str | None = Field(None, max_length=16)
    address: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    country: str | None = Field("Venezuela", max_length=100)

    # Datos clínicos basales
    blood_type: str | None = Field(None, max_length=10)
    height_cm: float | None = Field(None, ge=30, le=260)
    allergies: str | None = Field(None, max_length=500)
    chronic_conditions: str | None = Field(None, max_length=500)

    # Contacto de emergencia
    emergency_contact_name: str | None = Field(None, max_length=255)
    emergency_contact_phone: str | None = Field(None, max_length=32)
    emergency_contact_relationship: str | None = Field(None, max_length=100)
