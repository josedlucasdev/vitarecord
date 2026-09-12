import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class PrescriptionItem(BaseModel):
    medication: str = Field(..., min_length=2, max_length=150)
    dosage: str = Field(..., min_length=1, max_length=50)
    frequency: str = Field(..., min_length=1, max_length=50)
    duration: str = Field(..., min_length=1, max_length=50)
    instructions: str | None = Field(default=None, max_length=255)


class PrescriptionCreate(BaseModel):
    items: list[PrescriptionItem] = Field(..., min_length=1)
    diagnosis_summary: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    duration_days: int = Field(default=30, ge=1, le=365)


class PrescriptionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    medical_record_id: str
    appointment_id: str
    clinic_id: str
    doctor_id: str
    patient_id: str
    dependent_id: str | None = None
    prescription_code: str
    verification_hash: str
    items: list[dict[str, Any]]
    diagnosis_summary: str | None = None
    notes: str | None = None
    issued_at: datetime.datetime
    expires_at: datetime.datetime
    status: str

    # Datos enriquecidos
    doctor_name: str | None = None
    doctor_specialty: str | None = None
    patient_name: str | None = None
    clinic_name: str | None = None


class PrescriptionVerificationPublic(BaseModel):
    """Payload seguro expuesto a farmacias via QR publico (sin PHI sensible)."""

    is_valid: bool
    prescription_code: str
    clinic_name: str
    doctor_name: str
    doctor_specialty: str | None = None
    doctor_license: str | None = None
    patient_name: str | None = "Paciente Titular"
    issued_at: datetime.datetime
    expires_at: datetime.datetime
    status: str
    diagnosis_summary: str | None = None
    items: list[dict[str, Any]]
