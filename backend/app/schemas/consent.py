import datetime
from pydantic import BaseModel, ConfigDict, Field


class ConsentGrantCreate(BaseModel):
    granted_to_clinic_id: str
    scope: str = Field(default="READ_MEDICAL_RECORDS")
    granted_days: int = Field(default=30, ge=1, le=365)


class ConsentGrantPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    granted_to_clinic_id: str
    scope: str
    granted_at: datetime.datetime
    granted_until: datetime.datetime
    is_revoked: bool
