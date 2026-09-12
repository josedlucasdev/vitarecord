from pydantic import BaseModel


class ClinicRoomCreate(BaseModel):
    name: str
    room_number: str | None = None
    description: str | None = None


class ClinicRoomUpdate(BaseModel):
    name: str | None = None
    room_number: str | None = None
    description: str | None = None
    is_active: bool | None = None


class ClinicRoomPublic(BaseModel):
    id: str
    clinic_id: str
    name: str
    room_number: str | None = None
    description: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}
