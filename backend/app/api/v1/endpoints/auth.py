"""Autenticacion: login, refresh (con rotacion y deteccion de reuso), logout
y perfil propio (plan/plan.md seccion 2.A y 2.B.9).

Incluye recuperacion de contraseña, gestion de sesiones, MFA TOTP (obligatorio
por rol, ver app.api.deps.get_current_user) y proteccion contra fuerza bruta
en el login (app.core.login_guard).
"""

import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordRequestForm
import httpx
import pyotp
import qrcode
from sqlalchemy import func, or_, select
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
    NotificationSettingsResponse,
    NotificationSettingsUpdateRequest,
    PatientOnboardingCompleteRequest,
    PatientOnboardingValidateResponse,
    RefreshRequest,
    ResetPasswordRequest,
    SessionPublic,
    TokenPair,
    UserDeleteAccountRequest,
    UserProfileUpdateRequest,
    UserPublic,
    UserRecoveryCodesGenerateResponse,
    UserRecoveryMethodsResponse,
    UserRecoveryMethodsUpdateRequest,
)
from app.services.auth_service import AuthService
from app.services.storage_service import storage_service

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


DEFAULT_NOTIFICATION_CATEGORIES = {
    "appointments": {"email": True, "push": True, "whatsapp": True},
    "emergencies": {"email": True, "push": True, "whatsapp": True},
    "clinical_records": {"email": True, "push": True, "whatsapp": False},
    "security": {"email": True, "push": True, "whatsapp": False},
    "announcements": {"email": True, "push": False, "whatsapp": False},
}


@router.put("/me", response_model=UserPublic, summary="Actualizar perfil de usuario")
async def update_my_profile(
    payload: UserProfileUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user_allow_mfa_setup)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Actualiza datos básicos del usuario autenticado (nombre, apellido, email, teléfono)."""
    if payload.email and payload.email.lower() != current_user.email.lower():
        existing = await UserRepository(db).get_by_email(payload.email.lower())
        if existing and existing.id != current_user.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "El correo electrónico ya está registrado por otro usuario.")
        current_user.email = payload.email.lower()

    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip() or None
    elif payload.first_name is not None or payload.last_name is not None:
        first = (payload.first_name or "").strip()
        last = (payload.last_name or "").strip()
        combined = f"{first} {last}".strip()
        if combined:
            current_user.full_name = combined

    if payload.phone is not None:
        current_user.phone = payload.phone.strip() or None

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/me/avatar", summary="Subir avatar o foto de perfil")
async def upload_my_user_avatar(
    current_user: Annotated[User, Depends(get_current_user_allow_mfa_setup)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
):
    """Sube y almacena la fotografía de perfil de cualquier usuario autenticado."""
    allowed_types = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/jpg": "jpg"}
    content_type = (file.content_type or "").lower()
    if content_type not in allowed_types:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Formato de imagen no admitido. Se permite únicamente JPG, PNG o WEBP.",
        )

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La imagen no debe superar los 5 MB de tamaño.")

    from app.core.image_processing import sanitize_image_exif
    content, content_type = sanitize_image_exif(content, original_content_type=content_type, max_dimension=1024)
    ext = allowed_types.get(content_type, "png")
    s3_key = storage_service.build_avatar_key("users", current_user.id, ext)

    for other_ext in ("jpg", "png", "webp", "jpeg"):
        if other_ext != ext:
            storage_service.delete_file(storage_service.build_avatar_key("users", current_user.id, other_ext))

    storage_service.upload_file(content=content, s3_key=s3_key, content_type=content_type)
    avatar_url = f"/api/v1/auth/users/{current_user.id}/avatar"
    current_user.profile_picture_url = avatar_url
    await db.commit()
    await db.refresh(current_user)

    return {"profile_picture_url": avatar_url}


@router.delete("/me/avatar", summary="Eliminar avatar de perfil")
async def delete_my_user_avatar(
    current_user: Annotated[User, Depends(get_current_user_allow_mfa_setup)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Elimina la foto de perfil del usuario y restaura el avatar por defecto."""
    for entity in ("users", "patients", "doctors"):
        for ext in ("jpg", "png", "webp", "jpeg"):
            storage_service.delete_file(storage_service.build_avatar_key(entity, current_user.id, ext))

    current_user.profile_picture_url = None
    await db.commit()
    return {"message": "Foto de perfil eliminada correctamente."}


@router.api_route("/users/{user_id}/avatar", methods=["GET", "HEAD"], summary="Servir avatar de usuario")
async def get_user_avatar(user_id: str):
    """Sirve la foto de perfil del usuario desde Cloudflare R2 / almacenamiento."""
    for entity in ("users", "patients", "doctors"):
        for ext in ("jpg", "png", "webp", "jpeg"):
            s3_key = storage_service.build_avatar_key(entity, user_id, ext)
            res = storage_service.get_file(s3_key)
            if res:
                file_bytes, mime = res
                return Response(content=file_bytes, media_type=mime, headers={"Cache-Control": "public, max-age=86400"})

    from pathlib import Path
    from fastapi.responses import FileResponse
    for prefix in (f"user_{user_id}", f"patient_{user_id}", f"doctor_{user_id}"):
        matches = list(Path("uploads/avatars").glob(f"{prefix}.*"))
        if matches:
            fp = matches[0]
            media_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
            return FileResponse(fp, media_type=media_types.get(fp.suffix.lower(), "image/jpeg"))

    raise HTTPException(status.HTTP_404_NOT_FOUND, "Fotografía no encontrada.")


@router.get("/recovery-methods", response_model=UserRecoveryMethodsResponse, summary="Consultar métodos de recuperación")
async def get_recovery_methods(
    current_user: Annotated[User, Depends(get_current_user_allow_mfa_setup)],
):
    """Consulta métodos de recuperación configurados (email secundario, teléfono y códigos de respaldo)."""
    has_codes = bool(current_user.mfa_recovery_codes_hash)
    count = 0
    if current_user.mfa_recovery_codes_hash:
        try:
            parsed = json.loads(current_user.mfa_recovery_codes_hash)
            count = len(parsed) if isinstance(parsed, list) else 1
        except Exception:
            count = 1

    return UserRecoveryMethodsResponse(
        recovery_email=current_user.recovery_email,
        recovery_phone=current_user.recovery_phone,
        has_recovery_codes=has_codes,
        recovery_codes_count=count,
    )


@router.put("/recovery-methods", response_model=UserRecoveryMethodsResponse, summary="Configurar métodos de recuperación")
async def update_recovery_methods(
    payload: UserRecoveryMethodsUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user_allow_mfa_setup)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Permite fijar o actualizar correo secundario de recuperación y teléfono."""
    if payload.recovery_email is not None:
        current_user.recovery_email = str(payload.recovery_email).strip().lower() or None
    if payload.recovery_phone is not None:
        current_user.recovery_phone = payload.recovery_phone.strip() or None

    await db.commit()
    await db.refresh(current_user)

    has_codes = bool(current_user.mfa_recovery_codes_hash)
    count = 0
    if current_user.mfa_recovery_codes_hash:
        try:
            parsed = json.loads(current_user.mfa_recovery_codes_hash)
            count = len(parsed) if isinstance(parsed, list) else 1
        except Exception:
            count = 1

    return UserRecoveryMethodsResponse(
        recovery_email=current_user.recovery_email,
        recovery_phone=current_user.recovery_phone,
        has_recovery_codes=has_codes,
        recovery_codes_count=count,
    )


@router.post("/recovery-codes/generate", response_model=UserRecoveryCodesGenerateResponse, summary="Generar códigos de respaldo de emergencia")
async def generate_recovery_codes(
    current_user: Annotated[User, Depends(get_current_user_allow_mfa_setup)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Genera 8 códigos de respaldo únicos para recuperación segura de cuenta."""
    raw_codes = []
    hashed_codes = []
    for _ in range(8):
        part1 = secrets.token_hex(2).upper()
        part2 = secrets.token_hex(2).upper()
        code = f"{part1}-{part2}"
        raw_codes.append(code)
        hashed_codes.append(hashlib.sha256(code.encode()).hexdigest())

    current_user.mfa_recovery_codes_hash = json.dumps(hashed_codes)
    await db.commit()

    return UserRecoveryCodesGenerateResponse(
        codes=raw_codes,
        message="Guarda estos códigos en un lugar seguro. Solo se mostrarán una vez.",
    )


@router.get("/notification-settings", response_model=NotificationSettingsResponse, summary="Consultar configuración granular de alertas")
async def get_notification_settings(
    current_user: Annotated[User, Depends(get_current_user_allow_mfa_setup)],
):
    """Consulta canales preferidos y configuración por categorías (citas, urgencias, etc.)."""
    channels = current_user.preferred_notification_channels or ["PUSH", "WHATSAPP", "EMAIL"]
    categories = {k: dict(v) for k, v in DEFAULT_NOTIFICATION_CATEGORIES.items()}
    if current_user.notification_preferences and isinstance(current_user.notification_preferences, dict):
        for k, v in current_user.notification_preferences.items():
            if k in categories and isinstance(v, dict):
                categories[k] = {**categories[k], **v}
            elif isinstance(v, dict):
                categories[k] = v

    return NotificationSettingsResponse(channels=channels, categories=categories)


@router.put("/notification-settings", response_model=NotificationSettingsResponse, summary="Actualizar configuración granular de alertas")
async def update_notification_settings(
    payload: NotificationSettingsUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user_allow_mfa_setup)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Guarda canales preferidos y categorías de alertas deseadas por el usuario."""
    if payload.channels is not None:
        if not payload.channels:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Debe seleccionar al menos un canal de notificación.")
        current_user.preferred_notification_channels = [ch.upper() for ch in payload.channels]

    if payload.categories is not None:
        current_user.notification_preferences = payload.categories

    await db.commit()
    await db.refresh(current_user)

    channels = current_user.preferred_notification_channels or ["PUSH", "WHATSAPP", "EMAIL"]
    categories = {k: dict(v) for k, v in DEFAULT_NOTIFICATION_CATEGORIES.items()}
    if current_user.notification_preferences and isinstance(current_user.notification_preferences, dict):
        for k, v in current_user.notification_preferences.items():
            if k in categories and isinstance(v, dict):
                categories[k] = {**categories[k], **v}
            elif isinstance(v, dict):
                categories[k] = v

    return NotificationSettingsResponse(channels=channels, categories=categories)


@router.get("/me/export", summary="Exportar datos personales (Portabilidad GDPR)")
async def export_my_data(
    current_user: Annotated[User, Depends(get_current_user_allow_mfa_setup)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Genera copia estructurada JSON de todos los datos personales y registros asociados del usuario."""
    from app.models.appointment import Appointment
    from app.models.patient_dependent import PatientDependent
    from app.models.patient_consent_grant import PatientConsentGrant

    # Citas asociadas
    appt_stmt = select(Appointment).where(
        or_(Appointment.patient_id == current_user.id, Appointment.doctor_id == current_user.id)
    )
    appointments_list = (await db.execute(appt_stmt)).scalars().all()

    # Dependientes
    dep_stmt = select(PatientDependent).where(PatientDependent.guardian_user_id == current_user.id)
    dependents_list = (await db.execute(dep_stmt)).scalars().all()

    # Consentimientos
    consent_stmt = select(PatientConsentGrant).where(
        or_(PatientConsentGrant.patient_id == current_user.id, PatientConsentGrant.granted_by_user_id == current_user.id)
    )
    consents_list = (await db.execute(consent_stmt)).scalars().all()

    export_payload = {
        "metadata": {
            "title": "Exportación Oficial de Datos Personales - VitaRecord",
            "compliance": "Reglamento General de Protección de Datos (RGPD / GDPR) & Ley Orgánica de Privacidad",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "user_id": current_user.id,
            "version": "1.0",
        },
        "user_profile": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "phone": current_user.phone,
            "role": current_user.role,
            "status": current_user.status,
            "recovery_email": current_user.recovery_email,
            "recovery_phone": current_user.recovery_phone,
            "identification_number": current_user.identification_number,
            "birth_date": current_user.birth_date.isoformat() if current_user.birth_date else None,
            "gender": current_user.gender,
            "address": current_user.address,
            "city": current_user.city,
            "country": current_user.country,
            "created_at": current_user.created_at.isoformat() if hasattr(current_user, "created_at") and current_user.created_at else None,
        },
        "clinical_baseline": {
            "blood_type": current_user.blood_type,
            "height_cm": current_user.height_cm,
            "allergies": current_user.allergies,
            "chronic_conditions": current_user.chronic_conditions,
            "emergency_contact_name": current_user.emergency_contact_name,
            "emergency_contact_phone": current_user.emergency_contact_phone,
            "emergency_contact_relationship": current_user.emergency_contact_relationship,
        },
        "security": {
            "mfa_enabled": current_user.mfa_enabled,
            "has_recovery_codes": bool(current_user.mfa_recovery_codes_hash),
        },
        "notification_settings": {
            "preferred_channels": current_user.preferred_notification_channels or ["PUSH", "WHATSAPP", "EMAIL"],
            "preferences": current_user.notification_preferences or {},
        },
        "dependents": [
            {
                "id": d.id,
                "full_name": d.full_name,
                "relationship": d.relationship,
                "birth_date": d.birth_date.isoformat() if d.birth_date else None,
                "gender": d.gender,
                "emancipation_status": d.emancipation_status,
                "blood_type": d.blood_type,
                "allergies": d.allergies,
                "chronic_conditions": d.chronic_conditions,
            }
            for d in dependents_list
        ],
        "appointments": [
            {
                "id": a.id,
                "start_time": a.start_time.isoformat() if a.start_time else None,
                "end_time": a.end_time.isoformat() if a.end_time else None,
                "status": a.status,
                "reason": a.reason,
                "clinic_id": a.clinic_id,
            }
            for a in appointments_list
        ],
        "consents": [
            {
                "id": c.id,
                "scope": c.scope,
                "granted_to_clinic_id": c.granted_to_clinic_id,
                "granted_at": c.granted_at.isoformat() if c.granted_at else None,
                "granted_until": c.granted_until.isoformat() if c.granted_until else None,
                "is_revoked": c.is_revoked,
            }
            for c in consents_list
        ],
    }

    json_str = json.dumps(export_payload, indent=2, ensure_ascii=False)
    filename = f"vitarecord_datos_usuario_{current_user.id[:8]}.json"
    return Response(
        content=json_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.post("/me/delete-account", summary="Eliminar definitivamente cuenta de usuario (Derecho al olvido)")
async def delete_my_account(
    payload: UserDeleteAccountRequest,
    current_user: Annotated[User, Depends(get_current_user_allow_mfa_setup)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Elimina definitivamente y anonimiza la cuenta del usuario para cumplir con normativas de privacidad."""
    if current_user.hashed_password:
        if not payload.password or not verify_password(payload.password, current_user.hashed_password):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contraseña ingresada no es correcta.")
    else:
        phrase = (payload.confirmation_phrase or "").strip().upper()
        if phrase != "ELIMINAR MI CUENTA":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Debe escribir exactamente 'ELIMINAR MI CUENTA' para confirmar.")

    if current_user.role == "SUPERADMIN":
        superadmin_count = (
            await db.execute(select(func.count()).select_from(User).where(User.role == "SUPERADMIN", User.status == "ACTIVE"))
        ).scalar() or 0
        if superadmin_count <= 1:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No es posible eliminar el único Super Administrador del sistema.")

    # 1. Revocar sesiones
    await AuthService(db).revoke_all_sessions(current_user.id)

    # 2. Desvincular tokens FCM
    from app.repositories.device_token_repository import DeviceTokenRepository
    device_repo = DeviceTokenRepository(db)
    tokens = await device_repo.get_all_tokens_for_user(current_user.id)
    for tok in tokens:
        await db.delete(tok)

    # 3. Eliminar avatares
    for entity in ("users", "patients", "doctors"):
        for ext in ("jpg", "png", "webp", "jpeg"):
            storage_service.delete_file(storage_service.build_avatar_key(entity, current_user.id, ext))

    # 4. Anonimizar PII cumpliendo GDPR y retención clínica
    old_email = current_user.email
    current_user.email = f"deleted_{current_user.id[:8]}_{secrets.token_hex(4)}@deleted.vitarecord.local"
    current_user.full_name = "Usuario Eliminado (RGPD)"
    current_user.phone = None
    current_user.recovery_email = None
    current_user.recovery_phone = None
    current_user.hashed_password = None
    current_user.status = "DEACTIVATED"
    current_user.profile_picture_url = None
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    current_user.mfa_recovery_codes_hash = None
    current_user.address = None
    current_user.city = None
    current_user.emergency_contact_name = None
    current_user.emergency_contact_phone = None
    current_user.emergency_contact_relationship = None

    # 5. Registro inmutable de auditoría
    from app.models.audit import AuditLog
    audit_entry = AuditLog(
        clinic_id=current_user.clinic_id,
        user_id=current_user.id,
        action="ACCOUNT_DELETED_GDPR",
        entity_type="USER",
        entity_id=current_user.id,
        details={
            "original_email_hash": hashlib.sha256(old_email.encode()).hexdigest(),
            "role": current_user.role,
            "reason": payload.reason or "Solicitud voluntaria de eliminación de cuenta",
        },
    )
    db.add(audit_entry)
    await db.commit()

    return {
        "message": "Tu cuenta y datos identificables han sido eliminados y anonimizados permanentemente en cumplimiento con las normativas de privacidad y el RGPD."
    }


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


