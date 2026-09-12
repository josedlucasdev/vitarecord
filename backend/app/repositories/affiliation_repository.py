from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.affiliation import DoctorClinicAffiliation


class AffiliationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, affiliation_id: str) -> DoctorClinicAffiliation | None:
        result = await self.db.execute(
            select(DoctorClinicAffiliation).where(DoctorClinicAffiliation.id == affiliation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_doctor_and_clinic(
        self, doctor_id: str, clinic_id: str
    ) -> DoctorClinicAffiliation | None:
        result = await self.db.execute(
            select(DoctorClinicAffiliation).where(
                DoctorClinicAffiliation.doctor_id == doctor_id,
                DoctorClinicAffiliation.clinic_id == clinic_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> DoctorClinicAffiliation | None:
        result = await self.db.execute(
            select(DoctorClinicAffiliation).where(DoctorClinicAffiliation.invitation_token == token)
        )
        return result.scalar_one_or_none()

    async def list_for_doctor(self, doctor_id: str) -> list[DoctorClinicAffiliation]:
        result = await self.db.execute(
            select(DoctorClinicAffiliation).where(DoctorClinicAffiliation.doctor_id == doctor_id)
        )
        return list(result.scalars().all())

    async def list_for_clinic(self, clinic_id: str) -> list[DoctorClinicAffiliation]:
        result = await self.db.execute(
            select(DoctorClinicAffiliation).where(DoctorClinicAffiliation.clinic_id == clinic_id)
        )
        return list(result.scalars().all())

    async def create(self, affiliation: DoctorClinicAffiliation) -> DoctorClinicAffiliation:
        self.db.add(affiliation)
        await self.db.flush()
        return affiliation
