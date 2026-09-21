"""Endpoints de gestión del perfil personal, clínico y avatar del paciente."""

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.patient import PatientProfilePublic, PatientProfileUpdateRequest


logger = logging.getLogger("patients")
router = APIRouter()
AVATARS_DIR = Path("uploads/avatars")


def _build_patient_profile(user: User) -> PatientProfilePublic:
    """Construye el modelo PatientProfilePublic a partir de un usuario."""
    is_complete = bool(user.blood_type and user.height_cm)
    return PatientProfilePublic(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        status=user.status,
        profile_picture_url=user.profile_picture_url,
        identification_number=user.identification_number,
        birth_date=user.birth_date,
        gender=user.gender,
        address=user.address,
        city=user.city,
        country=user.country or "Venezuela",
        blood_type=user.blood_type,
        height_cm=user.height_cm,
        allergies=user.allergies,
        chronic_conditions=user.chronic_conditions,
        emergency_contact_name=user.emergency_contact_name,
        emergency_contact_phone=user.emergency_contact_phone,
        emergency_contact_relationship=user.emergency_contact_relationship,
        is_profile_complete=is_complete,
    )


@router.get("/patients/me/profile", response_model=PatientProfilePublic)
async def get_my_patient_profile(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Consulta el perfil clínico y personal del paciente autenticado."""
    return _build_patient_profile(current_user)


@router.put("/patients/me/profile", response_model=PatientProfilePublic)
async def update_my_patient_profile(
    payload: PatientProfileUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Actualiza datos personales, datos clínicos basales y contacto de emergencia del paciente."""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip()
    if payload.phone is not None:
        current_user.phone = payload.phone.strip()
    if payload.identification_number is not None:
        current_user.identification_number = payload.identification_number.strip()
    if payload.gender is not None:
        current_user.gender = payload.gender
    if payload.address is not None:
        current_user.address = payload.address
    if payload.city is not None:
        current_user.city = payload.city
    if payload.country is not None:
        current_user.country = payload.country

    if payload.birth_date is not None:
        if payload.birth_date == "":
            current_user.birth_date = None
        else:
            try:
                current_user.birth_date = datetime.strptime(payload.birth_date[:10], "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Formato de fecha de nacimiento inválido (YYYY-MM-DD).")

    # Datos clínicos basales
    if payload.blood_type is not None:
        current_user.blood_type = payload.blood_type.strip() or None
    if payload.height_cm is not None:
        current_user.height_cm = payload.height_cm
    if payload.allergies is not None:
        current_user.allergies = payload.allergies.strip() or None
    if payload.chronic_conditions is not None:
        current_user.chronic_conditions = payload.chronic_conditions.strip() or None

    # Contacto de emergencia
    if payload.emergency_contact_name is not None:
        current_user.emergency_contact_name = payload.emergency_contact_name.strip() or None
    if payload.emergency_contact_phone is not None:
        current_user.emergency_contact_phone = payload.emergency_contact_phone.strip() or None
    if payload.emergency_contact_relationship is not None:
        current_user.emergency_contact_relationship = payload.emergency_contact_relationship.strip() or None

    await db.commit()
    await db.refresh(current_user)

    return _build_patient_profile(current_user)


@router.post("/patients/me/avatar")
async def upload_my_patient_avatar(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
):
    """Sube y almacena la fotografía de perfil del paciente."""
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
    # Limpiar posibles avatares previos del paciente
    for existing in AVATARS_DIR.glob(f"patient_{current_user.id}.*"):
        try:
            existing.unlink()
        except Exception:
            pass

    ext = allowed_types[content_type]
    file_path = AVATARS_DIR / f"patient_{current_user.id}.{ext}"
    file_path.write_bytes(content)

    avatar_url = f"/api/v1/patients/{current_user.id}/avatar"
    current_user.profile_picture_url = avatar_url
    await db.commit()
    await db.refresh(current_user)

    return {"profile_picture_url": avatar_url}


@router.get("/patients/{patient_id}/avatar")
async def get_patient_avatar(patient_id: str):
    """Sirve la foto de perfil del paciente."""
    if not AVATARS_DIR.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fotografía no encontrada.")

    matches = list(AVATARS_DIR.glob(f"patient_{patient_id}.*"))
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
