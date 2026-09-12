import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.core.acl import Permission
from app.core.database import get_db
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCancelRequest,
    AppointmentCreate,
    AppointmentPublic,
)
from app.services.appointment_service import AppointmentService

router = APIRouter()


@router.post(
    "",
    response_model=AppointmentPublic,
    status_code=status.HTTP_201_CREATED,
)
async def book_appointment(
    payload: AppointmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.APPOINTMENTS_BOOK))],
):
    """Reserva de cita médica con garantía de bloqueo pesimista contra solapamientos."""
    service = AppointmentService(db)
    return await service.book_appointment(payload, current_user)


@router.get("", response_model=list[AppointmentPublic])
async def list_appointments(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.APPOINTMENTS_MANAGE))],
    clinic_id: str | None = None,
    doctor_id: str | None = None,
    patient_id: str | None = None,
    date: datetime.date | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
):
    """Lista citas médicas aplicando filtros según los permisos del rol autenticado."""
    service = AppointmentService(db)
    return await service.list_appointments(
        current_user=current_user,
        clinic_id=clinic_id,
        doctor_id=doctor_id,
        patient_id=patient_id,
        date=date,
        status=status_filter,
    )


@router.post("/{appointment_id}/accept", response_model=AppointmentPublic)
async def accept_appointment(
    appointment_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Aceptación formal de la cita por parte del paciente."""
    service = AppointmentService(db)
    return await service.accept_appointment(appointment_id, current_user)


@router.post("/{appointment_id}/reject", response_model=AppointmentPublic)
async def reject_appointment(
    appointment_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Rechazo de cita por el paciente: libera el slot y el consultorio de inmediato."""
    service = AppointmentService(db)
    return await service.reject_appointment(appointment_id, current_user)


@router.post("/{appointment_id}/cancel", response_model=AppointmentPublic)
async def cancel_appointment(
    appointment_id: str,
    payload: AppointmentCancelRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.APPOINTMENTS_MANAGE))],
):
    """Cancelación oportuna de cita: libera el slot y actualiza el pago a VOID."""
    service = AppointmentService(db)
    return await service.cancel_appointment(appointment_id, payload.cancellation_reason, current_user)
