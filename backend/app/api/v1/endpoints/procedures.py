"""Endpoints de gestión de procedimientos clínicos y catálogo de servicios."""

from decimal import Decimal
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.affiliation import DoctorClinicAffiliation
from app.models.clinic import Clinic
from app.models.procedure import MedicalProcedure
from app.models.user import User
from app.schemas.procedure import (
    MedicalProcedureCreate,
    MedicalProcedurePublic,
    MedicalProcedureUpdate,
)

logger = logging.getLogger("procedures")
router = APIRouter()


@router.get("/clinics/{clinic_id}/procedures", response_model=list[MedicalProcedurePublic])
async def list_procedures_for_clinic(
    clinic_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    doctor_id: Annotated[str | None, Query(description="Filtrar por médico si aplica")] = None,
):
    """Obtiene el catálogo de procedimientos disponibles para una clínica y/o médico.
    
    - Si el médico es CONTRATADO ('EMPLOYED'): Aplica el catálogo institucional de la clínica.
    - Si el médico es AUTÓNOMO / ALQUILER ('INDEPENDENT'): Aplica su catálogo personalizado.
      Si el médico independiente no tiene procedimientos registrados, retorna el catálogo institucional por defecto.
    """
    clinic = await db.get(Clinic, clinic_id)
    if not clinic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sede o clínica no encontrada.")

    if doctor_id:
        # Verificar la afiliación del médico con la clínica
        aff_stmt = select(DoctorClinicAffiliation).where(
            DoctorClinicAffiliation.doctor_id == doctor_id,
            DoctorClinicAffiliation.clinic_id == clinic_id,
            DoctorClinicAffiliation.status == "ACTIVE",
        )
        aff = (await db.execute(aff_stmt)).scalar_one_or_none()

        if aff and aff.contract_type == "INDEPENDENT":
            # Procedimientos personalizados del médico independiente
            doc_procs_stmt = select(MedicalProcedure).where(
                MedicalProcedure.clinic_id == clinic_id,
                MedicalProcedure.doctor_id == doctor_id,
                MedicalProcedure.is_active == True,
            ).order_by(MedicalProcedure.name.asc())
            doc_procs = list((await db.execute(doc_procs_stmt)).scalars().all())
            if doc_procs:
                return doc_procs

    # Catálogo institucional de la clínica (doctor_id is None)
    inst_stmt = select(MedicalProcedure).where(
        MedicalProcedure.clinic_id == clinic_id,
        MedicalProcedure.doctor_id.is_(None),
        MedicalProcedure.is_active == True,
    ).order_by(MedicalProcedure.name.asc())
    return list((await db.execute(inst_stmt)).scalars().all())


@router.get("/clinics/{clinic_id}/procedures/manage", response_model=list[MedicalProcedurePublic])
async def list_procedures_to_manage(
    clinic_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Lista los procedimientos que el usuario autenticado tiene derecho a gestionar.
    
    - DOCTOR: Lista sus procedimientos propios para esa sede.
    - CLINIC_ADMIN / SUPERADMIN: Lista los procedimientos institucionales de la sede.
    """
    if current_user.role == "DOCTOR":
        stmt = select(MedicalProcedure).where(
            MedicalProcedure.clinic_id == clinic_id,
            MedicalProcedure.doctor_id == current_user.id,
            MedicalProcedure.is_active == True,
        ).order_by(MedicalProcedure.name.asc())
        return list((await db.execute(stmt)).scalars().all())

    if current_user.role in ("CLINIC_ADMIN", "SUPERADMIN"):
        stmt = select(MedicalProcedure).where(
            MedicalProcedure.clinic_id == clinic_id,
            MedicalProcedure.doctor_id.is_(None),
            MedicalProcedure.is_active == True,
        ).order_by(MedicalProcedure.name.asc())
        return list((await db.execute(stmt)).scalars().all())

    raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos para administrar procedimientos.")


@router.post("/clinics/{clinic_id}/procedures", response_model=MedicalProcedurePublic, status_code=status.HTTP_201_CREATED)
async def create_procedure(
    clinic_id: str,
    payload: MedicalProcedureCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Crea un nuevo procedimiento en el catálogo.
    
    - Si es DOCTOR: Crea un procedimiento privado para el médico en esa sede (si es INDEPENDENT).
    - Si es CLINIC_ADMIN / SUPERADMIN: Crea un procedimiento institucional para la sede.
    """
    target_doctor_id: str | None = None

    if current_user.role == "DOCTOR":
        # Validar afiliación
        aff_stmt = select(DoctorClinicAffiliation).where(
            DoctorClinicAffiliation.doctor_id == current_user.id,
            DoctorClinicAffiliation.clinic_id == clinic_id,
            DoctorClinicAffiliation.status == "ACTIVE",
        )
        aff = (await db.execute(aff_stmt)).scalar_one_or_none()
        if not aff:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No estás afiliado a esta clínica.")
        if aff.contract_type == "EMPLOYED":
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Como médico contratado por la clínica, los precios y catálogo de procedimientos son fijados por la administración.",
            )
        target_doctor_id = current_user.id

    elif current_user.role in ("CLINIC_ADMIN", "SUPERADMIN"):
        if current_user.role != "SUPERADMIN" and current_user.clinic_id != clinic_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes administrar procedimientos de otra clínica.")
        target_doctor_id = None
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos para crear procedimientos.")

    proc = MedicalProcedure(
        clinic_id=clinic_id,
        doctor_id=target_doctor_id,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        currency=payload.currency,
        duration_minutes=payload.duration_minutes,
        category=payload.category,
        is_active=payload.is_active,
    )
    db.add(proc)
    await db.commit()
    await db.refresh(proc)
    return proc


@router.put("/clinics/{clinic_id}/procedures/{procedure_id}", response_model=MedicalProcedurePublic)
async def update_procedure(
    clinic_id: str,
    procedure_id: str,
    payload: MedicalProcedureUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Actualiza datos o precio de un procedimiento."""
    proc = await db.get(MedicalProcedure, procedure_id)
    if not proc or proc.clinic_id != clinic_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Procedimiento no encontrado.")

    if current_user.role == "DOCTOR":
        if proc.doctor_id != current_user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo puedes modificar tus propios procedimientos.")
    elif current_user.role in ("CLINIC_ADMIN", "SUPERADMIN"):
        if current_user.role != "SUPERADMIN" and current_user.clinic_id != clinic_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes modificar procedimientos de otra clínica.")
        if proc.doctor_id is not None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Este procedimiento pertenece a un médico particular.")
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos para modificar este procedimiento.")

    if payload.name is not None:
        proc.name = payload.name
    if payload.description is not None:
        proc.description = payload.description
    if payload.price is not None:
        proc.price = payload.price
    if payload.currency is not None:
        proc.currency = payload.currency
    if payload.duration_minutes is not None:
        proc.duration_minutes = payload.duration_minutes
    if payload.category is not None:
        proc.category = payload.category
    if payload.is_active is not None:
        proc.is_active = payload.is_active

    await db.commit()
    await db.refresh(proc)
    return proc


@router.delete("/clinics/{clinic_id}/procedures/{procedure_id}")
async def delete_procedure(
    clinic_id: str,
    procedure_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Desactiva o elimina un procedimiento del catálogo."""
    proc = await db.get(MedicalProcedure, procedure_id)
    if not proc or proc.clinic_id != clinic_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Procedimiento no encontrado.")

    if current_user.role == "DOCTOR":
        if proc.doctor_id != current_user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo puedes eliminar tus propios procedimientos.")
    elif current_user.role in ("CLINIC_ADMIN", "SUPERADMIN"):
        if current_user.role != "SUPERADMIN" and current_user.clinic_id != clinic_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes eliminar procedimientos de otra clínica.")
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos.")

    proc.is_active = False
    await db.commit()
    return {"message": "Procedimiento desactivado exitosamente."}
