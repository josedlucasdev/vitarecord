"""Endpoints para gestion de salas y consultorios fisicos por clinica (plan/plan.md seccion 2.B.1 y 2.B.4)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.core.acl import Permission
from app.core.database import get_db
from app.models.clinic import ClinicRoom
from app.models.user import User
from app.repositories.clinic_repository import ClinicRepository
from app.repositories.room_repository import RoomRepository
from app.schemas.room import ClinicRoomCreate, ClinicRoomPublic, ClinicRoomUpdate

router = APIRouter()


def _ensure_clinic_access(user: User, clinic_id: str) -> None:
    if user.role == "SUPERADMIN":
        return
    if user.clinic_id != clinic_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No tienes autorización para administrar consultorios en otra clínica.",
        )


@router.get("/clinics/{clinic_id}/rooms", response_model=list[ClinicRoomPublic])
async def list_clinic_rooms(
    clinic_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.ROOMS_READ))],
):
    """Lista las salas y consultorios fisicos de la clinica."""
    clinic = await ClinicRepository(db).get_by_id(clinic_id)
    if not clinic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clínica no encontrada.")
    return await RoomRepository(db).list_by_clinic(clinic_id)


@router.post(
    "/clinics/{clinic_id}/rooms",
    response_model=ClinicRoomPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_clinic_room(
    clinic_id: str,
    payload: ClinicRoomCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.ROOMS_MANAGE))],
):
    """Crea una sala fisica en la clinica y asegura su fila mutex en room_schedule_locks."""
    _ensure_clinic_access(current_user, clinic_id)
    clinic = await ClinicRepository(db).get_by_id(clinic_id)
    if not clinic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clínica no encontrada.")

    room = ClinicRoom(
        clinic_id=clinic_id,
        name=payload.name,
        room_number=payload.room_number,
        description=payload.description,
        is_active=True,
    )
    await RoomRepository(db).create(room)
    await db.commit()
    return room


@router.put("/clinics/{clinic_id}/rooms/{room_id}", response_model=ClinicRoomPublic)
async def update_clinic_room(
    clinic_id: str,
    room_id: str,
    payload: ClinicRoomUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.ROOMS_MANAGE))],
):
    """Actualiza los datos o el estado de un consultorio fisico."""
    _ensure_clinic_access(current_user, clinic_id)
    repo = RoomRepository(db)
    room = await repo.get_by_id(room_id)
    if not room or room.clinic_id != clinic_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Consultorio no encontrado en esta clínica.")

    if payload.name is not None:
        room.name = payload.name
    if payload.room_number is not None:
        room.room_number = payload.room_number
    if payload.description is not None:
        room.description = payload.description
    if payload.is_active is not None:
        room.is_active = payload.is_active

    await repo.update(room)
    await db.commit()
    return room


@router.delete("/clinics/{clinic_id}/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_clinic_room(
    clinic_id: str,
    room_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.ROOMS_MANAGE))],
):
    """Desactiva un consultorio fisico."""
    _ensure_clinic_access(current_user, clinic_id)
    repo = RoomRepository(db)
    room = await repo.get_by_id(room_id)
    if not room or room.clinic_id != clinic_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Consultorio no encontrado en esta clínica.")

    await repo.deactivate(room_id)
    await db.commit()
