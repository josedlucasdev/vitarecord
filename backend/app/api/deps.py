from contextvars import ContextVar
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.acl import Permission, has_permission
from app.core.config import settings
from app.core.database import get_db
from app.core.security import JWTError, decode_token
from app.core.tenant import CLINIC_BOUND_ROLES, GLOBAL_ROLES, set_tenant_context
from app.models.user import User
from app.repositories.user_repository import UserRepository

# Clinica del personal de sede resuelta en la peticion actual (evita una
# segunda consulta al evaluar la politica de MFA de recepcionistas).
_request_clinic: ContextVar[object | None] = ContextVar("_request_clinic", default=None)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user_allow_mfa_setup(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
    x_clinic_id: Annotated[str | None, Header(alias="X-Clinic-ID")] = None,
) -> User:
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado")
    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido o expirado") from exc

    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token no es de tipo access")

    user = await UserRepository(db).get_by_id(payload["sub"])
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no encontrado")

    if user.status in ("SUSPENDED", "DEACTIVATED"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Cuenta {user.status.lower()}, acceso denegado")

    clinic = None
    if user.clinic_id and user.role in ("CLINIC_ADMIN", "RECEPTIONIST"):
        from app.repositories.clinic_repository import ClinicRepository
        clinic = await ClinicRepository(db).get_by_id(user.clinic_id)
        if clinic and not clinic.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "La sede clínica se encuentra inactiva. Acceso revocado")
    # Se guarda para que get_current_user decida si exige MFA al recepcionista
    # sin volver a consultar la clinica.
    _request_clinic.set(clinic)

    # Inyecta el contexto de tenant para el filtro automatico de ORM
    # (app/core/tenant.py) - clave para el aislamiento del Principio 3.
    effective_clinic_id = await resolve_tenant_clinic_id(db, user, x_clinic_id)
    set_tenant_context(clinic_id=effective_clinic_id, role=user.role)
    await enforce_tenant_rate_limit(effective_clinic_id)

    return user


MFA_SETUP_REQUIRED_DETAIL = (
    "MFA_SETUP_REQUIRED: Su rol exige autenticacion de dos factores. "
    "Active Google Authenticator para continuar."
)


def user_requires_mfa(user: User) -> bool:
    """Reglas de MFA obligatorio (plan 2.B.9)."""
    if not settings.MFA_ENFORCEMENT_ENABLED:
        return False
    if user.role in settings.MFA_REQUIRED_ROLES:
        return True
    if user.role == "RECEPTIONIST":
        clinic = _request_clinic.get()
        return bool(clinic is not None and getattr(clinic, "require_mfa_for_receptionists", False))
    return False


async def get_current_user(
    user: Annotated[User, Depends(get_current_user_allow_mfa_setup)],
) -> User:
    """Usuario autenticado que ademas cumple la politica de MFA obligatorio.

    Los usuarios que deben tener MFA y aun no lo activaron reciben 403 con
    `MFA_SETUP_REQUIRED`; solo pueden usar los endpoints que dependen de
    `get_current_user_allow_mfa_setup` (/auth/me, /auth/mfa/*, sesiones).
    """
    if user_requires_mfa(user) and not (user.mfa_enabled and user.mfa_secret):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            MFA_SETUP_REQUIRED_DETAIL,
            headers={"X-MFA-Setup-Required": "true"},
        )
    return user


async def enforce_tenant_rate_limit(clinic_id: str | None) -> None:
    """Limite de peticiones/segundo por clinica en Redis ("noisy neighbor").

    Si Redis no esta disponible se deja pasar la peticion (fail-open): el
    rate limit es una proteccion de capacidad, no de correccion.
    """
    limit = settings.TENANT_RATE_LIMIT_PER_SECOND
    if not clinic_id or limit <= 0:
        return
    import logging
    import time

    from app.core.redis import get_redis

    key = f"rl:tenant:{clinic_id}:{int(time.time())}"
    try:
        redis = get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 2)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("rate_limit").warning("Rate limit por tenant no disponible: %s", exc)
        return
    if count > limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "La clinica excedio el limite de peticiones por segundo. Intente de nuevo en unos segundos.",
            headers={"Retry-After": "1"},
        )


async def resolve_tenant_clinic_id(db: AsyncSession, user: User, requested_clinic_id: str | None) -> str | None:
    """Determina la clinica efectiva de la peticion SIN confiar en el cliente.

    - Roles globales: sin filtro (la cabecera se ignora).
    - CLINIC_ADMIN / RECEPTIONIST: SIEMPRE su propia clinica; si la cabecera
      apunta a otra clinica se rechaza con 403 (intento de cruce de tenant).
    - DOCTOR: la cabecera es opcional; si llega, el medico debe tener una
      afiliacion ACTIVE con esa clinica.
    - PATIENT: la cabecera se ignora; el acceso del paciente se controla por
      propiedad (patient_id / dependientes), no por tenant.
    """
    if user.role in GLOBAL_ROLES:
        return None

    if user.role in CLINIC_BOUND_ROLES:
        if not user.clinic_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuario de sede sin clinica asignada")
        if requested_clinic_id and requested_clinic_id != user.clinic_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene acceso a la clinica solicitada")
        return user.clinic_id

    if user.role == "DOCTOR":
        if not requested_clinic_id:
            return None
        from sqlalchemy import select

        from app.models.affiliation import DoctorClinicAffiliation

        affiliation_id = await db.scalar(
            select(DoctorClinicAffiliation.id).where(
                DoctorClinicAffiliation.doctor_id == user.id,
                DoctorClinicAffiliation.clinic_id == requested_clinic_id,
                DoctorClinicAffiliation.status == "ACTIVE",
            )
        )
        if affiliation_id is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene una afiliacion activa con la clinica solicitada")
        return requested_clinic_id

    return None


def require_roles(*roles: str):
    async def _checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Rol no autorizado para esta operacion")
        return user

    return _checker


def require_permission(permission: Permission):
    async def _checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Permisos insuficientes. Se requiere el permiso '{permission}'.",
            )
        return user

    return _checker

