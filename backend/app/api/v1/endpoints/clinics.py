"""Endpoints para aprovisionamiento y consulta de clinicas/tenants (plan/plan.md seccion 2.B.0 y 2.B.1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.clinic import Clinic
from app.models.user import User
from app.repositories.clinic_repository import ClinicRepository
from app.schemas.clinic import ClinicCreateRequest, ClinicDoctorPublic, ClinicPublic

router = APIRouter()


@router.get("/public", response_model=list[ClinicPublic])
async def list_public_clinics(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Lista pública de clínicas activas para visitantes y filtros del directorio."""
    repo = ClinicRepository(db)
    all_clinics = await repo.list_all()
    return [c for c in all_clinics if c.is_active]


@router.get("", response_model=list[ClinicPublic])
async def list_clinics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Lista las clinicas registradas en el sistema."""
    repo = ClinicRepository(db)
    return await repo.list_all()


@router.post("", response_model=ClinicPublic, status_code=status.HTTP_201_CREATED)
async def create_clinic(
    payload: ClinicCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Crea una nueva clinica / tenant en la plataforma.

    Exclusivo para SUPERADMIN (plan/plan.md seccion 2.B.0).
    """
    if current_user.role != "SUPERADMIN":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Permisos insuficientes. Solo el SUPERADMIN puede dar de alta nuevos tenants/clínicas.",
        )

    repo = ClinicRepository(db)
    existing = await repo.get_by_slug(payload.slug)
    if existing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"El slug '{payload.slug}' ya se encuentra en uso por otra clínica.",
        )

    clinic = Clinic(
        name=payload.name,
        slug=payload.slug,
        timezone=payload.timezone,
        country_code=payload.country_code,
        is_active=True,
    )
    await repo.create(clinic)
    await db.commit()
    return clinic


@router.get("/{clinic_id}", response_model=ClinicPublic)
async def get_clinic(
    clinic_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Consulta los datos de una clinica especifica."""
    repo = ClinicRepository(db)
    clinic = await repo.get_by_id(clinic_id)
    if not clinic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clínica no encontrada")
    return clinic


@router.get("/{clinic_id}/doctors", response_model=list[ClinicDoctorPublic])
async def list_clinic_doctors(
    clinic_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Lista los médicos activos y verificados afiliados a la clínica para agendamiento."""
    from sqlalchemy import select
    from app.models.affiliation import DoctorClinicAffiliation

    stmt = (
        select(User)
        .join(DoctorClinicAffiliation, DoctorClinicAffiliation.doctor_id == User.id)
        .where(
            DoctorClinicAffiliation.clinic_id == clinic_id,
            DoctorClinicAffiliation.status == "ACTIVE",
            User.role == "DOCTOR",
            User.status == "ACTIVE",
            User.license_verification_status == "VERIFIED",
            ~User.email.like("%@clinica.com"),
            ~User.email.like("dr.registrado.%"),
            ~User.email.like("dr.nuevo.%"),
        )
    )
    result = await db.execute(stmt)
    doctors = list(result.scalars().all())

    # Fallback si el usuario tiene clinic_id directo
    if not doctors:
        stmt2 = select(User).where(
            User.clinic_id == clinic_id,
            User.role == "DOCTOR",
            User.status == "ACTIVE",
            User.license_verification_status == "VERIFIED",
            ~User.email.like("%@clinica.com"),
            ~User.email.like("dr.registrado.%"),
            ~User.email.like("dr.nuevo.%"),
        )
        result2 = await db.execute(stmt2)
        doctors = list(result2.scalars().all())

    return doctors
