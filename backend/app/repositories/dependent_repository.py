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
        blood_type: str | None = None,
        height_cm: float | None = None,
        allergies: str | None = None,
        chronic_conditions: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        notes: str | None = None,
    ) -> PatientDependent:
        today = datetime.date.today()
        # Verificar edad para estatus de emancipacion inicial
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        emancipation_status = "EMANCIPATION_PENDING_CONSENT" if age >= 18 else "MINOR"
        emancipated_at = datetime.datetime.utcnow() if age >= 18 else None

        dep = PatientDependent(
            guardian_user_id=guardian_user_id,
            full_name=full_name,
            relationship=relationship,
            birth_date=birth_date,
            id_document=id_document,
            gender=gender,
            emancipation_status=emancipation_status,
            emancipated_at=emancipated_at,
            blood_type=blood_type,
            height_cm=height_cm,
            allergies=allergies,
            chronic_conditions=chronic_conditions,
            email=email,
            phone=phone,
            notes=notes,
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

    async def get_by_id_and_guardian(self, dependent_id: str, guardian_id: str) -> PatientDependent | None:
        stmt = select(PatientDependent).where(
            PatientDependent.id == dependent_id,
            PatientDependent.guardian_user_id == guardian_id,
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def update_emancipation_status(
        self, dependent_id: str, status: str, emancipated_at: datetime.datetime | None = None
    ) -> PatientDependent | None:
        dep = await self.get_by_id(dependent_id)
        if dep:
            dep.emancipation_status = status
            if emancipated_at is not None:
                dep.emancipated_at = emancipated_at
            await self.db.flush()
        return dep

    async def link_user(self, dependent_id: str, user_id: str) -> PatientDependent | None:
        dep = await self.get_by_id(dependent_id)
        if dep:
            dep.linked_user_id = user_id
            dep.emancipation_status = "EMANCIPATED"
            if not dep.emancipated_at:
                dep.emancipated_at = datetime.datetime.utcnow()
            await self.db.flush()
        return dep

    async def list_minors_turned_adults(self, cutoff_date: datetime.date) -> list[PatientDependent]:
        """Obtiene dependientes en estado MINOR que ya cumplieron los 18 años."""
        stmt = select(PatientDependent).where(
            PatientDependent.emancipation_status == "MINOR",
            PatientDependent.birth_date <= cutoff_date,
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def delete(self, dependent: PatientDependent) -> None:
        await self.db.delete(dependent)
        await self.db.flush()
