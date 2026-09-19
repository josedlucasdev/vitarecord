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
    PublicAppointmentCreate,
)
from app.schemas.procedure import AppointmentProcedureCreate
from app.services.appointment_service import AppointmentService


router = APIRouter()


@router.post(
    "/public-book",
    response_model=AppointmentPublic,
    status_code=status.HTTP_201_CREATED,
)
async def public_book_appointment(
    payload: PublicAppointmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Reserva de cita médica abierta al público general sin requerir inicio de sesión previo.
    
    Captura información de triage clínico y biométrico, dejando la cita en estado
    PENDING_DOCTOR_APPROVAL hasta ser aceptada por el especialista.
    """
    service = AppointmentService(db)
    return await service.public_book_appointment(payload)


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


@router.get("/{appointment_id}", response_model=AppointmentPublic)
async def get_appointment(
    appointment_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Obtiene el detalle de una cita médica por su identificador único."""
    service = AppointmentService(db)
    return await service.get_appointment(appointment_id, current_user)



@router.post("/{appointment_id}/doctor-accept", response_model=AppointmentPublic)
async def doctor_accept_appointment(
    appointment_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Aprobación de la cita médica por parte del doctor y envío de invitación por correo al paciente."""
    service = AppointmentService(db)
    return await service.doctor_accept_appointment(appointment_id, current_user)


@router.post("/{appointment_id}/doctor-reject", response_model=AppointmentPublic)
async def doctor_reject_appointment(
    appointment_id: str,
    payload: AppointmentCancelRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Rechazo justificado de cita por parte del doctor."""
    service = AppointmentService(db)
    return await service.doctor_reject_appointment(appointment_id, payload.cancellation_reason, current_user)


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


@router.post("/{appointment_id}/procedures", response_model=AppointmentPublic)
async def add_appointment_procedure(
    appointment_id: str,
    payload: AppointmentProcedureCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Agrega un procedimiento clínico realizado a una cita (en consulta médica) y recalcula la caja."""
    service = AppointmentService(db)
    return await service.add_procedure_to_appointment(appointment_id, payload, current_user)

