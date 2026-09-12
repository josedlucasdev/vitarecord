import datetime
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def has_active_consent(self, patient_id: str, clinic_id: str) -> bool:
        now = datetime.datetime.utcnow()
        stmt = select(PatientConsentGrant).where(
            and_(
                PatientConsentGrant.patient_id == patient_id,
                PatientConsentGrant.granted_to_clinic_id == clinic_id,
                PatientConsentGrant.is_revoked.is_(False),
                PatientConsentGrant.granted_until > now,
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def revoke(self, grant_id: str) -> bool:
        stmt = select(PatientConsentGrant).where(PatientConsentGrant.id == grant_id)
        res = await self.db.execute(stmt)
        grant = res.scalar_one_or_none()
        if grant:
            grant.is_revoked = True
            await self.db.flush()
            return True
        return False
