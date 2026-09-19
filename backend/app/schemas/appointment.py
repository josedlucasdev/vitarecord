import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.procedure import AppointmentProcedurePublic


class PatientIntakeData(BaseModel):
    """Datos de triage clinico, medidas biometricas y antecedentes reportados por el paciente."""
    height_cm: float | None = Field(None, ge=30, le=260, description="Estatura en centímetros")
    weight_kg: float | None = Field(None, ge=1, le=400, description="Peso en kilogramos")
    bmi: float | None = Field(None, description="Índice de masa corporal calculado")
    bmi_category: str | None = Field(None, description="Categoría de IMC: Bajo peso, Normal, Sobrepeso, Obesidad")
    blood_type: str | None = Field(None, max_length=10, description="Grupo sanguíneo (ej. O+, A+, B-)")
    allergies: str | None = Field(None, max_length=500, description="Alergias a medicamentos o sustancias")
    chronic_conditions: str | None = Field(None, max_length=500, description="Enfermedades crónicas o antecedentes patológicos")
    current_medications: str | None = Field(None, max_length=500, description="Medicamentos de consumo habitual")
    symptoms: str | None = Field(None, max_length=1000, description="Síntomas o motivo detallado de la consulta")
    address: str | None = Field(None, max_length=255, description="Dirección de habitación")
    city: str | None = Field(None, max_length=100, description="Ciudad o estado")
    country: str | None = Field("Venezuela", max_length=100, description="País")
    id_document: str | None = Field(None, max_length=32, description="Cédula o documento de identidad")
    birth_date: str | None = Field(None, description="Fecha de nacimiento en formato YYYY-MM-DD")
    gender: str | None = Field(None, max_length=16, description="Sexo biológico")


class PublicAppointmentCreate(BaseModel):
    """Payload para solicitud de cita médica pública sin inicio de sesión previo."""
    clinic_id: str
    doctor_id: str
    room_id: str | None = None
    start_time: datetime.datetime
    end_time: datetime.datetime

    # Datos personales del paciente
    full_name: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    phone: str = Field(..., min_length=7, max_length=32)
    id_document: str | None = Field(None, max_length=32)
    birth_date: str | None = None
    gender: str | None = None

    # Dirección simplificada
    country: str = Field(default="Venezuela", max_length=100)
    city: str | None = Field(None, max_length=100)
    address: str | None = Field(None, max_length=255)

    # Medidas biométricas y triage clínico
    height_cm: float | None = None
    weight_kg: float | None = None
    bmi: float | None = None
    blood_type: str | None = None
    allergies: str | None = None
    chronic_conditions: str | None = None
    current_medications: str | None = None
    reason: str | None = Field(None, max_length=255)

    estimated_amount: Decimal = Field(default=Decimal("30.00"), ge=0)
    currency: str = Field(default="USD", max_length=8)
    procedure_ids: list[str] = Field(default_factory=list)


class AppointmentCreate(BaseModel):
    clinic_id: str
    doctor_id: str
    patient_id: str | None = None  # Si es null, se asigna al usuario autenticado
    dependent_id: str | None = None
    room_id: str | None = None
    start_time: datetime.datetime
    end_time: datetime.datetime
    reason: str | None = None
    intake_data: dict | None = None
    estimated_amount: Decimal = Field(default=Decimal("30.00"), ge=0)
    currency: str = Field(default="USD", max_length=8)
    procedure_ids: list[str] = Field(default_factory=list)


class AppointmentCancelRequest(BaseModel):
    cancellation_reason: str = Field(..., min_length=3, max_length=255)


class AppointmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    clinic_id: str
    doctor_id: str
    patient_id: str
    dependent_id: str | None = None
    room_id: str | None = None
    start_time: datetime.datetime
    end_time: datetime.datetime
    status: str
    reason: str | None = None
    cancellation_reason: str | None = None
    intake_data: dict | None = None

    # Campos enriquecidos para la UI
    doctor_name: str | None = None
    patient_name: str | None = None
    patient_email: str | None = None
    patient_phone: str | None = None
    clinic_name: str | None = None
    room_name: str | None = None
    payment_status: str | None = None
    payment_amount: Decimal | None = None
    payment_method: str | None = None
    currency: str | None = None
    consultation_fee: Decimal | None = None
    procedures: list["AppointmentProcedurePublic"] = Field(default_factory=list)

    created_at: datetime.datetime

