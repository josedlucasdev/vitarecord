import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.dependent_repository import DependentRepository
from app.schemas.patient_dependent import PatientDependentCreate, PatientDependentPublic


class DependentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = DependentRepository(db)

    async def add_dependent(
        self, guardian_id: str, payload: PatientDependentCreate
    ) -> PatientDependentPublic:
        if payload.birth_date > datetime.date.today():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "La fecha de nacimiento no puede ser en el futuro.",
            )

        dep = await self.repo.create(
            guardian_user_id=guardian_id,
            full_name=payload.full_name,
            relationship=payload.relationship,
            birth_date=payload.birth_date,
            id_document=payload.id_document,
            gender=payload.gender,
        )
        await self.db.commit()

        today = datetime.date.today()
        is_emancipated = (
            today.year
            - dep.birth_date.year
            - ((today.month, today.day) < (dep.birth_date.month, dep.birth_date.day))
            >= 18
        )

        return PatientDependentPublic(
            id=dep.id,
            guardian_user_id=dep.guardian_user_id,
            full_name=dep.full_name,
            relationship=dep.relationship,
            birth_date=dep.birth_date,
            id_document=dep.id_document,
            gender=dep.gender,
            emancipation_status=dep.emancipation_status,
            is_emancipated=is_emancipated,
            created_at=dep.created_at,
        )

    async def list_dependents(self, guardian_id: str) -> list[PatientDependentPublic]:
        items = await self.repo.list_by_guardian(guardian_id)
        today = datetime.date.today()

        result = []
        for dep in items:
            age = (
                today.year
                - dep.birth_date.year
                - ((today.month, today.day) < (dep.birth_date.month, dep.birth_date.day))
            )
            # Transición automática a EMANCIPATED si ya cumplió 18 años y estaba en MINOR
            if age >= 18 and dep.emancipation_status == "MINOR":
                await self.repo.update_emancipation_status(dep.id, "EMANCIPATED")
                await self.db.commit()
                dep.emancipation_status = "EMANCIPATED"

            result.append(
                PatientDependentPublic(
                    id=dep.id,
                    guardian_user_id=dep.guardian_user_id,
                    full_name=dep.full_name,
                    relationship=dep.relationship,
                    birth_date=dep.birth_date,
                    id_document=dep.id_document,
                    gender=dep.gender,
                    emancipation_status=dep.emancipation_status,
                    is_emancipated=age >= 18,
                    created_at=dep.created_at,
                )
            )
        return result
