import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.patient_consent_grant import PatientConsentGrant


class ConsentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        patient_id: str,
        granted_to_clinic_id: str,
        granted_by_user_id: str,
        granted_days: int = 30,
        scope: str = "READ_MEDICAL_RECORDS",
    ) -> PatientConsentGrant:
        now = datetime.datetime.utcnow()
        until = now + datetime.timedelta(days=granted_days)
        grant = PatientConsentGrant(
            patient_id=patient_id,
            granted_to_clinic_id=granted_to_clinic_id,
            granted_by_user_id=granted_by_user_id,
            scope=scope,
            granted_at=now,
            granted_until=until,
            is_revoked=False,
        )
        self.db.add(grant)
        await self.db.flush()
        return grant

    async def get_by_id(self, grant_id: str) -> PatientConsentGrant | None:
        stmt = (
            select(PatientConsentGrant)
            .options(selectinload(PatientConsentGrant.clinic))
            .where(PatientConsentGrant.id == grant_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_for_patient(self, patient_id: str) -> list[PatientConsentGrant]:
        stmt = (
            select(PatientConsentGrant)
            .options(selectinload(PatientConsentGrant.clinic))
            .where(PatientConsentGrant.patient_id == patient_id)
            .order_by(PatientConsentGrant.granted_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_active_for_clinic(self, clinic_id: str) -> list[PatientConsentGrant]:
        now = datetime.datetime.utcnow()
        stmt = (
            select(PatientConsentGrant)
            .options(selectinload(PatientConsentGrant.clinic), selectinload(PatientConsentGrant.patient))
            .where(
                PatientConsentGrant.granted_to_clinic_id == clinic_id,
                PatientConsentGrant.is_revoked.is_(False),
                PatientConsentGrant.granted_until > now,
            )
            .order_by(PatientConsentGrant.granted_until.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def has_active_consent(
        self, patient_id: str, clinic_ids: str | list[str] | set[str], scope: str = "READ_MEDICAL_RECORDS"
    ) -> bool:
        ids = [clinic_ids] if isinstance(clinic_ids, str) else list(clinic_ids)
        if not ids:
            return False
        now = datetime.datetime.utcnow()
        stmt = select(PatientConsentGrant.id).where(
            and_(
                PatientConsentGrant.patient_id == patient_id,
                PatientConsentGrant.granted_to_clinic_id.in_(ids),
                PatientConsentGrant.scope == scope,
                PatientConsentGrant.is_revoked.is_(False),
                PatientConsentGrant.granted_until > now,
            )
        )
        return (await self.db.execute(stmt.limit(1))).scalar_one_or_none() is not None

    async def revoke(self, grant: PatientConsentGrant) -> PatientConsentGrant:
        grant.is_revoked = True
        grant.revoked_at = datetime.datetime.utcnow()
        await self.db.flush()
        return grant
