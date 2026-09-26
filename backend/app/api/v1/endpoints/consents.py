"""Consentimientos inter-clínica del paciente (plan/plan.md Principio Operativo 3, 2.B.3 y 2.B.11).

Los datos clínicos generados en una clínica pertenecen a su tenant. Para que
los médicos de OTRA clínica que atienden al paciente puedan leer ese
historial, el paciente otorga un consentimiento explícito, con expiración, y
puede revocarlo en cualquier momento. Otorgar y revocar quedan auditados en
`audit_logs`. La regla de lectura se aplica en
MedicalRecordService.list_patient_history.
"""

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.clinic import Clinic
from app.models.patient_consent_grant import PatientConsentGrant
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.consent_repository import ConsentRepository
from app.schemas.consent import ConsentGrantCreate, ConsentGrantPublic

router = APIRouter()


def _to_public(grant: PatientConsentGrant) -> ConsentGrantPublic:
    now = datetime.datetime.utcnow()
    until = grant.granted_until.replace(tzinfo=None) if grant.granted_until.tzinfo else grant.granted_until
    if grant.is_revoked:
        state = "REVOKED"
    elif until <= now:
        state = "EXPIRED"
    else:
        state = "ACTIVE"
    pub = ConsentGrantPublic.model_validate(grant)
    pub.clinic_name = grant.clinic.name if grant.clinic else None
    pub.status = state
    return pub


def _require_patient(user: User) -> None:
    if user.role != "PATIENT":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el paciente titular gestiona sus consentimientos.")


@router.post("", response_model=ConsentGrantPublic, status_code=status.HTTP_201_CREATED)
async def grant_consent(
    payload: ConsentGrantCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """El paciente autoriza a una clínica a consultar su historial generado en otras clínicas."""
    _require_patient(current_user)
    clinic = await db.get(Clinic, payload.granted_to_clinic_id)
    if not clinic or not clinic.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clínica no encontrada o inactiva.")

    repo = ConsentRepository(db)
    grant = await repo.create(
        patient_id=current_user.id,
        granted_to_clinic_id=clinic.id,
        granted_by_user_id=current_user.id,
        granted_days=payload.granted_days,
        scope=payload.scope,
    )
    await AuditRepository(db).log_event(
        action="CONSENT_GRANTED",
        entity_type="patient_consent_grant",
        entity_id=grant.id,
        user_id=current_user.id,
        clinic_id=clinic.id,
        details={"scope": grant.scope, "granted_until": grant.granted_until.isoformat()},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    return _to_public(await repo.get_by_id(grant.id))


@router.get("/my", response_model=list[ConsentGrantPublic])
async def list_my_consents(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _require_patient(current_user)
    grants = await ConsentRepository(db).list_for_patient(current_user.id)
    return [_to_public(g) for g in grants]


@router.post("/{grant_id}/revoke", response_model=ConsentGrantPublic)
async def revoke_consent(
    grant_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Revocación inmediata: desde este momento la clínica deja de ver el historial externo."""
    _require_patient(current_user)
    repo = ConsentRepository(db)
    grant = await repo.get_by_id(grant_id)
    if not grant or grant.patient_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Consentimiento no encontrado.")
    if grant.is_revoked:
        return _to_public(grant)

    await repo.revoke(grant)
    await AuditRepository(db).log_event(
        action="CONSENT_REVOKED",
        entity_type="patient_consent_grant",
        entity_id=grant.id,
        user_id=current_user.id,
        clinic_id=grant.granted_to_clinic_id,
        details={"scope": grant.scope},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    return _to_public(await repo.get_by_id(grant.id))


@router.get("/clinic/{clinic_id}", response_model=list[ConsentGrantPublic])
async def list_clinic_active_consents(
    clinic_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Consentimientos vigentes recibidos por una clínica (solo metadatos, sin PHI)."""
    is_own_admin = current_user.role == "CLINIC_ADMIN" and current_user.clinic_id == clinic_id
    if current_user.role != "SUPERADMIN" and not is_own_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No autorizado para consultar consentimientos de esta clínica.")
    grants = await ConsentRepository(db).list_active_for_clinic(clinic_id)
    return [_to_public(g) for g in grants]
