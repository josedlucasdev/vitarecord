from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.acl import Permission, has_permission
from app.core.database import get_db
from app.core.security import JWTError, decode_token
from app.core.tenant import set_tenant_context
from app.models.user import User
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
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

    # Inyecta el contexto de tenant para el filtro automatico de ORM
    # (app/core/tenant.py) - clave para el aislamiento del Principio 3.
    set_tenant_context(clinic_id=x_clinic_id, role=user.role)

    return user


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

