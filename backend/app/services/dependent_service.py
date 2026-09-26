import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient_dependent import PatientDependent
from app.repositories.dependent_repository import DependentRepository
from app.schemas.patient_dependent import (
    PatientDependentCreate,
    PatientDependentPublic,
    PatientDependentUpdate,
)


class DependentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = DependentRepository(db)

    def _to_public_schema(self, dep: PatientDependent) -> PatientDependentPublic:
        today = datetime.date.today()
        age = (
            today.year
            - dep.birth_date.year
            - ((today.month, today.day) < (dep.birth_date.month, dep.birth_date.day))
        )
        is_emancipated = age >= 18 or dep.emancipation_status in ("EMANCIPATED", "EMANCIPATION_PENDING_CONSENT")
        is_complete = bool(dep.blood_type and dep.height_cm)

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
            emancipated_at=dep.emancipated_at,
            linked_user_id=dep.linked_user_id,
            blood_type=dep.blood_type,
            height_cm=dep.height_cm,
            allergies=dep.allergies,
            chronic_conditions=dep.chronic_conditions,
            email=dep.email,
            phone=dep.phone,
            notes=dep.notes,
            profile_picture_url=dep.profile_picture_url,
            age=age,
            is_profile_complete=is_complete,
            created_at=dep.created_at,
        )

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
            full_name=payload.full_name.strip(),
            relationship=payload.relationship.strip().upper(),
            birth_date=payload.birth_date,
            id_document=payload.id_document.strip() if payload.id_document else None,
            gender=payload.gender,
            blood_type=payload.blood_type.strip() if payload.blood_type else None,
            height_cm=payload.height_cm,
            allergies=payload.allergies.strip() if payload.allergies else None,
            chronic_conditions=payload.chronic_conditions.strip() if payload.chronic_conditions else None,
            email=payload.email.strip() if payload.email else None,
            phone=payload.phone.strip() if payload.phone else None,
            notes=payload.notes.strip() if payload.notes else None,
        )
        await self.db.commit()
        await self.db.refresh(dep)

        return self._to_public_schema(dep)

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
            # Transición automática a EMANCIPATION_PENDING_CONSENT si cumplió 18 años y estaba en MINOR
            if age >= 18 and dep.emancipation_status == "MINOR":
                now_utc = datetime.datetime.utcnow()
                await self.repo.update_emancipation_status(dep.id, "EMANCIPATION_PENDING_CONSENT", emancipated_at=now_utc)
                await self.db.commit()
                dep.emancipation_status = "EMANCIPATION_PENDING_CONSENT"
                dep.emancipated_at = now_utc

            result.append(self._to_public_schema(dep))
        return result

    async def get_dependent(self, guardian_id: str, dependent_id: str) -> PatientDependentPublic:
        dep = await self.repo.get_by_id_and_guardian(dependent_id, guardian_id)
        if not dep:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Familiar no encontrado.")
        return self._to_public_schema(dep)

    async def update_dependent(
        self, guardian_id: str, dependent_id: str, payload: PatientDependentUpdate
    ) -> PatientDependentPublic:
        dep = await self.repo.get_by_id_and_guardian(dependent_id, guardian_id)
        if not dep:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Familiar no encontrado.")

        if payload.full_name is not None:
            dep.full_name = payload.full_name.strip()
        if payload.relationship is not None:
            dep.relationship = payload.relationship.strip().upper()
        if payload.birth_date is not None:
            if payload.birth_date > datetime.date.today():
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "La fecha de nacimiento no puede ser en el futuro.")
            dep.birth_date = payload.birth_date
            today = datetime.date.today()
            age = today.year - dep.birth_date.year - ((today.month, today.day) < (dep.birth_date.month, dep.birth_date.day))
            if age >= 18 and dep.emancipation_status == "MINOR":
                dep.emancipation_status = "EMANCIPATION_PENDING_CONSENT"
                if not dep.emancipated_at:
                    dep.emancipated_at = datetime.datetime.utcnow()
            elif age < 18:
                dep.emancipation_status = "MINOR"
                dep.emancipated_at = None

        if payload.id_document is not None:
            dep.id_document = payload.id_document.strip() or None
        if payload.gender is not None:
            dep.gender = payload.gender
        if payload.blood_type is not None:
            dep.blood_type = payload.blood_type.strip() or None
        if payload.height_cm is not None:
            dep.height_cm = payload.height_cm
        if payload.allergies is not None:
            dep.allergies = payload.allergies.strip() or None
        if payload.chronic_conditions is not None:
            dep.chronic_conditions = payload.chronic_conditions.strip() or None
        if payload.email is not None:
            dep.email = payload.email.strip() or None
        if payload.phone is not None:
            dep.phone = payload.phone.strip() or None
        if payload.notes is not None:
            dep.notes = payload.notes.strip() or None

        await self.db.commit()
        await self.db.refresh(dep)
        return self._to_public_schema(dep)

    async def claim_dependent(self, user_id: str, dependent_id: str) -> PatientDependentPublic:
        """Permite a un paciente adulto vincularse a su registro histórico de dependiente."""
        dep = await self.repo.get_by_id(dependent_id)
        if not dep:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Familiar dependiente no encontrado.")

        today = datetime.date.today()
        age = today.year - dep.birth_date.year - ((today.month, today.day) < (dep.birth_date.month, dep.birth_date.day))
        if age < 18:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "No se puede emancipar ni vincular una cuenta independiente para un menor de edad.",
            )

        if dep.linked_user_id and dep.linked_user_id != user_id:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Este registro de dependiente ya se encuentra vinculado a otra cuenta de usuario.",
            )

        updated_dep = await self.repo.link_user(dependent_id, user_id)
        await self.db.commit()
        await self.db.refresh(updated_dep)
        return self._to_public_schema(updated_dep)

    async def delete_dependent(self, guardian_id: str, dependent_id: str) -> None:
        dep = await self.repo.get_by_id_and_guardian(dependent_id, guardian_id)
        if not dep:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Familiar no encontrado.")
        await self.repo.delete(dep)
        await self.db.commit()
