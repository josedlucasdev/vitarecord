import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.prescription import PrescriptionCreate, PrescriptionPublic


class MedicalAttachmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_name: str
    content_type: str
    file_size: int
    download_url: str | None = None


class MedicalRecordCreate(BaseModel):
    appointment_id: str
    anamnesis: str = Field(..., min_length=5, description="Motivo de consulta y antecedentes (se cifra con AES-256-GCM)")
    physical_exam: str | None = Field(default=None, description="Signos vitales y exploracion fisica")
    diagnosis: str = Field(..., min_length=3, description="Diagnostico clinico detallado")
    plan: str = Field(..., min_length=3, description="Conducta medica y plan terapeutico")
    icd10_code: str | None = Field(default=None, max_length=16, description="Codigo CIE-10/ICD-10")
    icd10_description: str | None = Field(default=None, max_length=255)
    prescription: PrescriptionCreate | None = None


class MedicalRecordPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    appointment_id: str
    clinic_id: str
    doctor_id: str
    patient_id: str
    dependent_id: str | None = None
    anamnesis: str
    physical_exam: str | None = None
    diagnosis: str
    plan: str
    icd10_code: str | None = None
    icd10_description: str | None = None
    encryption_key_version: int
    status: str
    created_at: datetime.datetime

    # Datos enriquecidos
    doctor_name: str | None = None
    doctor_specialty: str | None = None
    patient_name: str | None = None
    clinic_name: str | None = None
    prescriptions: list[PrescriptionPublic] = []
    attachments: list[MedicalAttachmentPublic] = []
