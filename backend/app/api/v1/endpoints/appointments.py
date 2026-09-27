import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.core.acl import Permission
from app.core.database import get_db
from app.core.image_processing import sanitize_and_convert_to_webp
from app.models.appointment import Appointment
from app.models.medical_attachment import MedicalAttachment
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCancelRequest,
    AppointmentCreate,
    AppointmentNoShowRequest,
    AppointmentPublic,
    AppointmentRescheduleRequest,
    PublicAppointmentCreate,
)
from app.schemas.medical_record import MedicalAttachmentPublic
from app.schemas.procedure import AppointmentProcedureCreate
from app.services.appointment_service import AppointmentService
from app.services.storage_service import storage_service


router = APIRouter()



@router.post(
    "/public-book",
    response_model=AppointmentPublic,
    status_code=status.HTTP_201_CREATED,
)
async def public_book_appointment(
    payload: PublicAppointmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Reserva de cita médica abierta al público general sin requerir inicio de sesión previo.
    
    Captura información de triage clínico y biométrico, dejando la cita en estado
    PENDING_DOCTOR_APPROVAL hasta ser aceptada por el especialista.
    """
    service = AppointmentService(db)
    return await service.public_book_appointment(payload)


@router.post(
    "",
    response_model=AppointmentPublic,
    status_code=status.HTTP_201_CREATED,
)
async def book_appointment(
    payload: AppointmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.APPOINTMENTS_BOOK))],
):
    """Reserva de cita médica con garantía de bloqueo pesimista contra solapamientos."""
    service = AppointmentService(db)
    return await service.book_appointment(payload, current_user)


@router.get("", response_model=list[AppointmentPublic])
async def list_appointments(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.APPOINTMENTS_MANAGE))],
    clinic_id: str | None = None,
    doctor_id: str | None = None,
    patient_id: str | None = None,
    date: datetime.date | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
):
    """Lista citas médicas aplicando filtros según los permisos del rol autenticado."""
    service = AppointmentService(db)
    return await service.list_appointments(
        current_user=current_user,
        clinic_id=clinic_id,
        doctor_id=doctor_id,
        patient_id=patient_id,
        date=date,
        status=status_filter,
    )


@router.get("/{appointment_id}", response_model=AppointmentPublic)
async def get_appointment(
    appointment_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Obtiene el detalle de una cita médica por su identificador único."""
    service = AppointmentService(db)
    return await service.get_appointment(appointment_id, current_user)



@router.post("/{appointment_id}/doctor-accept", response_model=AppointmentPublic)
async def doctor_accept_appointment(
    appointment_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Aprobación de la cita médica por parte del doctor y envío de invitación por correo al paciente."""
    service = AppointmentService(db)
    return await service.doctor_accept_appointment(appointment_id, current_user)


@router.post("/{appointment_id}/doctor-reject", response_model=AppointmentPublic)
async def doctor_reject_appointment(
    appointment_id: str,
    payload: AppointmentCancelRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Rechazo justificado de cita por parte del doctor."""
    service = AppointmentService(db)
    return await service.doctor_reject_appointment(appointment_id, payload.cancellation_reason, current_user)


@router.post("/{appointment_id}/accept", response_model=AppointmentPublic)
async def accept_appointment(
    appointment_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Aceptación formal de la cita por parte del paciente."""
    service = AppointmentService(db)
    return await service.accept_appointment(appointment_id, current_user)


@router.post("/{appointment_id}/reject", response_model=AppointmentPublic)
async def reject_appointment(
    appointment_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Rechazo de cita por el paciente: libera el slot y el consultorio de inmediato."""
    service = AppointmentService(db)
    return await service.reject_appointment(appointment_id, current_user)


@router.post("/{appointment_id}/cancel", response_model=AppointmentPublic)
async def cancel_appointment(
    appointment_id: str,
    payload: AppointmentCancelRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.APPOINTMENTS_MANAGE))],
):
    """Cancelación oportuna de cita: libera el slot y actualiza el pago a VOID."""
    service = AppointmentService(db)
    return await service.cancel_appointment(appointment_id, payload.cancellation_reason, current_user)


@router.post("/{appointment_id}/procedures", response_model=AppointmentPublic)
async def add_appointment_procedure(
    appointment_id: str,
    payload: AppointmentProcedureCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Agrega un procedimiento clínico realizado a una cita (en consulta médica) y recalcula la caja."""
    service = AppointmentService(db)
    return await service.add_procedure_to_appointment(appointment_id, payload, current_user)


@router.post("/{appointment_id}/check-in", response_model=AppointmentPublic)
async def check_in_appointment(
    appointment_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Marca la llegada del paciente a recepción (CHECKED_IN)."""
    service = AppointmentService(db)
    return await service.check_in(appointment_id, current_user)


@router.post("/{appointment_id}/start-consultation", response_model=AppointmentPublic)
async def start_consultation_appointment(
    appointment_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """El médico especialista inicia formalmente la consulta médica (IN_CONSULTATION)."""
    service = AppointmentService(db)
    return await service.start_consultation(appointment_id, current_user)


@router.post("/{appointment_id}/no-show", response_model=AppointmentPublic)
async def record_no_show_appointment(
    appointment_id: str,
    payload: AppointmentNoShowRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Registra la inasistencia del paciente (NO_SHOW), contabiliza strikes y aplica fair use."""
    service = AppointmentService(db)
    return await service.record_no_show(appointment_id, payload.reason, current_user)


@router.post("/{appointment_id}/reschedule", response_model=AppointmentPublic)
async def reschedule_appointment(
    appointment_id: str,
    payload: AppointmentRescheduleRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Reprograma una cita a un nuevo horario validando disponibilidad de consultorio y médico."""
    service = AppointmentService(db)
    return await service.reschedule_appointment(
        appointment_id=appointment_id,
        new_start_time=payload.new_start_time,
        new_end_time=payload.new_end_time,
        reason=payload.reason,
        current_user=current_user,
    )


@router.post(
    "/{appointment_id}/attachments",
    response_model=MedicalAttachmentPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Subir anexo o audio de consulta a la cita médica",
)
async def upload_appointment_attachment(
    appointment_id: str,
    file: UploadFile = File(...),
    attachment_type: Annotated[str, Form()] = "DOCUMENT",
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(require_permission(Permission.CLINICAL_RECORDS_WRITE))] = None,
):
    """Sube un archivo (audio de consulta, estudio de laboratorio, foto o documento) vinculado a la cita."""
    from sqlalchemy import select

    appt_res = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = appt_res.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita médica no encontrada.")

    # Validar permisos: solo el médico tratante de la cita o personal autorizado
    if current_user.role == "DOCTOR" and appointment.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para adjuntar archivos a una cita asignada a otro especialista.",
        )

    raw_bytes = await file.read()
    orig_name = file.filename or "archivo.dat"
    content_type = file.content_type or "application/octet-stream"

    # Procesar según tipo de anexo
    is_audio = attachment_type == "CONSULTATION_AUDIO" or content_type.startswith("audio/")
    is_img = not is_audio and (
        content_type.startswith("image/") or orig_name.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    )

    if is_img:
        try:
            final_bytes, content_type = sanitize_and_convert_to_webp(raw_bytes)
            file_name = orig_name.rsplit(".", 1)[0] + ".webp"
        except Exception:
            final_bytes = raw_bytes
            file_name = orig_name
    elif is_audio:
        final_bytes = raw_bytes
        # Normalizar extensión si es audio grabado desde navegador webm/mp4
        if "webm" in content_type and not orig_name.lower().endswith(".webm"):
            file_name = f"consulta_audio_{appointment_id[:8]}.webm"
        elif "mp4" in content_type and not orig_name.lower().endswith((".mp4", ".m4a")):
            file_name = f"consulta_audio_{appointment_id[:8]}.mp4"
        else:
            file_name = orig_name
    else:
        final_bytes = raw_bytes
        file_name = orig_name

    s3_key = storage_service.build_medical_record_attachment_key(
        appointment.clinic_id, f"appt_{appointment.id}", file_name
    )
    storage_service.upload_file(final_bytes, s3_key, content_type=content_type)

    attachment = MedicalAttachment(
        appointment_id=appointment.id,
        clinic_id=appointment.clinic_id,
        file_name=file_name,
        content_type=content_type,
        file_size=len(final_bytes),
        s3_key=s3_key,
        attachment_type=attachment_type,
        medical_record_id=None,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    dl_url = None
    try:
        dl_url = storage_service.generate_presigned_download_url(s3_key)
    except Exception:
        pass

    return MedicalAttachmentPublic(
        id=attachment.id,
        file_name=attachment.file_name,
        content_type=attachment.content_type,
        file_size=attachment.file_size,
        attachment_type=attachment.attachment_type,
        appointment_id=attachment.appointment_id,
        medical_record_id=attachment.medical_record_id,
        download_url=dl_url,
    )


@router.get(
    "/{appointment_id}/attachments",
    response_model=list[MedicalAttachmentPublic],
    summary="Listar anexos y audios vinculados a la cita médica",
)
async def list_appointment_attachments(
    appointment_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.CLINICAL_RECORDS_READ))],
):
    """Lista todos los archivos adjuntos y grabaciones de audio asociadas a una cita médica."""
    from sqlalchemy import select

    appt_res = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = appt_res.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita médica no encontrada.")

    stmt = select(MedicalAttachment).where(MedicalAttachment.appointment_id == appointment_id)
    attachments = (await db.execute(stmt)).scalars().all()

    result = []
    for att in attachments:
        dl_url = None
        if att.s3_key:
            try:
                dl_url = storage_service.generate_presigned_download_url(att.s3_key)
            except Exception:
                pass
        result.append(
            MedicalAttachmentPublic(
                id=att.id,
                file_name=att.file_name,
                content_type=att.content_type,
                file_size=att.file_size,
                attachment_type=att.attachment_type,
                appointment_id=att.appointment_id,
                medical_record_id=att.medical_record_id,
                download_url=dl_url,
            )
        )
    return result


@router.delete(
    "/{appointment_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un anexo o grabación de audio de la cita",
)
async def delete_appointment_attachment(
    appointment_id: str,
    attachment_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.CLINICAL_RECORDS_WRITE))],
):
    """Elimina un archivo adjunto tanto de S3 como de la base de datos."""
    from sqlalchemy import select

    stmt = select(MedicalAttachment).where(
        MedicalAttachment.id == attachment_id,
        MedicalAttachment.appointment_id == appointment_id,
    )
    attachment = (await db.execute(stmt)).scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anexo no encontrado.")

    if attachment.s3_key:
        try:
            storage_service.delete_file(attachment.s3_key)
        except Exception:
            pass

    await db.delete(attachment)
    await db.commit()
    return None


