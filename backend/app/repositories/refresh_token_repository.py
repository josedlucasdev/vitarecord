import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import RefreshToken


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class RefreshTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_raw_token(self, raw_token: str) -> RefreshToken | None:
        token_hash = hash_token(raw_token)
        result = await self.db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        return result.scalar_one_or_none()

    async def create(self, token: RefreshToken) -> RefreshToken:
        self.db.add(token)
        await self.db.flush()
        return token

    async def list_active_for_user(self, user_id: str) -> list[RefreshToken]:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            ).order_by(RefreshToken.issued_at.desc())
        )
        return list(result.scalars().all())

    async def revoke_by_id(self, user_id: str, session_id: str) -> bool:
        from datetime import datetime, timezone

        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.id == session_id,
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        token = result.scalar_one_or_none()
        if not token:
            return False
        token.revoked_at = datetime.now(timezone.utc)
        return True

    async def revoke_all_for_user(self, user_id: str) -> None:
        from datetime import datetime, timezone

        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        )
        now = datetime.now(timezone.utc)
        for token in result.scalars():
            token.revoked_at = now
