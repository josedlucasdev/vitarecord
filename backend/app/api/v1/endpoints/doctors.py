"""Endpoints de consulta de médicos y sus clínicas afiliadas (plan/plan.md sección 2.B.2)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.affiliation import DoctorClinicAffiliation
from app.models.clinic import Clinic
from app.models.user import User
from app.schemas.clinic import (
    AcademicDegree,
    ClinicPublic,
    DoctorProfileUpdateRequest,
    DoctorPublicWithClinics,
    WorkExperience,
)

router = APIRouter()


@router.get("/public-directory", response_model=list[DoctorPublicWithClinics])
async def list_public_doctors_directory(
    db: Annotated[AsyncSession, Depends(get_db)],
    clinic_id: Annotated[str | None, Query(description="Filtrar por ID de clínica")] = None,
    specialty: Annotated[str | None, Query(description="Filtrar por especialidad médica")] = None,
    search: Annotated[str | None, Query(description="Búsqueda por nombre, especialidad o biografía")] = None,
):
    """Directorio médico 100% público para búsqueda y agendamiento de citas sin requerir autenticación previa."""
    # 1. Base query: médicos activos y verificados
    conditions = [
        User.role == "DOCTOR",
        User.status == "ACTIVE",
        User.license_verification_status == "VERIFIED",
        or_(User.is_public_profile_enabled == True, User.is_public_profile_enabled.is_(None)),
        ~User.email.like("%@clinica.com"),
        ~User.email.like("dr.registrado.%"),
        ~User.email.like("dr.nuevo.%"),
    ]

    if specialty:
        conditions.append(User.specialty.ilike(f"%{specialty.strip()}%"))

    if search:
        s = f"%{search.strip()}%"
        conditions.append(
            or_(
                User.full_name.ilike(s),
                User.specialty.ilike(s),
                User.biography.ilike(s),
            )
        )

    stmt_docs = select(User).where(*conditions).order_by(User.full_name.asc())
    docs_result = await db.execute(stmt_docs)
    doctors = list(docs_result.scalars().all())

    if not doctors:
        return []

    # 2. Consultar afiliaciones activas a clínicas
    doc_ids = [d.id for d in doctors]
    stmt_aff = (
        select(DoctorClinicAffiliation, Clinic)
        .join(Clinic, Clinic.id == DoctorClinicAffiliation.clinic_id)
        .where(
            DoctorClinicAffiliation.doctor_id.in_(doc_ids),
            DoctorClinicAffiliation.status == "ACTIVE",
            Clinic.is_active == True,
        )
    )
    aff_result = await db.execute(stmt_aff)
    aff_rows = aff_result.all()

    doctor_clinics_map: dict[str, list[Clinic]] = {}
    for aff, cl in aff_rows:
        doctor_clinics_map.setdefault(aff.doctor_id, []).append(cl)

    all_clinics_stmt = select(Clinic).where(Clinic.is_active == True)
    all_clinics_res = await db.execute(all_clinics_stmt)
    clinics_by_id = {c.id: c for c in all_clinics_res.scalars().all()}

    output: list[DoctorPublicWithClinics] = []
    for doc in doctors:
        doc_clinics = doctor_clinics_map.get(doc.id, [])
        if not doc_clinics and doc.clinic_id and doc.clinic_id in clinics_by_id:
            doc_clinics = [clinics_by_id[doc.clinic_id]]

        # Si se filtró por clínica específica, asegurar que atiende en esa clínica
        if clinic_id:
            clinic_ids_doc = [c.id for c in doc_clinics]
            if clinic_id not in clinic_ids_doc:
                continue

        degrees_data = [AcademicDegree(**d) if isinstance(d, dict) else d for d in (doc.academic_degrees or [])]
        experience_data = [WorkExperience(**e) if isinstance(e, dict) else e for e in (doc.work_experience or [])]

        output.append(
            DoctorPublicWithClinics(
                id=doc.id,
                full_name=doc.full_name,
                email=doc.email,
                phone=doc.phone,
                specialty=doc.specialty,
                biography=doc.biography,
                license_number=doc.license_number,
                license_verification_status=doc.license_verification_status,
                is_available_for_emergencies=doc.is_available_for_emergencies,
                is_public_profile_enabled=doc.is_public_profile_enabled,
                academic_degrees=degrees_data,
                work_experience=experience_data,
                clinics=[ClinicPublic.model_validate(c) for c in doc_clinics],
            )
        )

    return output


@router.get("/me/profile", response_model=DoctorPublicWithClinics)
async def get_my_doctor_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Obtiene el perfil profesional del médico autenticado para su edición."""
    if current_user.role != "DOCTOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo facultativos médicos pueden acceder a este perfil.")

    stmt_aff = (
        select(DoctorClinicAffiliation, Clinic)
        .join(Clinic, Clinic.id == DoctorClinicAffiliation.clinic_id)
        .where(
            DoctorClinicAffiliation.doctor_id == current_user.id,
            DoctorClinicAffiliation.status == "ACTIVE",
            Clinic.is_active == True,
        )
    )
    aff_rows = (await db.execute(stmt_aff)).all()
    doc_clinics = [cl for _, cl in aff_rows]

    if not doc_clinics and current_user.clinic_id:
        cl = await db.get(Clinic, current_user.clinic_id)
        if cl and cl.is_active:
            doc_clinics = [cl]

    degrees_data = [AcademicDegree(**d) if isinstance(d, dict) else d for d in (current_user.academic_degrees or [])]
    experience_data = [WorkExperience(**e) if isinstance(e, dict) else e for e in (current_user.work_experience or [])]

    return DoctorPublicWithClinics(
        id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
        phone=current_user.phone,
        specialty=current_user.specialty,
        biography=current_user.biography,
        license_number=current_user.license_number,
        license_verification_status=current_user.license_verification_status,
        is_available_for_emergencies=current_user.is_available_for_emergencies,
        is_public_profile_enabled=current_user.is_public_profile_enabled,
        academic_degrees=degrees_data,
        work_experience=experience_data,
        clinics=[ClinicPublic.model_validate(c) for c in doc_clinics],
    )


@router.put("/me/profile", response_model=DoctorPublicWithClinics)
async def update_my_doctor_profile(
    payload: DoctorProfileUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Actualiza la biografía, teléfonos, títulos y experiencia laboral del médico."""
    if current_user.role != "DOCTOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo facultativos médicos pueden editar este perfil.")

    if payload.biography is not None:
        current_user.biography = payload.biography
    if payload.phone is not None:
        current_user.phone = payload.phone
    if payload.specialty is not None:
        current_user.specialty = payload.specialty
    current_user.is_public_profile_enabled = payload.is_public_profile_enabled
    current_user.academic_degrees = [d.model_dump() for d in payload.academic_degrees]
    current_user.work_experience = [e.model_dump() for e in payload.work_experience]

    await db.commit()
    await db.refresh(current_user)

    return await get_my_doctor_profile(current_user, db)


@router.get("/{doctor_id}/public-profile", response_model=DoctorPublicWithClinics)
async def get_doctor_public_profile(
    doctor_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Obtiene el perfil público detallado de un médico para el modal o vista de paciente."""
    user = await db.get(User, doctor_id)
    if not user or user.role != "DOCTOR" or user.status != "ACTIVE":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Médico no encontrado o inactivo.")

    stmt_aff = (
        select(DoctorClinicAffiliation, Clinic)
        .join(Clinic, Clinic.id == DoctorClinicAffiliation.clinic_id)
        .where(
            DoctorClinicAffiliation.doctor_id == doctor_id,
            DoctorClinicAffiliation.status == "ACTIVE",
            Clinic.is_active == True,
        )
    )
    aff_rows = (await db.execute(stmt_aff)).all()
    doc_clinics = [cl for _, cl in aff_rows]
    if not doc_clinics and user.clinic_id:
        cl = await db.get(Clinic, user.clinic_id)
        if cl and cl.is_active:
            doc_clinics = [cl]

    degrees_data = [AcademicDegree(**d) if isinstance(d, dict) else d for d in (user.academic_degrees or [])]
    experience_data = [WorkExperience(**e) if isinstance(e, dict) else e for e in (user.work_experience or [])]

    return DoctorPublicWithClinics(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        specialty=user.specialty,
        biography=user.biography,
        license_number=user.license_number,
        license_verification_status=user.license_verification_status,
        is_available_for_emergencies=user.is_available_for_emergencies,
        is_public_profile_enabled=user.is_public_profile_enabled,
        academic_degrees=degrees_data,
        work_experience=experience_data,
        clinics=[ClinicPublic.model_validate(c) for c in doc_clinics],
    )


@router.get("", response_model=list[DoctorPublicWithClinics])
async def list_doctors_with_clinics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Lista todos los médicos activos y verificados, incluyendo las clínicas donde atienden."""
    stmt_docs = select(User).where(
        User.role == "DOCTOR",
        User.status == "ACTIVE",
        User.license_verification_status == "VERIFIED",
        ~User.email.like("%@clinica.com"),
        ~User.email.like("dr.registrado.%"),
        ~User.email.like("dr.nuevo.%"),
    )
    docs_result = await db.execute(stmt_docs)
    doctors = list(docs_result.scalars().all())

    stmt_aff = (
        select(DoctorClinicAffiliation, Clinic)
        .join(Clinic, Clinic.id == DoctorClinicAffiliation.clinic_id)
        .where(
            DoctorClinicAffiliation.status == "ACTIVE",
            Clinic.is_active == True,
        )
    )
    aff_result = await db.execute(stmt_aff)
    aff_rows = aff_result.all()

    doctor_clinics_map: dict[str, list[Clinic]] = {}
    for aff, cl in aff_rows:
        doctor_clinics_map.setdefault(aff.doctor_id, []).append(cl)

    all_clinics_stmt = select(Clinic).where(Clinic.is_active == True)
    all_clinics_res = await db.execute(all_clinics_stmt)
    clinics_by_id = {c.id: c for c in all_clinics_res.scalars().all()}

    output: list[DoctorPublicWithClinics] = []
    for doc in doctors:
        doc_clinics = doctor_clinics_map.get(doc.id, [])
        if not doc_clinics and doc.clinic_id and doc.clinic_id in clinics_by_id:
            doc_clinics = [clinics_by_id[doc.clinic_id]]

        degrees_data = [AcademicDegree(**d) if isinstance(d, dict) else d for d in (doc.academic_degrees or [])]
        experience_data = [WorkExperience(**e) if isinstance(e, dict) else e for e in (doc.work_experience or [])]

        output.append(
            DoctorPublicWithClinics(
                id=doc.id,
                full_name=doc.full_name,
                email=doc.email,
                phone=doc.phone,
                specialty=doc.specialty,
                biography=doc.biography,
                license_number=doc.license_number,
                license_verification_status=doc.license_verification_status,
                is_available_for_emergencies=doc.is_available_for_emergencies,
                is_public_profile_enabled=doc.is_public_profile_enabled,
                academic_degrees=degrees_data,
                work_experience=experience_data,
                clinics=[ClinicPublic.model_validate(c) for c in doc_clinics],
            )
        )

    return output


@router.get("/{doctor_id}/clinics", response_model=list[ClinicPublic])
async def list_doctor_clinics(
    doctor_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Lista las clínicas activas donde un médico específico tiene afiliación activa."""
    stmt = (
        select(Clinic)
        .join(DoctorClinicAffiliation, DoctorClinicAffiliation.clinic_id == Clinic.id)
        .where(
            DoctorClinicAffiliation.doctor_id == doctor_id,
            DoctorClinicAffiliation.status == "ACTIVE",
            Clinic.is_active == True,
        )
    )
    result = await db.execute(stmt)
    clinics = list(result.scalars().all())

    if not clinics:
        user = await db.get(User, doctor_id)
        if user and user.clinic_id:
            cl = await db.get(Clinic, user.clinic_id)
            if cl and cl.is_active:
                clinics = [cl]

    return clinics

