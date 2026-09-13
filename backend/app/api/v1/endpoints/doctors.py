"""Endpoints de consulta de médicos y sus clínicas afiliadas (plan/plan.md sección 2.B.2)."""

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.affiliation import DoctorClinicAffiliation
from app.models.clinic import Clinic
from app.models.schedule import DoctorWeeklySchedule
from app.models.user import User
from app.schemas.clinic import (
    AcademicDegree,
    ClinicPublic,
    DoctorProfileUpdateRequest,
    DoctorPublicWithClinics,
    WorkExperience,
)
from app.services.email_service import build_branded_email_html, send_email

logger = logging.getLogger("doctors")
router = APIRouter()
AVATARS_DIR = Path("uploads/avatars")


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
                profile_picture_url=doc.profile_picture_url,
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
        profile_picture_url=current_user.profile_picture_url,
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
    if payload.profile_picture_url is not None:
        current_user.profile_picture_url = payload.profile_picture_url
    current_user.is_public_profile_enabled = payload.is_public_profile_enabled
    current_user.academic_degrees = [d.model_dump() for d in payload.academic_degrees]
    current_user.work_experience = [e.model_dump() for e in payload.work_experience]

    await db.commit()
    await db.refresh(current_user)

    return await get_my_doctor_profile(current_user, db)


@router.post("/me/avatar")
async def upload_my_doctor_avatar(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
):
    """Sube y almacena la fotografía de perfil del médico."""
    if current_user.role != "DOCTOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo facultativos médicos pueden actualizar este avatar.")

    allowed_types = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/jpg": "jpg"}
    content_type = (file.content_type or "").lower()
    if content_type not in allowed_types:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Formato de imagen no admitido. Se permite únicamente JPG, PNG o WEBP.",
        )

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La imagen no debe superar los 5 MB de tamaño.")

    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    # Limpiar posibles avatares previos con otras extensiones
    for existing in AVATARS_DIR.glob(f"{current_user.id}.*"):
        try:
            existing.unlink()
        except Exception:
            pass

    ext = allowed_types[content_type]
    file_path = AVATARS_DIR / f"{current_user.id}.{ext}"
    file_path.write_bytes(content)

    avatar_url = f"/api/v1/doctors/{current_user.id}/avatar"
    current_user.profile_picture_url = avatar_url
    await db.commit()
    await db.refresh(current_user)

    return {"profile_picture_url": avatar_url}


@router.get("/{doctor_id}/avatar")
async def get_doctor_avatar(doctor_id: str):
    """Sirve la foto de perfil del médico."""
    if not AVATARS_DIR.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fotografía no encontrada.")

    matches = list(AVATARS_DIR.glob(f"{doctor_id}.*"))
    if not matches:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fotografía no encontrada.")

    file_path = matches[0]
    media_type = "image/jpeg"
    if file_path.suffix.lower() == ".png":
        media_type = "image/png"
    elif file_path.suffix.lower() == ".webp":
        media_type = "image/webp"

    return FileResponse(file_path, media_type=media_type)


@router.delete("/me/avatar")
async def delete_my_doctor_avatar(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Elimina la foto de perfil del médico."""
    if current_user.role != "DOCTOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo facultativos médicos pueden eliminar su avatar.")

    if AVATARS_DIR.exists():
        for existing in AVATARS_DIR.glob(f"{current_user.id}.*"):
            try:
                existing.unlink()
            except Exception:
                pass

    current_user.profile_picture_url = None
    await db.commit()
    return {"message": "Foto de perfil eliminada exitosamente."}


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
        profile_picture_url=user.profile_picture_url,
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
                profile_picture_url=doc.profile_picture_url,
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


@router.post("/me/clinics/{clinic_id}/disaffiliate")
async def disaffiliate_from_clinic(
    clinic_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Permite al médico autenticado desvincularse formal y voluntariamente de una sede clínica.
    Desactiva sus turnos semanales en esa sede, limpia caché de disponibilidad y notifica a la administración.
    """
    if current_user.role != "DOCTOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo facultativos médicos pueden realizar esta acción.")

    clinic = await db.get(Clinic, clinic_id)
    if not clinic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sede clínica no encontrada.")

    # 1. Actualizar afiliación a DISAFFILIATED
    stmt_aff = (
        select(DoctorClinicAffiliation)
        .where(
            DoctorClinicAffiliation.doctor_id == current_user.id,
            DoctorClinicAffiliation.clinic_id == clinic_id,
            DoctorClinicAffiliation.status.in_(["ACTIVE", "INVITED", "INVITED_PENDING_VERIFICATION"]),
        )
    )
    aff_res = await db.execute(stmt_aff)
    affiliations = aff_res.scalars().all()

    if not affiliations and current_user.clinic_id != clinic_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"No posees una vinculación activa con la sede {clinic.name}."
        )

    for aff in affiliations:
        aff.status = "DISAFFILIATED"
        aff.responded_at = datetime.now(timezone.utc)

    # Si no existía registro formal en DoctorClinicAffiliation pero era su clinic_id directo
    if not affiliations and current_user.clinic_id == clinic_id:
        new_aff = DoctorClinicAffiliation(
            doctor_id=current_user.id,
            clinic_id=clinic_id,
            status="DISAFFILIATED",
            responded_at=datetime.now(timezone.utc),
        )
        db.add(new_aff)

    # 2. Si current_user.clinic_id era esta clínica, reasignar o limpiar
    if current_user.clinic_id == clinic_id:
        stmt_other = (
            select(DoctorClinicAffiliation.clinic_id)
            .where(
                DoctorClinicAffiliation.doctor_id == current_user.id,
                DoctorClinicAffiliation.clinic_id != clinic_id,
                DoctorClinicAffiliation.status == "ACTIVE",
            )
            .limit(1)
        )
        other_clinic_id = (await db.execute(stmt_other)).scalar_one_or_none()
        current_user.clinic_id = other_clinic_id

    # 3. Desactivar horarios semanales en esta sede
    stmt_sched = (
        select(DoctorWeeklySchedule)
        .where(
            DoctorWeeklySchedule.doctor_id == current_user.id,
            DoctorWeeklySchedule.clinic_id == clinic_id,
        )
    )
    sched_res = await db.execute(stmt_sched)
    for sched in sched_res.scalars().all():
        sched.is_active = False

    # 4. Invalidar caché en Redis
    try:
        r = get_redis()
        keys = await r.keys(f"slots:{clinic_id}:{current_user.id}:*")
        if keys:
            await r.delete(*keys)
    except Exception as exc:
        logger.warning("Error al invalidar caché Redis de turnos: %s", exc)

    # 5. Notificar por email a la administración de la clínica
    stmt_admins = select(User).where(
        User.role == "CLINIC_ADMIN",
        User.clinic_id == clinic_id,
        User.status == "ACTIVE",
    )
    admins = (await db.execute(stmt_admins)).scalars().all()
    admin_emails = [a.email for a in admins if a.email]
    if not admin_emails:
        admin_emails = ["admin@intimasalud.com"]

    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y a las %H:%M UTC")
    html_content = build_branded_email_html(
        title=f"Desvinculación Médica - Sede {clinic.name}",
        subtitle="Notificación oficial de actualización del cuerpo facultativo de la sede.",
        content_html=(
            f"Se notifica a la administración de <strong>{clinic.name}</strong> que el médico "
            f"<strong>{current_user.full_name or current_user.email}</strong> "
            f"ha solicitado y formalizado su <strong>desvinculación voluntaria</strong> de esta sede médica.<br/><br/>"
            "En cumplimiento del protocolo de desconexión, sus horarios semanales de atención en esta clínica han sido desactivados "
            "y el profesional dejará de figurar en el directorio público asociado a esta sede."
        ),
        details_table=[
            ("Médico Facultativo", current_user.full_name or current_user.email),
            ("Especialidad", current_user.specialty or "No especificada"),
            ("Matrícula Profesional", current_user.license_number or "N/A"),
            ("Sede Médica", clinic.name),
            ("Fecha de Desvinculación", now_str),
            ("Estado", "DESVINCULADO"),
        ],
        alert_box="Esta notificación se genera automáticamente por la plataforma VitaRecord en cumplimiento de las normativas de gestión médica.",
    )

    for email_addr in admin_emails:
        try:
            await send_email(
                email_addr,
                f"Aviso de Desvinculación Médica: Dr. {current_user.full_name or ''} - Sede {clinic.name}",
                html_content,
            )
        except Exception as exc:
            logger.warning("Error enviando email de desvinculación a %s: %s", email_addr, exc)

    await db.commit()

    return {
        "message": f"Te has desvinculado exitosamente de la sede {clinic.name}. La administración de la clínica ha sido formalmente notificada.",
        "clinic_id": clinic.id,
        "clinic_name": clinic.name,
    }

