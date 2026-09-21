from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
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
    """Elimina un familiar del núcleo del paciente titular."""
    service = DependentService(db)
    await service.delete_dependent(current_user.id, dependent_id)


@router.post("/patients/me/dependents/{dependent_id}/avatar")
async def upload_dependent_avatar(
    dependent_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    """Sube y almacena la fotografía de perfil de un familiar dependiente."""
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

    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    for existing in AVATARS_DIR.glob(f"dep_{dependent_id}.*"):
        try:
            existing.unlink()
        except Exception:
            pass

    ext = allowed_types[content_type]
    file_path = AVATARS_DIR / f"dep_{dependent_id}.{ext}"
    file_path.write_bytes(content)

    avatar_url = f"/api/v1/patients/dependents/{dependent_id}/avatar"
    dep.profile_picture_url = avatar_url
    await db.commit()
    await db.refresh(dep)

    return {"profile_picture_url": avatar_url}


@router.get("/patients/dependents/{dependent_id}/avatar")
async def get_dependent_avatar(dependent_id: str):
    """Sirve la foto de perfil del familiar."""
    if not AVATARS_DIR.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fotografía no encontrada.")

    matches = list(AVATARS_DIR.glob(f"dep_{dependent_id}.*"))
    if not matches:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fotografía no encontrada.")

    file_path = matches[0]
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    return FileResponse(file_path, media_type=media_types.get(file_path.suffix.lower(), "image/jpeg"))
