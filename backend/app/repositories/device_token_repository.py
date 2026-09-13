import datetime
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_device_token import UserDeviceToken


class DeviceTokenRepository:
    """Repositorio para la gestión de tokens de notificación push (FCM / Web Push)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register_device_token(
        self,
        user_id: str,
        fcm_token: str,
        platform: str = "web",
        device_name: str | None = None,
    ) -> UserDeviceToken:
        """Registra o actualiza un token FCM para el usuario."""
        stmt = select(UserDeviceToken).where(UserDeviceToken.fcm_token == fcm_token)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.user_id = user_id
            existing.platform = platform
            existing.device_name = device_name
            existing.is_active = True
            existing.last_used_at = datetime.datetime.utcnow()
            await self.session.flush()
            return existing

        new_token = UserDeviceToken(
            user_id=user_id,
            fcm_token=fcm_token,
            platform=platform,
            device_name=device_name,
            is_active=True,
            last_used_at=datetime.datetime.utcnow(),
        )
        self.session.add(new_token)
        await self.session.flush()
        return new_token

    async def get_active_tokens_for_user(self, user_id: str) -> list[UserDeviceToken]:
        """Retorna todos los tokens activos asociados al usuario."""
        stmt = (
            select(UserDeviceToken)
            .where(UserDeviceToken.user_id == user_id, UserDeviceToken.is_active.is_(True))
            .order_by(UserDeviceToken.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_tokens_for_user(self, user_id: str) -> list[UserDeviceToken]:
        """Retorna todos los dispositivos registrados del usuario."""
        stmt = (
            select(UserDeviceToken)
            .where(UserDeviceToken.user_id == user_id)
            .order_by(UserDeviceToken.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def deactivate_token(self, fcm_token: str) -> None:
        """Marca un token como inactivo (útil cuando FCM responde NotRegistered/InvalidToken)."""
        stmt = select(UserDeviceToken).where(UserDeviceToken.fcm_token == fcm_token)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.is_active = False
            await self.session.flush()

    async def remove_device(self, user_id: str, identifier: str) -> bool:
        """Elimina un token por ID o por token FCM para el usuario."""
        stmt = delete(UserDeviceToken).where(
            UserDeviceToken.user_id == user_id,
            (UserDeviceToken.id == identifier) | (UserDeviceToken.fcm_token == identifier),
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return (result.rowcount or 0) > 0
