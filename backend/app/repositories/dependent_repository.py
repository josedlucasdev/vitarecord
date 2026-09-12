import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient_dependent import PatientDependent


class DependentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        guardian_user_id: str,
        full_name: str,
        relationship: str,
        birth_date: datetime.date,
        id_document: str | None = None,
        gender: str | None = None,
    ) -> PatientDependent:
        today = datetime.date.today()
        # Verificar edad para estatus de emancipacion inicial
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        emancipation_status = "EMANCIPATED" if age >= 18 else "MINOR"

        dep = PatientDependent(
            guardian_user_id=guardian_user_id,
            full_name=full_name,
            relationship=relationship,
            birth_date=birth_date,
            id_document=id_document,
            gender=gender,
            emancipation_status=emancipation_status,
        )
        self.db.add(dep)
        await self.db.flush()
        return dep

    async def list_by_guardian(self, guardian_user_id: str) -> list[PatientDependent]:
        stmt = (
            select(PatientDependent)
            .where(PatientDependent.guardian_user_id == guardian_user_id)
            .order_by(PatientDependent.full_name)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_by_id(self, dependent_id: str) -> PatientDependent | None:
        stmt = select(PatientDependent).where(PatientDependent.id == dependent_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def update_emancipation_status(self, dependent_id: str, status: str) -> PatientDependent | None:
        dep = await self.get_by_id(dependent_id)
        if dep:
            dep.emancipation_status = status
            await self.db.flush()
        return dep
