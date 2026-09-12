"""Endpoints de agenda y disponibilidad medica con cache en Redis (plan/plan.md seccion 2.B.4)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.core.acl import Permission
from app.core.database import get_db
from app.models.user import User
from app.schemas.availability import (
    DoctorScheduleCreate,
    DoctorSchedulePublic,
    TimeSlotPublic,
)
from app.services.availability_service import AvailabilityService

router = APIRouter()


@router.get("/doctors/{doctor_id}/schedules", response_model=list[DoctorSchedulePublic])
async def get_doctor_schedules(
    doctor_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    clinic_id: str | None = None,
):
    """Consulta la configuracion semanal de atencion del medico."""
    service = AvailabilityService(db)
    return await service.get_doctor_schedules(doctor_id, clinic_id)


@router.post("/doctors/{doctor_id}/schedules", response_model=list[DoctorSchedulePublic])
async def set_doctor_schedules(
    doctor_id: str,
    payload: DoctorScheduleCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.DOCTORS_SCHEDULE_MANAGE))],
):
    """Configura o reemplaza los bloques de horario del medico en una clinica."""
    service = AvailabilityService(db)
    return await service.set_doctor_schedules(doctor_id, payload, current_user)


@router.get(
    "/clinics/{clinic_id}/doctors/{doctor_id}/slots",
    response_model=list[TimeSlotPublic],
)
async def get_available_slots(
    clinic_id: str,
    doctor_id: str,
    date: Annotated[str, Query(..., description="Fecha en formato YYYY-MM-DD")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Calcula slots libres para agendamiento, utilizando cache en Redis para lectura ultrarrapida."""
    service = AvailabilityService(db)
    return await service.calculate_available_slots(clinic_id, doctor_id, date)
