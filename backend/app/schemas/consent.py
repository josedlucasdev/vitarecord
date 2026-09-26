import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ConsentScope = Literal["READ_MEDICAL_RECORDS"]


class ConsentGrantCreate(BaseModel):
    granted_to_clinic_id: str
    scope: ConsentScope = "READ_MEDICAL_RECORDS"
    granted_days: int = Field(default=30, ge=1, le=365)


class ConsentGrantPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    granted_to_clinic_id: str
    clinic_name: str | None = None
    scope: str
    granted_at: datetime.datetime
    granted_until: datetime.datetime
    is_revoked: bool
    revoked_at: datetime.datetime | None = None
    # ACTIVE, REVOKED o EXPIRED (calculado)
    status: str = "ACTIVE"
