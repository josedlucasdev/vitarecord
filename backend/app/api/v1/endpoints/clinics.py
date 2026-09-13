"""Endpoints para aprovisionamiento y consulta de clinicas/tenants (plan/plan.md seccion 2.B.0 y 2.B.1)."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.core.acl import Permission
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_password_reset_token
from app.models.affiliation import DoctorClinicAffiliation, PatientClinicAffiliation
from app.models.clinic import Clinic
from app.models.schedule import DoctorWeeklySchedule
from app.models.user import DoctorScheduleLock, User
from app.repositories.clinic_repository import ClinicRepository
from app.schemas.clinic import ClinicCreateRequest, ClinicDoctorPublic, ClinicPublic
from app.schemas.clinic_user import (
    ALLOWED_CLINIC_ROLES,
    GLOBAL_ROLES,
    TENANT_ROLES,
    ClinicUserCreateRequest,
    ClinicUserPublic,
    ClinicUserRoleUpdate,
)
from app.services.email_service import build_branded_email_html, send_email

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


@router.get("/{clinic_id}/users", response_model=list[ClinicUserPublic])
async def list_clinic_users(
    clinic_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.STAFF_MANAGE))],
    role: str | None = None,
    search: str | None = None,
):
    """Lista los usuarios del tenant (admins y secretarias) y los usuarios globales (médicos y pacientes) activamente vinculados a la sede."""
    if current_user.role != "SUPERADMIN" and current_user.clinic_id != clinic_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No tienes permisos para consultar usuarios de otra clínica.",
        )

    repo = ClinicRepository(db)
    clinic = await repo.get_by_id(clinic_id)
    if not clinic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clínica no encontrada.")

    stmt = (
        select(User)
        .outerjoin(
            DoctorClinicAffiliation,
            (DoctorClinicAffiliation.doctor_id == User.id)
            & (DoctorClinicAffiliation.clinic_id == clinic_id)
            & (DoctorClinicAffiliation.status == "ACTIVE"),
        )
        .outerjoin(
            PatientClinicAffiliation,
            (PatientClinicAffiliation.patient_id == User.id)
            & (PatientClinicAffiliation.clinic_id == clinic_id)
            & (PatientClinicAffiliation.status == "ACTIVE"),
        )
        .where(
            or_(
                (User.clinic_id == clinic_id) & (User.role.in_(TENANT_ROLES)),
                DoctorClinicAffiliation.id.isnot(None),
                PatientClinicAffiliation.id.isnot(None),
            )
        )
        .distinct()
    )

    if role:
        stmt = stmt.where(User.role == role.strip().upper())

    if search:
        term = f"%{search.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(User.full_name).like(term), func.lower(User.email).like(term)))

    stmt = stmt.order_by(User.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/{clinic_id}/users", response_model=ClinicUserPublic, status_code=status.HTTP_201_CREATED)
async def create_clinic_user(
    clinic_id: str,
    payload: ClinicUserCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.STAFF_MANAGE))],
):
    """Crea o vincula usuarios para la clínica.

    - Administradores y Secretarias son usuarios exclusivos del tenant (correo estrictamente único).
    - Médicos y Pacientes son usuarios globales: si ya existen en la plataforma con el mismo rol,
      se vinculan a la clínica; si no existen, se crean y vinculan automáticamente.
    """
    if current_user.role != "SUPERADMIN" and current_user.clinic_id != clinic_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No tienes permisos para crear usuarios en otra clínica.",
        )

    repo = ClinicRepository(db)
    clinic = await repo.get_by_id(clinic_id)
    if not clinic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clínica no encontrada.")

    clean_role = payload.role.strip().upper()
    if clean_role not in ALLOWED_CLINIC_ROLES:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Rol '{payload.role}' no permitido. Roles válidos: {', '.join(ALLOWED_CLINIC_ROLES)}",
        )

    clean_email = payload.email.strip().lower()
    existing_user = await db.scalar(select(User).where(func.lower(User.email) == clean_email))

    role_labels = {
        "CLINIC_ADMIN": "Administrador de Clínica",
        "RECEPTIONIST": "Recepcionista / Secretaria",
        "DOCTOR": "Médico Especialista",
        "PATIENT": "Paciente",
    }
    role_display = role_labels.get(clean_role, clean_role)

    # 1. Caso: Usuario exclusivo del Tenant (CLINIC_ADMIN o RECEPTIONIST)
    if clean_role in TENANT_ROLES:
        if existing_user:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"El correo electrónico '{payload.email}' ya se encuentra registrado en el sistema. Los correos deben ser únicos.",
            )

        new_user = User(
            email=clean_email,
            full_name=payload.full_name.strip(),
            phone=payload.phone.strip() if payload.phone else None,
            role=clean_role,
            status="PENDING_ONBOARDING",
            clinic_id=clinic_id,
            license_verification_status="NOT_APPLICABLE",
        )
        db.add(new_user)
        await db.flush()

        reset_token = create_password_reset_token(new_user.id)
        reset_url = f"{settings.FRONTEND_URL}/#/reset-password?token={reset_token}"

        email_html = build_branded_email_html(
            title=f"Bienvenido a {clinic.name}",
            subtitle=f"Has sido registrado como {role_display}.",
            content_html=(
                f"Hola <strong>{new_user.full_name}</strong>,<br/><br/>"
                f"Se ha creado tu cuenta de acceso a la plataforma para <strong>{clinic.name}</strong>. "
                "Para definir tu contraseña y comenzar a operar en el sistema, haz clic en el siguiente botón:"
            ),
            cta_text="Configurar Mi Contraseña",
            cta_link=reset_url,
            alert_box="Por seguridad, este enlace es válido durante 1 hora.",
        )
        await send_email(new_user.email, f"Activa tu cuenta - {clinic.name}", email_html)

        await db.commit()
        await db.refresh(new_user)
        return new_user

    # 2. Caso: Médico Especialista (Entidad global, puede trabajar en múltiples sedes)
    if clean_role == "DOCTOR":
        if existing_user:
            if existing_user.role != "DOCTOR":
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"El correo electrónico '{payload.email}' ya pertenece a una cuenta con rol '{existing_user.role}'.",
                )

            aff = await db.scalar(
                select(DoctorClinicAffiliation).where(
                    DoctorClinicAffiliation.doctor_id == existing_user.id,
                    DoctorClinicAffiliation.clinic_id == clinic_id,
                )
            )
            if aff and aff.status == "ACTIVE":
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"El médico '{existing_user.full_name}' ya se encuentra activamente vinculado a {clinic.name}.",
                )

            if aff:
                aff.status = "ACTIVE"
                aff.responded_at = datetime.now(timezone.utc)
            else:
                new_aff = DoctorClinicAffiliation(
                    doctor_id=existing_user.id,
                    clinic_id=clinic_id,
                    status="ACTIVE",
                    responded_at=datetime.now(timezone.utc),
                )
                db.add(new_aff)

            # Asegurar lock de agenda
            existing_lock = await db.scalar(select(DoctorScheduleLock).where(DoctorScheduleLock.doctor_id == existing_user.id))
            if not existing_lock:
                db.add(DoctorScheduleLock(doctor_id=existing_user.id))

            email_html = build_branded_email_html(
                title=f"Vinculación a {clinic.name}",
                subtitle="Has sido incorporado al equipo médico de la sede.",
                content_html=(
                    f"Estimado(a) <strong>{existing_user.full_name}</strong>,<br/><br/>"
                    f"Has sido vinculado como facultativo médico en <strong>{clinic.name}</strong>. "
                    "Ya puedes configurar tus horarios y recibir citas para esta sede con tus credenciales habituales."
                ),
                cta_text="Ingresar a la Plataforma",
                cta_link=f"{settings.FRONTEND_URL}/#/login",
            )
            await send_email(existing_user.email, f"Nueva vinculación médica - {clinic.name}", email_html)

            await db.commit()
            await db.refresh(existing_user)
            return existing_user

        # Nuevo médico no existente en la plataforma
        new_user = User(
            email=clean_email,
            full_name=payload.full_name.strip(),
            phone=payload.phone.strip() if payload.phone else None,
            role="DOCTOR",
            status="PENDING_ONBOARDING",
            clinic_id=None,  # Entidad global
            specialty=payload.specialty.strip() if payload.specialty else None,
            license_number=payload.license_number.strip() if payload.license_number else None,
            license_verification_status="VERIFIED",
        )
        db.add(new_user)
        await db.flush()

        affiliation = DoctorClinicAffiliation(
            doctor_id=new_user.id,
            clinic_id=clinic_id,
            status="ACTIVE",
        )
        db.add(affiliation)

        db.add(DoctorScheduleLock(doctor_id=new_user.id))

        reset_token = create_password_reset_token(new_user.id)
        reset_url = f"{settings.FRONTEND_URL}/#/reset-password?token={reset_token}"

        email_html = build_branded_email_html(
            title=f"Bienvenido a {clinic.name}",
            subtitle="Has sido registrado como Médico Especialista.",
            content_html=(
                f"Estimado(a) <strong>{new_user.full_name}</strong>,<br/><br/>"
                f"Se ha creado tu perfil profesional en <strong>{clinic.name}</strong>. "
                "Para configurar tu contraseña de acceso y comenzar a utilizar la plataforma, haz clic en el siguiente enlace:"
            ),
            cta_text="Configurar Mi Contraseña",
            cta_link=reset_url,
            alert_box="Por seguridad, este enlace es válido durante 1 hora.",
        )
        await send_email(new_user.email, f"Activa tu cuenta profesional - {clinic.name}", email_html)

        await db.commit()
        await db.refresh(new_user)
        return new_user

    # 3. Caso: Paciente (Entidad global, puede agendar en múltiples clínicas)
    if clean_role == "PATIENT":
        if existing_user:
            if existing_user.role != "PATIENT":
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"El correo electrónico '{payload.email}' ya pertenece a una cuenta con rol '{existing_user.role}'.",
                )

            pat_aff = await db.scalar(
                select(PatientClinicAffiliation).where(
                    PatientClinicAffiliation.patient_id == existing_user.id,
                    PatientClinicAffiliation.clinic_id == clinic_id,
                )
            )
            if pat_aff and pat_aff.status == "ACTIVE":
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"El paciente '{existing_user.full_name}' ya se encuentra registrado en {clinic.name}.",
                )

            if pat_aff:
                pat_aff.status = "ACTIVE"
            else:
                new_pat_aff = PatientClinicAffiliation(
                    patient_id=existing_user.id,
                    clinic_id=clinic_id,
                    status="ACTIVE",
                )
                db.add(new_pat_aff)

            await db.commit()
            await db.refresh(existing_user)
            return existing_user

        # Nuevo paciente no existente en la plataforma
        new_user = User(
            email=clean_email,
            full_name=payload.full_name.strip(),
            phone=payload.phone.strip() if payload.phone else None,
            role="PATIENT",
            status="PENDING_ONBOARDING",
            clinic_id=None,  # Entidad global
            license_verification_status="NOT_APPLICABLE",
        )
        db.add(new_user)
        await db.flush()

        pat_aff = PatientClinicAffiliation(
            patient_id=new_user.id,
            clinic_id=clinic_id,
            status="ACTIVE",
        )
        db.add(pat_aff)

        reset_token = create_password_reset_token(new_user.id)
        reset_url = f"{settings.FRONTEND_URL}/#/reset-password?token={reset_token}"

        email_html = build_branded_email_html(
            title=f"Bienvenido a {clinic.name}",
            subtitle="Se ha creado tu cuenta de paciente.",
            content_html=(
                f"Hola <strong>{new_user.full_name}</strong>,<br/><br/>"
                f"Has sido registrado como paciente en <strong>{clinic.name}</strong>. "
                "Para definir tu contraseña personal y gestionar tus citas médicas, haz clic en el siguiente botón:"
            ),
            cta_text="Configurar Mi Contraseña",
            cta_link=reset_url,
            alert_box="Por motivos de seguridad, este enlace tiene una validez de 1 hora.",
        )
        await send_email(new_user.email, f"Activa tu cuenta de paciente - {clinic.name}", email_html)

        await db.commit()
        await db.refresh(new_user)
        return new_user


@router.post("/{clinic_id}/users/{user_id}/disaffiliate")
async def disaffiliate_clinic_user(
    clinic_id: str,
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.STAFF_MANAGE))],
):
    """Desvincula a un médico o paciente de la clínica sin alterar su cuenta de usuario ni bloquearle acceso a otras sedes."""
    if current_user.role != "SUPERADMIN" and current_user.clinic_id != clinic_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos para gestionar usuarios de otra clínica.")

    target_user = await db.get(User, user_id)
    if not target_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")

    if target_user.role in TENANT_ROLES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Los administradores y secretarias no se desvinculan porque pertenecen a la clínica. Deben ser desactivados o eliminados.",
        )

    if target_user.role == "DOCTOR":
        aff = await db.scalar(
            select(DoctorClinicAffiliation).where(
                DoctorClinicAffiliation.doctor_id == user_id,
                DoctorClinicAffiliation.clinic_id == clinic_id,
                DoctorClinicAffiliation.status == "ACTIVE",
            )
        )
        if not aff and target_user.clinic_id != clinic_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "El médico no posee una vinculación activa con esta clínica.")

        if aff:
            aff.status = "DISAFFILIATED"
            aff.responded_at = datetime.now(timezone.utc)
        else:
            db.add(
                DoctorClinicAffiliation(
                    doctor_id=user_id,
                    clinic_id=clinic_id,
                    status="DISAFFILIATED",
                    responded_at=datetime.now(timezone.utc),
                )
            )

        # Desactivar horarios del médico en esta sede
        schedules = await db.scalars(
            select(DoctorWeeklySchedule).where(
                DoctorWeeklySchedule.doctor_id == user_id,
                DoctorWeeklySchedule.clinic_id == clinic_id,
            )
        )
        for s in schedules:
            s.is_active = False

        if target_user.clinic_id == clinic_id:
            target_user.clinic_id = None

        await db.commit()
        return {
            "message": f"El médico '{target_user.full_name}' ha sido desvinculado de la clínica. Su cuenta permanece ACTIVA en la plataforma.",
            "user_id": user_id,
            "status": "DISAFFILIATED",
        }

    if target_user.role == "PATIENT":
        pat_aff = await db.scalar(
            select(PatientClinicAffiliation).where(
                PatientClinicAffiliation.patient_id == user_id,
                PatientClinicAffiliation.clinic_id == clinic_id,
                PatientClinicAffiliation.status == "ACTIVE",
            )
        )
        if not pat_aff and target_user.clinic_id != clinic_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "El paciente no posee una vinculación activa con esta clínica.")

        if pat_aff:
            pat_aff.status = "DISAFFILIATED"
        else:
            db.add(
                PatientClinicAffiliation(
                    patient_id=user_id,
                    clinic_id=clinic_id,
                    status="DISAFFILIATED",
                )
            )

        if target_user.clinic_id == clinic_id:
            target_user.clinic_id = None

        await db.commit()
        return {
            "message": f"El paciente '{target_user.full_name}' ha sido desvinculado de la clínica. Su cuenta personal permanece ACTIVA.",
            "user_id": user_id,
            "status": "DISAFFILIATED",
        }


@router.delete("/{clinic_id}/users/{user_id}")
async def remove_or_toggle_clinic_user(
    clinic_id: str,
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.STAFF_MANAGE))],
    action: str | None = None,
):
    """Para médicos y pacientes: realiza desvinculación de la sede sin afectar su cuenta en el sistema.

    Para administradores y secretarias: permite inactivar/activar o eliminar del tenant.
    """
    if current_user.role != "SUPERADMIN" and current_user.clinic_id != clinic_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos para modificar usuarios de otra clínica.")

    if current_user.id == user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No puedes modificar o eliminar tu propio usuario.")

    target_user = await db.get(User, user_id)
    if not target_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")

    # Si es Médico o Paciente -> solo desvinculación
    if target_user.role in GLOBAL_ROLES:
        return await disaffiliate_clinic_user(clinic_id, user_id, db, current_user)

    # Si es Usuario Tenant (CLINIC_ADMIN o RECEPTIONIST)
    if target_user.clinic_id != clinic_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El usuario no pertenece a esta clínica.")

    if action == "delete":
        # Desactivación o eliminación definitiva de usuario del tenant
        target_user.status = "DEACTIVATED"
        await db.commit()
        return {"message": f"Usuario {target_user.full_name} eliminado/desactivado del tenant.", "status": "DEACTIVATED"}

    # Toggle entre ACTIVE y DEACTIVATED
    if target_user.status == "DEACTIVATED":
        target_user.status = "ACTIVE"
    else:
        target_user.status = "DEACTIVATED"

    await db.commit()
    await db.refresh(target_user)
    return target_user


@router.patch("/{clinic_id}/users/{user_id}/role", response_model=ClinicUserPublic)
async def update_clinic_user_role(
    clinic_id: str,
    user_id: str,
    payload: ClinicUserRoleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.STAFF_MANAGE))],
):
    """Permite al administrador de la clínica cambiar el rol de un usuario de la sede (CLINIC_ADMIN <-> RECEPTIONIST)."""
    if current_user.role != "SUPERADMIN" and current_user.clinic_id != clinic_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos para modificar usuarios de otra clínica.")

    if current_user.id == user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No puedes modificar tu propio rol.")

    target_user = await db.get(User, user_id)
    if not target_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")

    if target_user.clinic_id != clinic_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El usuario no pertenece a esta clínica.")

    if target_user.role not in TENANT_ROLES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Los médicos y pacientes son entidades globales; no se puede alterar su rol desde la clínica.",
        )

    clean_new_role = payload.role.strip().upper()
    if clean_new_role not in TENANT_ROLES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Rol destino inválido. Solo se permite alternar entre: {', '.join(TENANT_ROLES)}",
        )

    target_user.role = clean_new_role
    await db.commit()
    await db.refresh(target_user)
    return target_user


@router.post("/{clinic_id}/users/{user_id}/resend-invite")
async def resend_user_invite(
    clinic_id: str,
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.STAFF_MANAGE))],
):
    """Reenvía la invitación con enlace para configurar contraseña."""
    if current_user.role != "SUPERADMIN" and current_user.clinic_id != clinic_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos para gestionar usuarios de otra clínica.")

    repo = ClinicRepository(db)
    clinic = await repo.get_by_id(clinic_id)
    if not clinic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clínica no encontrada.")

    target_user = await db.get(User, user_id)
    if not target_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")

    is_affiliated = False
    if target_user.role == "DOCTOR":
        aff = await db.scalar(
            select(DoctorClinicAffiliation).where(
                DoctorClinicAffiliation.doctor_id == user_id,
                DoctorClinicAffiliation.clinic_id == clinic_id,
                DoctorClinicAffiliation.status == "ACTIVE",
            )
        )
        is_affiliated = aff is not None
    elif target_user.role == "PATIENT":
        pat_aff = await db.scalar(
            select(PatientClinicAffiliation).where(
                PatientClinicAffiliation.patient_id == user_id,
                PatientClinicAffiliation.clinic_id == clinic_id,
                PatientClinicAffiliation.status == "ACTIVE",
            )
        )
        is_affiliated = pat_aff is not None
    elif target_user.role in TENANT_ROLES:
        is_affiliated = target_user.clinic_id == clinic_id

    if not is_affiliated and target_user.clinic_id != clinic_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El usuario no está vinculado a esta clínica.")

    reset_token = create_password_reset_token(target_user.id)
    reset_url = f"{settings.FRONTEND_URL}/#/reset-password?token={reset_token}"

    role_labels = {
        "CLINIC_ADMIN": "Administrador de Clínica",
        "RECEPTIONIST": "Recepcionista / Secretaria",
        "DOCTOR": "Médico Especialista",
        "PATIENT": "Paciente",
    }
    role_display = role_labels.get(target_user.role, target_user.role)

    email_html = build_branded_email_html(
        title=f"Acceso a {clinic.name}",
        subtitle=f"Invitación para configurar tu cuenta ({role_display}).",
        content_html=(
            f"Hola <strong>{target_user.full_name}</strong>,<br/><br/>"
            f"Se ha reenviado tu invitación de acceso para <strong>{clinic.name}</strong>. "
            "Haz clic en el siguiente enlace para configurar tu contraseña de acceso:"
        ),
        cta_text="Configurar Mi Contraseña",
        cta_link=reset_url,
        alert_box="Por motivos de seguridad, este enlace tiene una validez de 1 hora.",
    )
    await send_email(target_user.email, f"Configura tu contraseña - {clinic.name}", email_html)
    return {"message": f"Correo de invitación reenviado exitosamente a {target_user.email}"}

