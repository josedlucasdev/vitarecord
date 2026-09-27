"""Endpoints de Historias Clinicas, Recetas con QR y Auditoria (plan/plan.md 2.B.8)."""

import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.core.acl import Permission
from app.core.database import get_db
from app.models.medical_attachment import MedicalAttachment
from app.models.user import User
from app.schemas.medical_record import (
    AIConsultationAssistRequest,
    AIConsultationAssistResponse,
    AIPrescriptionItem,
    DoctorAttendedPatientPublic,
    MedicalRecordCreate,
    MedicalRecordPublic,
)

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
    "/doctor/my-patients",
    response_model=list[DoctorAttendedPatientPublic],
    summary="Listar pacientes atendidos por el médico (Búsqueda y expediente)",
)
async def list_doctor_attended_patients(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.CLINICAL_RECORDS_READ))],
    q: Annotated[str | None, Query(description="Término de búsqueda")] = None,
    filter_type: Annotated[str | None, Query(alias="filter", description="Filtro ALL, TITULAR o DEPENDENT")] = None,
):
    """Permite al médico buscar y listar los pacientes a los que ha atendido al menos una vez."""
    from fastapi import HTTPException
    if current_user.role != "DOCTOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los médicos especialistas pueden acceder a su lista de pacientes atendidos.",
        )
    service = MedicalRecordService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.list_doctor_attended_patients(
        doctor_id=current_user.id,
        query=q,
        filter_type=filter_type,
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
    "/patient/{patient_id}/pdf",
    summary="Descargar o imprimir historia clínica integral en PDF",
)
async def download_patient_medical_history_pdf(
    patient_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.CLINICAL_RECORDS_READ))],
    dependent_id: Annotated[str | None, Query()] = None,
):
    """Genera e imprime el expediente clínico completo del paciente en formato PDF oficial."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = MedicalRecordService(db)
    pdf_bytes = await service.get_medical_history_pdf_bytes(
        patient_id=patient_id,
        current_user=current_user,
        dependent_id=dependent_id,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    suffix = f"_{dependent_id[:8]}" if dependent_id else f"_{patient_id[:8]}"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=historia_clinica{suffix}.pdf"},
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
    clinic_id = getattr(current_user, "clinic_id", None) or "general"
    s3_key = storage_service.build_medical_record_attachment_key(clinic_id, record_id, payload.file_name)
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
    """Guarda los metadatos del anexo una vez subido exitosamente a S3, aplicando optimización WebP y eliminación EXIF si es imagen."""
    from sqlalchemy import select
    from app.models.medical_record import MedicalRecord

    record = (await db.execute(select(MedicalRecord).where(MedicalRecord.id == record_id))).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Historia médica no encontrada.")

    file_name = payload.file_name
    content_type = payload.content_type
    file_size = payload.file_size
    s3_key = payload.s3_key

    # Optimización WebP y eliminación EXIF para imágenes (plan 2.B.5 / Módulo 5)
    is_img = content_type.startswith("image/") or file_name.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    if is_img:
        try:
            file_data = storage_service.get_file(s3_key)
            if file_data:
                raw_bytes, _ = file_data
                from app.core.image_processing import sanitize_and_convert_to_webp

                webp_bytes, new_content_type = sanitize_and_convert_to_webp(raw_bytes)
                new_key = s3_key.rsplit(".", 1)[0] + ".webp"
                storage_service.upload_file(webp_bytes, new_key, content_type=new_content_type)
                if new_key != s3_key:
                    storage_service.delete_file(s3_key)

                s3_key = new_key
                content_type = new_content_type
                file_size = len(webp_bytes)
                file_name = file_name.rsplit(".", 1)[0] + ".webp"
        except Exception:
            pass

    attachment = MedicalAttachment(
        medical_record_id=record.id,
        clinic_id=record.clinic_id,
        file_name=file_name,
        content_type=content_type,
        file_size=file_size,
        s3_key=s3_key,
    )
    db.add(attachment)
    await db.commit()
    return {"id": attachment.id, "file_name": attachment.file_name, "content_type": attachment.content_type, "file_size": attachment.file_size}


@router.post(
    "/{record_id}/attachments/upload",
    summary="Subida directa de anexo médico con sanitización EXIF y WebP",
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment_direct(
    record_id: str,
    file: UploadFile = File(...),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(require_permission(Permission.CLINICAL_RECORDS_WRITE))] = None,
):
    """Sube un archivo directamente, convirtiendo imágenes a WebP y eliminando metadatos EXIF."""
    from sqlalchemy import select
    from app.models.medical_record import MedicalRecord

    record = (await db.execute(select(MedicalRecord).where(MedicalRecord.id == record_id))).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Historia médica no encontrada.")

    raw_bytes = await file.read()
    orig_name = file.filename or "archivo.dat"
    content_type = file.content_type or "application/octet-stream"

    is_img = content_type.startswith("image/") or orig_name.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    if is_img:
        from app.core.image_processing import sanitize_and_convert_to_webp

        final_bytes, content_type = sanitize_and_convert_to_webp(raw_bytes)
        file_name = orig_name.rsplit(".", 1)[0] + ".webp"
    else:
        final_bytes = raw_bytes
        file_name = orig_name

    s3_key = storage_service.build_medical_record_attachment_key(record.clinic_id, record.id, file_name)
    storage_service.upload_file(final_bytes, s3_key, content_type=content_type)

    attachment = MedicalAttachment(
        medical_record_id=record.id,
        clinic_id=record.clinic_id,
        file_name=file_name,
        content_type=content_type,
        file_size=len(final_bytes),
        s3_key=s3_key,
    )
    db.add(attachment)
    await db.commit()
    return {"id": attachment.id, "file_name": attachment.file_name, "content_type": attachment.content_type, "file_size": attachment.file_size}


class AIAssistRequest(BaseModel):
    clinic_id: str
    field_type: str  # anamnesis, physical_exam, diagnosis, plan
    text: str
    tone: str | None = "formal_clinical"  # formal_clinical, summary, detailed


class AIAssistResponse(BaseModel):
    enhanced_text: str
    provider: str
    tokens_used: int | None = None


@router.post(
    "/ai-assist",
    response_model=AIAssistResponse,
    summary="Mejorar y estructurar texto clínico dictado mediante Inteligencia Artificial",
)
async def enhance_clinical_text(
    payload: AIAssistRequest,
    current_user: Annotated[User, Depends(require_permission(Permission.CLINICAL_RECORDS_WRITE))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Procesa el texto dictado o redactado por el médico tratante usando el proveedor de IA configurado para la clínica."""
    import httpx
    from fastapi import HTTPException
    from app.models.clinic import Clinic

    if not payload.text or not payload.text.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El texto a mejorar no puede estar vacío.")

    clinic = await db.get(Clinic, payload.clinic_id)
    if not clinic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sede clínica no encontrada.")

    if not clinic.ai_enabled:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El módulo de Inteligencia Artificial no está activo para esta sede. El SuperAdmin debe activarlo en la gestión de clínicas.",
        )

    api_url = (clinic.ai_api_url or "").strip()
    api_key = (clinic.ai_api_key or "").strip()

    if not api_url or not api_key:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "La clínica tiene la IA activada pero falta configurar la URL de la API o el Token de acceso.",
        )

    field_descriptions = {
        "anamnesis": "Motivo de Consulta y Enfermedad Actual (Anamnesis ginecológica y médica integral)",
        "physical_exam": "Examen Físico y Signos Vitales (Exploración física, constantes vitales y hallazgos)",
        "diagnosis": "Diagnóstico Clínico Detallado (Diagnóstico presuntivo o de certeza, clasificación y estadio)",
        "plan": "Conducta Médica y Plan de Tratamiento Terapéutico (Indicaciones, farmacoterapia, estudios paraclínicos y pautas de seguimiento)",
    }
    field_desc = field_descriptions.get(payload.field_type, payload.field_type)

    system_prompt = (
        "Eres un asistente médico experto en redacción clínica profesional y terminología médica precisa. "
        "Tu tarea es corregir la ortografía, puntuar correctamente, estructurar en párrafos limpios y enriquecer con léxico médico formal "
        "el siguiente texto dictado por un médico especialista, manteniendo estrictamente todos los hechos clínicos, dosis y datos reales sin inventar información. "
        "Devuelve únicamente el texto clínico mejorado, sin introducciones ni saludos."
    )
    user_prompt = f"Sección clínica: {field_desc}.\nTexto dictado por el médico:\n{payload.text.strip()}"

    # Soporte compatible con OpenAI / Anthropic / Gemini / Ollama / Local REST APIs
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": (clinic.ai_model or "").strip() or "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 1000
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(api_url, json=body, headers=headers)
            if res.status_code == 200:
                data = res.json()
                enhanced = ""
                # Formato OpenAI Chat Completions
                if "choices" in data and len(data["choices"]) > 0:
                    enhanced = data["choices"][0].get("message", {}).get("content", "").strip()
                # Formato Gemini REST
                elif "candidates" in data and len(data["candidates"]) > 0:
                    enhanced = data["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                # Fallback plano
                elif "output" in data:
                    enhanced = str(data["output"]).strip()
                elif "response" in data:
                    enhanced = str(data["response"]).strip()
                else:
                    enhanced = str(data)

                return AIAssistResponse(
                    enhanced_text=enhanced or payload.text,
                    provider="external_ai_gateway",
                    tokens_used=data.get("usage", {}).get("total_tokens")
                )
            else:
                err_detail = res.text[:300]
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    f"Error del proveedor de IA (HTTP {res.status_code}): {err_detail}",
                )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Fallo al conectar con el servicio de IA: {str(exc)}",
        )


@router.post(
    "/ai-consultation-assist",
    response_model=AIConsultationAssistResponse,
    summary="Asistencia inteligente para consulta médica completa (Audio, especialidad y documentos)",
)
async def assist_full_consultation(
    payload: AIConsultationAssistRequest,
    current_user: Annotated[User, Depends(require_permission(Permission.CLINICAL_RECORDS_WRITE))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Analiza la consulta clínica completa (diálogo médico-paciente, especialidad médica y documentos/exámenes).

    Estructura y prellena formalmente los campos de anamnesis, examen físico, diagnóstico, CIE-10, conducta y receta.
    """
    import base64
    import json
    import re
    import httpx
    from fastapi import HTTPException
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.appointment import Appointment
    from app.models.clinic import Clinic

    if not payload.transcript or not payload.transcript.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La transcripción de la consulta no puede estar vacía.")

    stmt = (
        select(Appointment)
        .options(
            selectinload(Appointment.doctor),
            selectinload(Appointment.patient),
            selectinload(Appointment.clinic),
            selectinload(Appointment.dependent),
            selectinload(Appointment.attachments),
        )
        .where(Appointment.id == payload.appointment_id)
    )
    appointment = (await db.execute(stmt)).scalar_one_or_none()
    if not appointment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cita médica no encontrada.")

    clinic = appointment.clinic
    if not clinic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sede clínica asociada no encontrada.")

    if not clinic.ai_enabled or not getattr(clinic, "ai_consultation_assistant_enabled", False):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El módulo de Consulta Asistida por IA no está activo para esta sede. El SuperAdmin debe activarlo.",
        )

    api_url = (clinic.ai_api_url or "").strip()
    api_key = (clinic.ai_api_key or "").strip()
    ai_model = (clinic.ai_model or "").strip() or "gpt-4o-mini"

    if not api_url or not api_key:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "La clínica tiene la IA activada pero falta configurar la URL de la API o el Token de acceso.",
        )

    # 1. Resolver Especialidad Médica y Contexto Clínico
    doctor_specialty = (
        payload.doctor_specialty
        or (appointment.doctor.specialty if appointment.doctor else None)
        or "Medicina General"
    )

    if appointment.dependent:
        patient_desc = f"{appointment.dependent.full_name} (Familiar Dependiente, {appointment.dependent.relationship or 'A cargo'})"
    else:
        patient_name = appointment.patient.full_name if appointment.patient else "Paciente"
        patient_desc = f"{patient_name} (Paciente Titular)"

    intake_parts = []
    if appointment.intake_data and isinstance(appointment.intake_data, dict):
        for k, v in appointment.intake_data.items():
            if v:
                intake_parts.append(f"{k}: {v}")
    intake_str = ("Triage basal y antecedentes registrados: " + "; ".join(intake_parts)) if intake_parts else ""
    reason_str = f"Motivo inicial reportado al agendar: {appointment.reason}" if appointment.reason else ""

    # 2. Procesar documentos y fotos adjuntas en la cita
    doc_descriptions = []
    image_parts = []
    for att in (appointment.attachments or []):
        if att.attachment_type == "CONSULTATION_AUDIO":
            continue
        doc_descriptions.append(f"- Anexo: {att.file_name} ({att.attachment_type})")
        if att.content_type.startswith("image/") and att.file_size < 4 * 1024 * 1024:
            file_data = storage_service.get_file(att.s3_key)
            if file_data:
                raw_b, ctype = file_data
                b64 = base64.b64encode(raw_b).decode("utf-8")
                image_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{ctype};base64,{b64}"}
                })

    # 3. Construir Prompts Especializados
    system_prompt = (
        f"Eres un médico especialista de máximo prestigio y rigor clínico en {doctor_specialty}. "
        "Estás asistiendo en tiempo real al médico tratante tras haber grabado la consulta médica con el paciente.\n\n"
        f"Tu objetivo es actuar y redactar pensando exactamente como un médico especialista en {doctor_specialty}, "
        "estructurando una historia clínica profesional, completa y concisa a partir del diálogo sostenido en la consulta, "
        "los antecedentes del paciente y los exámenes o fotos presentados.\n\n"
        "Reglas clínicas fundamentales:\n"
        "1. Aplica terminología médica formal, precisa y elegante en español.\n"
        "2. Mantén estricta fidelidad a lo manifestado por médico y paciente: no agregues patologías ni fármacos no mencionados.\n"
        "3. Si en la conversación se acordó un tratamiento, extrae con exactitud los medicamentos, dosis, frecuencia y duración.\n"
        "4. Proporciona el código de Clasificación Internacional de Enfermedades (CIE-10 / ICD-10) más certero para el diagnóstico principal.\n\n"
        "RESPONDE ÚNICAMENTE CON UN OBJETO JSON VÁLIDO (sin texto antes ni después) con la siguiente estructura exacta:\n"
        "{\n"
        '  "anamnesis": "Motivo de consulta y enfermedad actual redactada formalmente (cronología, síntomas, antecedentes pertinentes)...",\n'
        '  "physical_exam": "Constantes vitales, examen físico por sistemas o hallazgos explorados...",\n'
        '  "diagnosis": "Diagnóstico clínico detallado (presuntivo o definitivo, justificación clínica)...",\n'
        '  "icd10_code": "Código CIE-10 (ej: N94.4, Z01.4, J00, etc.)",\n'
        '  "icd10_description": "Descripción oficial del código CIE-10",\n'
        '  "plan": "Conducta médica integral, recomendaciones terapéuticas, paraclínicos solicitados y pautas de control...",\n'
        '  "prescriptions": [\n'
        '     {\n'
        '       "medication": "Nombre comercial o principio activo",\n'
        '       "dosage": "Dosis / concentración (ej: 500 mg)",\n'
        '       "frequency": "Frecuencia (ej: Cada 8 horas)",\n'
        '       "duration": "Duración (ej: 7 días)",\n'
        '       "instructions": "Vía de administración y recomendaciones (ej: Vía oral tras alimentos)"\n'
        '     }\n'
        '  ],\n'
        '  "clinical_summary": "Breve resumen ejecutivo de 2 oraciones para orientación rápida del médico"\n'
        "}"
    )

    text_user_content = (
        f"FICHA CLÍNICA DE LA ATENCIÓN:\n"
        f"- Paciente: {patient_desc}\n"
        f"- Especialidad Médica: {doctor_specialty}\n"
        f"{reason_str}\n"
        f"{intake_str}\n\n"
        f"DOCUMENTOS Y EXÁMENES SUBIDOS:\n"
        f"{chr(10).join(doc_descriptions) if doc_descriptions else 'Sin documentos o imágenes anexas.'}\n\n"
        f"NOTAS ADICIONALES DEL MÉDICO:\n{payload.extra_notes or 'Sin notas adicionales.'}\n\n"
        f"TRANSCRIPCIÓN COMPLETA DE LA CONSULTA MÉDICO-PACIENTE:\n"
        f"{payload.transcript.strip()}"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Intentar primero con imágenes si las hay, o texto directo
    async def call_ai(include_images: bool):
        if include_images and image_parts:
            user_msg = [{"type": "text", "text": text_user_content}] + image_parts[:3]
        else:
            user_msg = text_user_content

        body = {
            "model": ai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.2,
            "max_tokens": 2000,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            return await client.post(api_url, json=body, headers=headers)

    try:
        res = await call_ai(include_images=bool(image_parts))
        if res.status_code != 200 and image_parts:
            # Si falló posiblemente por soporte de visión en el modelo, reintentar sólo con texto
            res = await call_ai(include_images=False)

        if res.status_code != 200:
            err_detail = res.text[:300]
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"Error del proveedor de IA ({res.status_code}): {err_detail}",
            )

        data = res.json()
        raw_text = ""
        if "choices" in data and len(data["choices"]) > 0:
            raw_text = data["choices"][0].get("message", {}).get("content", "").strip()
        elif "candidates" in data and len(data["candidates"]) > 0:
            raw_text = data["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
        elif "output" in data:
            raw_text = str(data["output"]).strip()
        elif "response" in data:
            raw_text = str(data["response"]).strip()
        else:
            raw_text = str(data)

        # Limpiar bloques de código markdown ```json ... ``` si existen
        clean_json_str = raw_text
        if "```" in clean_json_str:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_json_str)
            if match:
                clean_json_str = match.group(1).strip()

        try:
            parsed = json.loads(clean_json_str)
        except Exception:
            # Si el modelo no devolvió JSON puro, estructuramos fallback con el texto
            parsed = {
                "anamnesis": clean_json_str[:1000],
                "physical_exam": None,
                "diagnosis": "Diagnóstico en revisión médica",
                "icd10_code": None,
                "icd10_description": None,
                "plan": "Plan terapéutico según criterio del especialista",
                "prescriptions": [],
                "clinical_summary": "Resumen procesado por IA",
            }

        # Parsear prescripciones seguras
        prescriptions_list = []
        for p in parsed.get("prescriptions", []):
            if isinstance(p, dict) and p.get("medication"):
                prescriptions_list.append(
                    AIPrescriptionItem(
                        medication=str(p.get("medication", "")).strip(),
                        dosage=str(p.get("dosage", "")).strip() or "Dosis estándar",
                        frequency=str(p.get("frequency", "")).strip() or "Según indicación",
                        duration=str(p.get("duration", "")).strip() or "Duración clínica",
                        instructions=str(p.get("instructions", "")).strip() if p.get("instructions") else None,
                    )
                )

        return AIConsultationAssistResponse(
            anamnesis=str(parsed.get("anamnesis", "")).strip() or payload.transcript[:500],
            physical_exam=str(parsed.get("physical_exam", "")).strip() if parsed.get("physical_exam") else None,
            diagnosis=str(parsed.get("diagnosis", "")).strip() or "Evaluación clínica completada",
            icd10_code=str(parsed.get("icd10_code", "")).strip() if parsed.get("icd10_code") else None,
            icd10_description=str(parsed.get("icd10_description", "")).strip() if parsed.get("icd10_description") else None,
            plan=str(parsed.get("plan", "")).strip() or "Continuar controles habituales.",
            prescriptions=prescriptions_list,
            clinical_summary=str(parsed.get("clinical_summary", "")).strip() if parsed.get("clinical_summary") else None,
            provider="external_ai_gateway",
            tokens_used=data.get("usage", {}).get("total_tokens"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Fallo al procesar consulta con IA: {str(exc)}",
        )


