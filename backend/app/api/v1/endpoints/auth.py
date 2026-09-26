"""Autenticacion: login, refresh (con rotacion y deteccion de reuso), logout
y perfil propio (plan/plan.md seccion 2.A y 2.B.9).

Incluye recuperacion de contraseña, gestion de sesiones, MFA TOTP (obligatorio
por rol, ver app.api.deps.get_current_user) y proteccion contra fuerza bruta
en el login (app.core.login_guard).
"""

import base64
import io
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordRequestForm
import httpx
import pyotp
import qrcode
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_user_allow_mfa_setup
from app.core import login_guard
from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token, generate_totp_secret, hash_password, is_token_type, verify_password, verify_totp
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.clinic_repository import ClinicRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    FacebookLoginRequest,
    ForgotPasswordRequest,
    GoogleLoginRequest,
    MFADisableRequest,
    MFAEnableRequest,
    MFASetupResponse,
    MFAStatusResponse,
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


@router.get("/mfa-status", response_model=MFAStatusResponse, summary="Verifica si un usuario tiene MFA activo para el login")
async def get_mfa_status(
    email: Annotated[str, Query()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retorna si el usuario tiene MFA activado sin revelar más información."""
    clean_email = email.strip().lower()
    user = await UserRepository(db).get_by_email(clean_email)
    if not user:
        return MFAStatusResponse(mfa_enabled=False)
    return MFAStatusResponse(mfa_enabled=bool(user.mfa_enabled and user.mfa_secret))


@router.post("/login", response_model=TokenPair)
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
    mfa_code: str | None = None,
):
    # Si mfa_code no vino en query params, extraerlo del form body si existe
    if not mfa_code:
        try:
            form = await request.form()
            mfa_code = form.get("mfa_code")
        except Exception:
            pass

    client_ip = request.client.host if request.client else None
    captcha_token = None
    try:
        form = await request.form()
        captcha_token = form.get("captcha_token")
    except Exception:
        pass

    # Backoff exponencial, bloqueo temporal y CAPTCHA (plan 2.B.9).
    await login_guard.check_login_allowed(form_data.username, client_ip, captcha_token)

    service = AuthService(db)
    try:
        user = await service.authenticate(form_data.username, form_data.password, mfa_code)
    except HTTPException as exc:
        # Pedir el codigo MFA (sin haberlo enviado) no es un intento fallido.
        is_mfa_prompt = str(exc.detail).startswith("MFA_REQUIRED")
        if exc.status_code == status.HTTP_401_UNAUTHORIZED and not is_mfa_prompt:
            await login_guard.register_login_failure(form_data.username, client_ip)
        raise
    await login_guard.register_login_success(form_data.username)

    access_token, refresh_token = await service.issue_token_pair(
        user,
        device_info=request.headers.get("user-agent"),
        ip_address=client_ip,
    )
    await db.commit()
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/facebook", response_model=TokenPair, summary="Iniciar sesión o registrar paciente con Facebook")
async def login_with_facebook(
    request: Request,
    payload: FacebookLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Autenticación y registro automático de pacientes mediante Facebook Login."""
    token = payload.access_token.strip()
    picture_url = None

    if settings.ALLOW_DEV_SOCIAL_LOGIN and token.startswith("dev_fb_"):
        # Emulación para pruebas automatizadas y desarrollo local
        fb_id = token.replace("dev_fb_", "")
        email = f"paciente_fb_{fb_id[:8]}@example.com"
        name = "Paciente Facebook"
    else:
        url = f"https://graph.facebook.com/me?fields=id,name,email,picture.type(large)&access_token={token}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url)
                if res.status_code != 200:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token de Facebook inválido o expirado.")
                fb_data = res.json()
                fb_id = fb_data.get("id")
                name = fb_data.get("name", "Paciente Facebook")
                email = fb_data.get("email") or f"fb_{fb_id}@facebook.intimasalud.com"
                picture_url = fb_data.get("picture", {}).get("data", {}).get("url")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Error conectando con Meta Graph API: {exc}")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(email)

    if not user:
        # Registrar paciente automáticamente
        user = User(
            email=email,
            full_name=name,
            role="PATIENT",
            status="ACTIVE",
            profile_picture_url=picture_url,
            preferred_notification_channels=["PUSH", "WHATSAPP", "EMAIL"],
        )
        db.add(user)
        await db.flush()
    else:
        if picture_url and not user.profile_picture_url:
            user.profile_picture_url = picture_url
            await db.flush()

    service = AuthService(db)
    access_token, refresh_token = await service.issue_token_pair(
        user,
        device_info=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/google", response_model=TokenPair, summary="Iniciar sesión o registrar paciente con Google")
async def login_with_google(
    request: Request,
    payload: GoogleLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Autenticación y registro automático de pacientes mediante Google Identity Services."""
    credential = payload.credential.strip()
    picture_url = None

    if settings.ALLOW_DEV_SOCIAL_LOGIN and credential.startswith("dev_google_"):
        # Emulación para pruebas automatizadas y desarrollo local
        google_sub = credential.replace("dev_google_", "")
        email = f"paciente_google_{google_sub[:8]}@example.com"
        name = "Paciente Google"
    else:
        # Verificación directa de Google ID Token con Google OAuth2 TokenInfo API
        url = f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url)
                if res.status_code != 200:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token de Google inválido o expirado.")
                google_data = res.json()
                if settings.GOOGLE_CLIENT_ID and google_data.get("aud") != settings.GOOGLE_CLIENT_ID:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "El token de Google no corresponde a esta aplicación.")
                email = google_data.get("email")
                if not email:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "El token de Google no contiene un correo electrónico válido.")
                name = google_data.get("name") or google_data.get("given_name") or "Paciente Google"
                picture_url = google_data.get("picture")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Error conectando con Google Auth API: {exc}")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(email)

    if not user:
        # Registrar paciente automáticamente
        user = User(
            email=email,
            full_name=name,
            role="PATIENT",
            status="ACTIVE",
            profile_picture_url=picture_url,
            preferred_notification_channels=["PUSH", "WHATSAPP", "EMAIL"],
        )
        db.add(user)
        await db.flush()
    else:
        if picture_url and not user.profile_picture_url:
            user.profile_picture_url = picture_url
            await db.flush()

    service = AuthService(db)
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
async def me(current_user: Annotated[User, Depends(get_current_user_allow_mfa_setup)]):
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
    current_user: Annotated[User, Depends(get_current_user_allow_mfa_setup)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Lista las sesiones activas del usuario autenticado."""
    return await AuthService(db).list_sessions(current_user.id)


@router.delete("/sessions/{session_id}", status_code=204)
async def revoke_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user_allow_mfa_setup)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Revoca una sesion especifica del usuario."""
    await AuthService(db).revoke_session(current_user.id, session_id)


@router.delete("/sessions", status_code=204)
async def revoke_all_sessions(
    current_user: Annotated[User, Depends(get_current_user_allow_mfa_setup)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Revoca todas las sesiones activas del usuario."""
    await AuthService(db).revoke_all_sessions(current_user.id)


@router.get("/mfa/status", response_model=MFAStatusResponse, summary="Estado actual de MFA del usuario autenticado")
async def get_my_mfa_status(
    current_user: Annotated[User, Depends(get_current_user_allow_mfa_setup)],
):
    """Verifica si el usuario autenticado tiene habilitado el segundo factor."""
    return MFAStatusResponse(mfa_enabled=bool(current_user.mfa_enabled and current_user.mfa_secret))


@router.post("/mfa/setup", response_model=MFASetupResponse, summary="Genera clave secreta y código QR para Google Authenticator")
async def setup_mfa(
    current_user: Annotated[User, Depends(get_current_user_allow_mfa_setup)],
):
    """Genera secreto TOTP Base32 y código QR PNG en base64 para escanear con Google Authenticator."""
    secret = generate_totp_secret()
    totp = pyotp.TOTP(secret)
    otpauth_url = totp.provisioning_uri(name=current_user.email, issuer_name="VitaRecord")

    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(otpauth_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"

    return MFASetupResponse(
        secret=secret,
        otpauth_url=otpauth_url,
        qr_code=qr_base64,
    )


@router.post("/mfa/enable", summary="Verifica el primer código y activa MFA para el usuario")
async def enable_mfa(
    payload: MFAEnableRequest,
    current_user: Annotated[User, Depends(get_current_user_allow_mfa_setup)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Valida el código de 6 dígitos con el secreto generado y activa el segundo factor."""
    if not payload.secret or not payload.code:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Se requiere la clave secreta y el código de verificación.")

    clean_code = payload.code.strip().replace(" ", "").replace("-", "")
    if not verify_totp(payload.secret, clean_code):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "El código ingresado es incorrecto o ha expirado. Verifica que la hora de tu dispositivo esté sincronizada.",
        )

    current_user.mfa_enabled = True
    current_user.mfa_secret = payload.secret
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    import logging
    logging.getLogger("auth").info("MFA activado con éxito para usuario %s (%s)", current_user.email, current_user.id)
    return {"message": "Autenticación de segundo factor (Google Authenticator) activada exitosamente."}


@router.post("/mfa/disable", summary="Desactiva MFA para el usuario previa comprobación de contraseña")
async def disable_mfa(
    payload: MFADisableRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Desactiva el segundo factor solicitando la contraseña del usuario por seguridad."""
    from app.api.deps import user_requires_mfa

    if user_requires_mfa(current_user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Su rol exige autenticación de dos factores; no es posible desactivarla.",
        )
    if not current_user.hashed_password or not verify_password(payload.password, current_user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contraseña ingresada no es correcta.")

    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    await db.commit()
    return {"message": "Autenticación de segundo factor desactivada exitosamente."}


