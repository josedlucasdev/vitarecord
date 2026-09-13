"""Autenticacion: login, refresh (con rotacion y deteccion de reuso), logout
y perfil propio (plan/plan.md seccion 2.A y 2.B.9).

Pendiente para una iteracion posterior (no incluido aun): recuperacion de
contraseña por enlace firmado / OTP, gestion de sesiones activas listables
por el usuario, y setup/activacion de MFA TOTP para roles obligados.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import decode_token, hash_password, is_token_type, verify_password
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.clinic_repository import ClinicRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    PatientOnboardingCompleteRequest,
    PatientOnboardingValidateResponse,
    RefreshRequest,
    ResetPasswordRequest,
    SessionPublic,
    TokenPair,
    UserPublic,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.get("/patient-onboarding/validate", response_model=PatientOnboardingValidateResponse)
async def validate_patient_onboarding_token(
    token: Annotated[str, Query()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Valida el token de invitación para el registro del paciente."""
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El enlace de registro no es válido o ha expirado.")

    if not is_token_type(payload, "patient_invitation"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tipo de token no válido.")

    user_id = payload.get("sub")
    user = await UserRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario paciente no encontrado.")

    appointment_id = payload.get("appointment_id")
    doctor_name = None
    clinic_name = None
    start_time_str = None

    if appointment_id:
        app = await AppointmentRepository(db).get_by_id(appointment_id)
        if app:
            doctor_name = app.doctor.full_name if app.doctor else None
            clinic_name = app.clinic.name if app.clinic else None
            start_time_str = app.start_time.strftime("%d/%m/%Y a las %H:%M")

    return PatientOnboardingValidateResponse(
        valid=True,
        email=user.email,
        full_name=user.full_name,
        doctor_name=doctor_name,
        clinic_name=clinic_name,
        appointment_id=appointment_id,
        start_time=start_time_str,
    )


@router.post("/patient-onboarding/complete", response_model=TokenPair)
async def complete_patient_onboarding(
    request: Request,
    payload: PatientOnboardingCompleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Fija la contraseña del paciente, activa su cuenta y emite sesión autenticada."""
    try:
        claims = decode_token(payload.token)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El enlace de registro no es válido o ha expirado.")

    if not is_token_type(claims, "patient_invitation"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tipo de token no válido.")

    user_id = claims.get("sub")
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paciente no encontrado.")

    if len(payload.password) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contraseña debe tener al menos 8 caracteres.")

    user.hashed_password = hash_password(payload.password)
    user.status = "ACTIVE"
    user.role = "PATIENT"
    await db.flush()

    service = AuthService(db)
    access_token, refresh_token = await service.issue_token_pair(
        user,
        device_info=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenPair)
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
    mfa_code: str | None = None,
):
    service = AuthService(db)
    user = await service.authenticate(form_data.username, form_data.password, mfa_code)
    access_token, refresh_token = await service.issue_token_pair(
        user,
        device_info=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    request: Request,
    payload: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthService(db)
    access_token, refresh_token = await service.refresh(
        payload.refresh_token,
        device_info=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=204)
async def logout(payload: RefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    await AuthService(db).logout(payload.refresh_token)


@router.get("/me", response_model=UserPublic)
async def me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Genera token firmado de recuperacion y envia correo (o simula si no existe)."""
    await AuthService(db).forgot_password(payload.email)
    return {
        "message": "Si el correo está registrado, recibirás un enlace de recuperación."
    }


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Restablece la contrasena a traves del token firmado."""
    await AuthService(db).reset_password(payload.token, payload.new_password)
    return {"message": "Contraseña actualizada exitosamente."}


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Permite al usuario autenticado cambiar su contraseña verificando la actual."""
    if not current_user.hashed_password or not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contraseña actual no es correcta.")

    if len(payload.new_password) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La nueva contraseña debe tener al menos 8 caracteres.")

    current_user.hashed_password = hash_password(payload.new_password)
    await db.commit()
    return {"message": "Contraseña actualizada exitosamente."}


@router.get("/sessions", response_model=list[SessionPublic])
async def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Lista las sesiones activas del usuario autenticado."""
    return await AuthService(db).list_sessions(current_user.id)


@router.delete("/sessions/{session_id}", status_code=204)
async def revoke_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Revoca una sesion especifica del usuario."""
    await AuthService(db).revoke_session(current_user.id, session_id)


@router.delete("/sessions", status_code=204)
async def revoke_all_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Revoca todas las sesiones activas del usuario."""
    await AuthService(db).revoke_all_sessions(current_user.id)

