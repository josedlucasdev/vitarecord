import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.patient_dependent import (
    PatientDependentCreate,
    PatientDependentPublic,
    PatientDependentUpdate,
)
from app.services.dependent_service import DependentService
from app.services.storage_service import storage_service

router = APIRouter()
AVATARS_DIR = Path("uploads/avatars")


@router.get("/patients/me/dependents", response_model=list[PatientDependentPublic])
async def list_my_dependents(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Consulta la lista de familiares/dependientes registrados por el paciente titular."""
    service = DependentService(db)
    return await service.list_dependents(current_user.id)


@router.post(
    "/patients/me/dependents",
    response_model=PatientDependentPublic,
    status_code=status.HTTP_201_CREATED,
)
async def add_my_dependent(
    payload: PatientDependentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Registra un nuevo familiar dependiente asociado al paciente titular con su ficha clínica."""
    service = DependentService(db)
    return await service.add_dependent(current_user.id, payload)


@router.get("/patients/me/dependents/{dependent_id}", response_model=PatientDependentPublic)
async def get_my_dependent(
    dependent_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Obtiene el detalle completo y ficha clínica del familiar indicado."""
    service = DependentService(db)
    return await service.get_dependent(current_user.id, dependent_id)


@router.put("/patients/me/dependents/{dependent_id}", response_model=PatientDependentPublic)
async def update_my_dependent(
    dependent_id: str,
    payload: PatientDependentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Actualiza datos personales, ficha clínica o notas de un familiar."""
    service = DependentService(db)
    return await service.update_dependent(current_user.id, dependent_id, payload)


@router.delete("/patients/me/dependents/{dependent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_dependent(
    dependent_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Elimina un familiar del núcleo del paciente titular y su avatar en R2."""
    service = DependentService(db)
    await service.delete_dependent(current_user.id, dependent_id)
    # Limpiar avatar en R2
    for ext in ("jpg", "png", "webp", "jpeg"):
        storage_service.delete_file(storage_service.build_avatar_key("dependents", dependent_id, ext))


@router.post("/patients/me/dependents/{dependent_id}/avatar")
async def upload_dependent_avatar(
    dependent_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    """Sube y almacena la fotografía de perfil de un familiar dependiente en Cloudflare R2."""
    service = DependentService(db)
    dep = await service.repo.get_by_id_and_guardian(dependent_id, current_user.id)
    if not dep:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Familiar no encontrado.")

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

    from app.core.image_processing import sanitize_image_exif

    content, content_type = sanitize_image_exif(content, original_content_type=content_type, max_dimension=1024)
    ext = allowed_types.get(content_type, "png")
    s3_key = storage_service.build_avatar_key("dependents", dependent_id, ext)

    # Limpiar extensiones previas en R2
    for other_ext in ("jpg", "png", "webp", "jpeg"):
        if other_ext != ext:
            storage_service.delete_file(storage_service.build_avatar_key("dependents", dependent_id, other_ext))

    storage_service.upload_file(content=content, s3_key=s3_key, content_type=content_type)

    avatar_url = f"/api/v1/patients/dependents/{dependent_id}/avatar"
    dep.profile_picture_url = avatar_url
    await db.commit()
    await db.refresh(dep)

    return {"profile_picture_url": avatar_url}


@router.api_route("/patients/dependents/{dependent_id}/avatar", methods=["GET", "HEAD"])
async def get_dependent_avatar(dependent_id: str):
    """Sirve la foto de perfil del familiar desde Cloudflare R2."""
    for ext in ("jpg", "png", "webp", "jpeg"):
        s3_key = storage_service.build_avatar_key("dependents", dependent_id, ext)
        res = storage_service.get_file(s3_key)
        if res:
            file_bytes, mime = res
            return Response(content=file_bytes, media_type=mime, headers={"Cache-Control": "public, max-age=86400"})

    # Fallback si existía en disco local
    if AVATARS_DIR.exists():
        matches = list(AVATARS_DIR.glob(f"dep_{dependent_id}.*"))
        if matches:
            file_path = matches[0]
            media_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
            }
            return FileResponse(file_path, media_type=media_types.get(file_path.suffix.lower(), "image/jpeg"))

    raise HTTPException(status.HTTP_404_NOT_FOUND, "Fotografía no encontrada.")


@router.post("/patients/dependents/{dependent_id}/claim", response_model=PatientDependentPublic)
async def claim_emancipated_dependent(
    dependent_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Permite a un paciente con cuenta propia vincular su ficha histórica de dependiente emancipada."""
    service = DependentService(db)
    return await service.claim_dependent(user_id=current_user.id, dependent_id=dependent_id)


@router.post("/patients/me/dependents/{dependent_id}/invite")
async def invite_emancipated_dependent(
    dependent_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    email: str | None = None,
):
    """Invita al dependiente que cumplió la mayoría de edad a registrar su cuenta propia de paciente."""
    service = DependentService(db)
    dep = await service.repo.get_by_id_and_guardian(dependent_id, current_user.id)
    if not dep:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Familiar dependiente no encontrado.")

    target_email = (email or dep.email or "").strip()
    if not target_email:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Se requiere un correo electrónico válido para enviar la invitación al dependiente mayor de edad.",
        )

    # Actualizar correo si fue suministrado en la invitación
    if email and dep.email != target_email:
        dep.email = target_email

    if dep.emancipation_status == "MINOR":
        dep.emancipation_status = "EMANCIPATION_PENDING_CONSENT"
        dep.emancipated_at = datetime.datetime.utcnow()

    await db.commit()

    # Enviar notificación/email de invitación
    from app.services.notification_service import NotificationService
    notif_service = NotificationService(db)
    await notif_service.send_multichannel_notification(
        recipient=None,
        email=target_email,
        subject="Invitación a crear tu cuenta independiente en VitaRecord",
        message=(
            f"Hola {dep.full_name}, has alcanzado la mayoría de edad. Tu responsable legal "
            f"te ha invitado a activar tu propia cuenta personal de paciente en VitaRecord "
            f"para gestionar tu expediente clínico de forma confidencial e independiente."
        ),
    )

    return {
        "status": "INVITATION_SENT",
        "email": target_email,
        "emancipation_status": dep.emancipation_status,
        "message": "Invitación enviada exitosamente al dependiente mayor de edad.",
    }
