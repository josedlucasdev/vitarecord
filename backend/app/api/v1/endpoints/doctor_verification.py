"""Endpoints para revision y verificacion de matricula profesional medica (plan/plan.md seccion 2.B.2 y 2.B.8)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.doctor_verification import (
    DoctorPendingVerificationPublic,
    EmergencyAvailabilityToggleRequest,
    VerifyDoctorRequest,
    VerifyDoctorResponse,
)
from app.services.doctor_verification_service import DoctorVerificationService

router = APIRouter()


@router.get("/doctors/pending-verification", response_model=list[DoctorPendingVerificationPublic])
async def list_pending_doctors(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Lista los medicos con matricula pendiente de validacion (para SUPERADMIN / COMPLIANCE_REVIEWER)."""
    service = DoctorVerificationService(db)
    return await service.list_pending(current_user)


@router.post("/doctors/{doctor_id}/verify", response_model=VerifyDoctorResponse)
async def verify_doctor(
    doctor_id: str,
    payload: VerifyDoctorRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Aprueba o rechaza formalmente la matricula medica con registro inmutable en audit_logs."""
    service = DoctorVerificationService(db)
    return await service.verify_doctor(
        doctor_id=doctor_id,
        request=payload,
        reviewer=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/doctors/{doctor_id}/emergency-availability")
async def toggle_emergency_availability(
    doctor_id: str,
    payload: EmergencyAvailabilityToggleRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Activa o desactiva disponibilidad para emergencias. Requiere matricula VERIFIED."""
    service = DoctorVerificationService(db)
    return await service.toggle_emergency_availability(
        doctor_id=doctor_id,
        is_available=payload.is_available,
        current_user=current_user,
    )
