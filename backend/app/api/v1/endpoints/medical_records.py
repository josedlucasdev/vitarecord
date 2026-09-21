"""Endpoints de Historias Clinicas, Recetas con QR y Auditoria (plan/plan.md 2.B.8)."""

import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.core.acl import Permission
from app.core.database import get_db
from app.models.medical_attachment import MedicalAttachment
from app.models.user import User
from app.schemas.medical_record import MedicalRecordCreate, MedicalRecordPublic
from app.schemas.prescription import PrescriptionVerificationPublic
from app.services.medical_record_service import MedicalRecordService
from app.services.storage_service import storage_service

router = APIRouter()


class AttachmentPresignRequest(BaseModel):
    file_name: str
    content_type: str
    file_size: int


class AttachmentRegisterRequest(BaseModel):
    file_name: str
    content_type: str
    file_size: int
    s3_key: str


@router.post(
    "",
    response_model=MedicalRecordPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear historia clínica y emitir receta (Médico tratante)",
)
async def create_medical_record(
    payload: MedicalRecordCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.CLINICAL_RECORDS_WRITE))],
):
    """Cifra los datos clínicos confidenciales en reposo, genera la receta y transiciona la cita a COMPLETED."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = MedicalRecordService(db)
    return await service.create_medical_record(
        data=payload,
        current_user=current_user,
        client_ip=client_ip,
        user_agent=user_agent,
    )


@router.get(
    "/appointment/{appointment_id}",
    response_model=MedicalRecordPublic,
    summary="Consultar historia clínica de una cita (Registra action=READ)",
)
async def get_medical_record_by_appointment(
    appointment_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.CLINICAL_RECORDS_READ))],
):
    """Consulta la historia clínica de una cita. Registra inmutablemente la lectura en audit_logs."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = MedicalRecordService(db)
    return await service.get_record_by_appointment(
        appointment_id=appointment_id,
        current_user=current_user,
        client_ip=client_ip,
        user_agent=user_agent,
    )


@router.get(
    "/patient/{patient_id}",
    response_model=list[MedicalRecordPublic],
    summary="Consultar historial clínico del paciente (Registra action=READ por cada registro)",
)
async def list_patient_history(
    patient_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.CLINICAL_RECORDS_READ))],
    dependent_id: Annotated[str | None, Query()] = None,
    include_dependents: Annotated[bool, Query()] = False,
):
    """Obtiene el listado histórico de consultas de un paciente o dependiente familiar.
    
    Por defecto aísla estrictamente el expediente: si se pasa dependent_id solo devuelve ese familiar;
    si no se pasa, solo devuelve las del titular directo, a menos que include_dependents=True.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = MedicalRecordService(db)
    return await service.list_patient_history(
        patient_id=patient_id,
        current_user=current_user,
        dependent_id=dependent_id,
        include_dependents=include_dependents,
        client_ip=client_ip,
        user_agent=user_agent,
    )


@router.get(
    "/prescriptions/{prescription_id}/pdf",
    summary="Descargar receta médica oficial en formato PDF",
)
async def download_prescription_pdf(
    prescription_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Genera y descarga el PDF firmado con código QR verificable."""
    service = MedicalRecordService(db)
    pdf_bytes = await service.get_prescription_pdf_bytes(prescription_id, current_user)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=receta_{prescription_id[:8]}.pdf"},
    )


@router.get(
    "/prescriptions/verify/{verification_hash}",
    response_model=PrescriptionVerificationPublic,
    summary="Verificación pública de receta médica para farmacias (Sin autenticación)",
)
async def verify_prescription_public(
    verification_hash: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Endpoint público escaneado por el código QR: confirma autenticidad y vigencia sin exponer PHI íntimo."""
    service = MedicalRecordService(db)
    return await service.verify_prescription_public(verification_hash)


@router.post(
    "/{record_id}/attachments/presigned-upload",
    summary="Generar URL prefirmada para subida directa de anexos médicos a S3",
)
async def get_presigned_attachment_upload_url(
    record_id: str,
    payload: AttachmentPresignRequest,
    current_user: Annotated[User, Depends(require_permission(Permission.CLINICAL_RECORDS_WRITE))],
):
    """Genera una URL prefirmada PUT para que el navegador suba ecografías o laboratorios directo a S3."""
    file_ext = payload.file_name.split(".")[-1] if "." in payload.file_name else "dat"
    s3_key = f"medical_records/{record_id}/{uuid.uuid4().hex}.{file_ext}"
    presigned = storage_service.generate_presigned_upload_url(
        s3_key=s3_key,
        content_type=payload.content_type,
    )
    return presigned


@router.post(
    "/{record_id}/attachments",
    summary="Registrar anexo médico confirmado en base de datos",
    status_code=status.HTTP_201_CREATED,
)
async def register_attachment(
    record_id: str,
    payload: AttachmentRegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.CLINICAL_RECORDS_WRITE))],
):
    """Guarda los metadatos del anexo una vez subido exitosamente a S3."""
    from sqlalchemy import select
    from app.models.medical_record import MedicalRecord

    record = (await db.execute(select(MedicalRecord).where(MedicalRecord.id == record_id))).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Historia médica no encontrada.")

    attachment = MedicalAttachment(
        medical_record_id=record.id,
        clinic_id=record.clinic_id,
        file_name=payload.file_name,
        content_type=payload.content_type,
        file_size=payload.file_size,
        s3_key=payload.s3_key,
    )
    db.add(attachment)
    await db.commit()
    return {"id": attachment.id, "file_name": attachment.file_name}
