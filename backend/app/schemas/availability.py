from pydantic import BaseModel, Field


class DoctorScheduleBlock(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="0=Lunes, 6=Domingo")
    start_time: str = Field(..., description="Formato HH:MM, ej. 08:00")
    end_time: str = Field(..., description="Formato HH:MM, ej. 13:00")
    slot_duration_minutes: int = Field(30, ge=10, le=180)


class DoctorScheduleCreate(BaseModel):
    clinic_id: str
    blocks: list[DoctorScheduleBlock]


class DoctorSchedulePublic(BaseModel):
    id: str
    doctor_id: str
    clinic_id: str
    day_of_week: int
    start_time: str
    end_time: str
    slot_duration_minutes: int
    is_active: bool

    model_config = {"from_attributes": True}


class TimeSlotPublic(BaseModel):
    start_time: str
    end_time: str
    is_available: bool
    clinic_id: str
    doctor_id: str
    room_id: str | None = None
