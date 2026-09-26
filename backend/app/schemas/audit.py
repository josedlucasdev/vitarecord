from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class AuditLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    clinic_id: str | None = None
    user_id: str | None = None
    action: str
    entity_type: str
    entity_id: str
    details: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime


class AuditLogPaginationResponse(BaseModel):
    items: list[AuditLogPublic]
    total: int
    limit: int
    offset: int
