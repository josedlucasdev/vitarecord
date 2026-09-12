"""Autenticacion: login, refresh (con rotacion y deteccion de reuso), logout
y perfil propio (plan/plan.md seccion 2.A y 2.B.9).

Pendiente para una iteracion posterior (no incluido aun): recuperacion de
contraseña por enlace firmado / OTP, gestion de sesiones activas listables
por el usuario, y setup/activacion de MFA TOTP para roles obligados.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    RefreshRequest,
    ResetPasswordRequest,
    SessionPublic,
    TokenPair,
    UserPublic,
)
from app.services.auth_service import AuthService

router = APIRouter()


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

