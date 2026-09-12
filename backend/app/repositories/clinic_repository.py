from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import Clinic


class ClinicRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, clinic_id: str) -> Clinic | None:
        result = await self.db.execute(select(Clinic).where(Clinic.id == clinic_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Clinic | None:
        result = await self.db.execute(select(Clinic).where(Clinic.slug == slug))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Clinic]:
        result = await self.db.execute(select(Clinic))
        return list(result.scalars().all())

    async def create(self, clinic: Clinic) -> Clinic:
        self.db.add(clinic)
        await self.db.flush()
        return clinic
