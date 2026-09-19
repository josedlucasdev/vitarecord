"""Login, refresh con rotacion y deteccion de reuso, y MFA (plan/plan.md
seccion 2.A y 2.B.9).

Reglas clave implementadas aqui:
- Cada uso de un refresh token lo invalida y emite uno nuevo
  (replaced_by_token_id).
- Si un refresh token YA invalidado se reutiliza, se interpreta como
  robo de sesion y se revocan TODAS las sesiones activas del usuario.
"""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
    verify_totp,
)
from app.models.user import RefreshToken, User
from app.repositories.refresh_token_repository import RefreshTokenRepository, hash_token
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)

    async def authenticate(self, email: str, password: str, mfa_code: str | None = None) -> User:
        user = await self.users.get_by_email(email)
        if user is None or not user.hashed_password or not verify_password(password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales invalidas")

        if user.status not in ("ACTIVE", "PENDING_VERIFICATION"):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Cuenta en estado {user.status}, no puede iniciar sesion")

        if user.clinic_id and user.role in ("CLINIC_ADMIN", "RECEPTIONIST"):
            from app.repositories.clinic_repository import ClinicRepository
            clinic = await ClinicRepository(self.db).get_by_id(user.clinic_id)
            if not clinic or not clinic.is_active:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "La sede clínica asociada se encuentra inactiva o suspendida. Comuníquese con el Super Administrador.",
                )

        if user.mfa_enabled:
            if not mfa_code or not user.mfa_secret or not verify_totp(user.mfa_secret, mfa_code):
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Codigo MFA invalido o ausente")

        return user

    async def issue_token_pair(self, user: User, device_info: str | None = None,
                                ip_address: str | None = None) -> tuple[str, str]:
        access_token = create_access_token(
            user.id, clinic_id=user.clinic_id, role=user.role, email=user.email
        )
        raw_refresh_token = create_refresh_token(user.id)

        payload = decode_token(raw_refresh_token)
        record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh_token),
            device_info=device_info,
            ip_address=ip_address,
            issued_at=datetime.fromtimestamp(payload["iat"].timestamp() if hasattr(payload["iat"], "timestamp") else payload["iat"], tz=timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        await self.refresh_tokens.create(record)
        return access_token, raw_refresh_token

    async def refresh(self, raw_refresh_token: str, device_info: str | None = None,
                       ip_address: str | None = None) -> tuple[str, str]:
        try:
            payload = decode_token(raw_refresh_token)
        except Exception as exc:  # noqa: BLE001 - jose.JWTError u otros
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token invalido") from exc

        if payload.get("type") != "refresh":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token no es de tipo refresh")

        stored = await self.refresh_tokens.get_by_raw_token(raw_refresh_token)
        if stored is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token desconocido")

        if stored.revoked_at is not None:
            # Reuso de un token ya invalidado: posible robo de sesion.
            # Se revocan TODAS las sesiones activas del usuario.
            await self.refresh_tokens.revoke_all_for_user(stored.user_id)
            await self.db.commit()
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Refresh token reutilizado: todas las sesiones fueron revocadas por seguridad",
            )

        user = await self.users.get_by_id(stored.user_id)
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no encontrado")

        stored.revoked_at = datetime.now(timezone.utc)

        new_access_token, new_raw_refresh = await self.issue_token_pair(user, device_info, ip_address)

        new_stored = await self.refresh_tokens.get_by_raw_token(new_raw_refresh)
        if new_stored is not None:
            stored.replaced_by_token_id = new_stored.id

        await self.db.commit()
        return new_access_token, new_raw_refresh

    async def logout(self, raw_refresh_token: str) -> None:
        stored = await self.refresh_tokens.get_by_raw_token(raw_refresh_token)
        if stored is not None and stored.revoked_at is None:
            stored.revoked_at = datetime.now(timezone.utc)
            await self.db.commit()

    async def forgot_password(self, email: str) -> None:
        from app.core.security import create_password_reset_token
        from app.services.email_service import build_branded_email_html, send_email

        user = await self.users.get_by_email(email)
        if not user:
            # Respuesta constante para evitar enumeracion de usuarios
            return

        token = create_password_reset_token(user.id)
        portal_prefix = "patient"
        if user.role in ("SUPERADMIN", "COMPLIANCE_REVIEWER", "MODERATOR"):
            portal_prefix = "admin"
        elif user.role in ("CLINIC_ADMIN", "DOCTOR", "RECEPTIONIST"):
            portal_prefix = "clinic"

        reset_link = f"{settings.FRONTEND_URL}/#/{portal_prefix}/reset-password?token={token}"
        html_body = build_branded_email_html(
            title="Recuperación de Contraseña",
            subtitle="Has solicitado restablecer tu contraseña de acceso a la plataforma VitaRecord.",
            content_html=(
                "Hemos recibido una solicitud para restablecer tu clave de acceso.<br/>"
                "Para definir una nueva contraseña y volver a ingresar a tu cuenta de forma segura, "
                "haz clic en el siguiente enlace:"
            ),
            cta_text="Restablecer Mi Contraseña",
            cta_link=reset_link,
            alert_box="Por seguridad, este enlace es válido durante 1 hora. Si no solicitaste este cambio, puedes ignorar este mensaje; tu cuenta permanecerá debidamente protegida.",
        )
        await send_email(user.email, "Recuperación de Contraseña - VitaRecord", html_body)

    async def reset_password(self, token: str, new_password: str) -> None:
        from app.core.security import hash_password

        try:
            payload = decode_token(token)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token de recuperación inválido o expirado") from exc

        if payload.get("type") != "password_reset":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tipo de token inválido")

        user_id = payload.get("sub")
        user = await self.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

        user.hashed_password = hash_password(new_password)
        if user.status == "PENDING_ONBOARDING":
            user.status = "ACTIVE"
        # Revocar todas las sesiones activas por seguridad
        await self.refresh_tokens.revoke_all_for_user(user.id)
        await self.db.commit()

    async def list_sessions(self, user_id: str) -> list[dict]:
        tokens = await self.refresh_tokens.list_active_for_user(user_id)
        return [
            {
                "id": t.id,
                "device_info": t.device_info,
                "ip_address": t.ip_address,
                "issued_at": t.issued_at.isoformat() if t.issued_at else None,
                "expires_at": t.expires_at.isoformat() if t.expires_at else None,
            }
            for t in tokens
        ]

    async def revoke_session(self, user_id: str, session_id: str) -> bool:
        revoked = await self.refresh_tokens.revoke_by_id(user_id, session_id)
        if revoked:
            await self.db.commit()
        return revoked

    async def revoke_all_sessions(self, user_id: str) -> None:
        await self.refresh_tokens.revoke_all_for_user(user_id)
        await self.db.commit()

