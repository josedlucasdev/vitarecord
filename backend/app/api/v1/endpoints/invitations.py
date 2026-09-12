"""Endpoints del ciclo de invitaciones de medicos a clinicas (plan/plan.md seccion 2.B.2)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.invitation import (
    CompleteOnboardingRequest,
    CreateInvitationRequest,
    InvitationResponse,
    RespondInvitationRequest,
    ValidateTokenResponse,
)
from app.services.invitation_service import InvitationService

router = APIRouter()


@router.post("/clinics/{clinic_id}/invitations", response_model=InvitationResponse)
async def invite_doctor(
    clinic_id: str,
    payload: CreateInvitationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Envia una invitacion a un medico para afiliarse a la clinica."""
    service = InvitationService(db)
    return await service.invite_doctor(clinic_id, payload, inviting_user=current_user)


@router.get("/invitations/validate", response_model=ValidateTokenResponse)
async def validate_invitation(
    token: Annotated[str, Query(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Valida la validez de un token de invitacion o onboarding."""
    service = InvitationService(db)
    return await service.validate_invitation_token(token)


@router.post("/invitations/respond")
async def respond_invitation(
    payload: RespondInvitationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Caso A: Medico con cuenta previa acepta o rechaza una invitacion de afiliacion."""
    service = InvitationService(db)
    return await service.respond_invitation(payload.token, payload.action)


@router.post("/invitations/onboarding")
async def complete_onboarding(
    payload: CompleteOnboardingRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Caso B: Medico nuevo define contrasena y perfil para completar su registro."""
    service = InvitationService(db)
    return await service.complete_onboarding(payload)
