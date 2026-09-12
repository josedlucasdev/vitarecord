import datetime
from pydantic import BaseModel, ConfigDict, Field


class PatientDependentCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=128)
    relationship: str = Field(..., description="HIJO, PADRE, CONYUGE, OTRO")
    birth_date: datetime.date
    id_document: str | None = None
    gender: str | None = None


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
    created_at: datetime.datetime
