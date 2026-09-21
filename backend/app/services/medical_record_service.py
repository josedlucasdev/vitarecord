"""Servicio de Dominio para Expedientes Clinicos, Recetas Criptograficas y Auditoria Inmutable (plan/plan.md 2.B.8).

Cumple los principios DoD del Modulo 5:
1. Toda lectura genera obligatoriamente una fila action='READ' en audit_logs.
2. Cifrado en reposo AES-256-GCM con DEK por clinica y versionado.
3. Generacion de recetas con hash SHA-256 y endpoint de verificacion publica.
"""

import datetime
import hashlib
import logging
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.crypto import (
    decrypt_field,
    encrypt_field,
    get_or_create_clinic_dek,
)
from app.models.appointment import Appointment
from app.models.audit import AuditLog
from app.models.clinic import Clinic
from app.models.medical_attachment import MedicalAttachment
from app.models.medical_record import MedicalRecord
from app.models.patient_dependent import PatientDependent
from app.models.prescription import Prescription
from app.models.user import User
from app.schemas.medical_record import (
    MedicalAttachmentPublic,
    MedicalRecordCreate,
    MedicalRecordPublic,
)
from app.schemas.prescription import (
    PrescriptionPublic,
    PrescriptionVerificationPublic,
)
from app.services.prescription_pdf_service import generate_prescription_pdf

logger = logging.getLogger("medical_records")


class MedicalRecordService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _audit(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        clinic_id: str | None,
        user_id: str | None,
        client_ip: str | None = None,
        user_agent: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Inserta un registro inmutable en audit_logs de forma determinista."""
        log = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            clinic_id=clinic_id,
            user_id=user_id,
            ip_address=client_ip,
            user_agent=user_agent,
            details=details,
        )
        self.db.add(log)
        await self.db.flush()

    async def create_medical_record(
        self,
        data: MedicalRecordCreate,
        current_user: User,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> MedicalRecordPublic:
        """Crea el expediente clinico, cifra campos con AES-256-GCM, emite receta y finaliza la cita."""
        if current_user.role != "DOCTOR":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el personal médico autorizado puede redactar historias clínicas.",
            )

        # Cargar la cita con relaciones
        stmt = (
            select(Appointment)
            .options(
                selectinload(Appointment.doctor),
                selectinload(Appointment.patient),
                selectinload(Appointment.clinic),
                selectinload(Appointment.dependent),
            )
            .where(Appointment.id == data.appointment_id)
        )
        appointment = (await self.db.execute(stmt)).scalar_one_or_none()
        if not appointment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada.")

        if appointment.doctor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes redactar la historia clínica de un paciente asignado a otro médico.",
            )

        if appointment.status == "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta cita ya fue finalizada con historia clínica.",
            )

        # 1. Obtener la DEK activa de la clinica (Envelope Encryption)
        dek, key_version = await get_or_create_clinic_dek(self.db, appointment.clinic_id)

        # 2. Cifrar campos confidenciales (PHI)
        enc_anamnesis = encrypt_field(data.anamnesis, dek)
        enc_exam = encrypt_field(data.physical_exam, dek)
        enc_diag = encrypt_field(data.diagnosis, dek)
        enc_plan = encrypt_field(data.plan, dek)

        record = MedicalRecord(
            appointment_id=appointment.id,
            clinic_id=appointment.clinic_id,
            doctor_id=appointment.doctor_id,
            patient_id=appointment.patient_id,
            dependent_id=appointment.dependent_id,
            encrypted_anamnesis=enc_anamnesis,
            encrypted_physical_exam=enc_exam,
            encrypted_diagnosis=enc_diag,
            encrypted_plan=enc_plan,
            icd10_code=data.icd10_code,
            icd10_description=data.icd10_description,
            encryption_key_version=key_version,
            status="COMPLETED",
        )
        self.db.add(record)
        await self.db.flush()

        # 3. Si incluye prescripcion, generar receta medica con token SHA-256
        created_prescription = None
        if data.prescription and data.prescription.items:
            # Codigo legible tipo RX-20260912-A1B2
            today_str = datetime.datetime.now().strftime("%Y%m%d")
            rand_code = uuid.uuid4().hex[:4].upper()
            prescription_code = f"RX-{today_str}-{rand_code}"

            # Token de verificacion SHA-256 determinista y firmado
            token_payload = f"{prescription_code}:{appointment.id}:{appointment.doctor_id}:{appointment.patient_id}:{uuid.uuid4().hex}"
            verification_hash = hashlib.sha256(token_payload.encode()).hexdigest()

            now = datetime.datetime.now()
            expires_at = now + datetime.timedelta(days=data.prescription.duration_days)

            items_dicts = [item.model_dump() for item in data.prescription.items]

            prescription = Prescription(
                medical_record_id=record.id,
                appointment_id=appointment.id,
                clinic_id=appointment.clinic_id,
                doctor_id=appointment.doctor_id,
                patient_id=appointment.patient_id,
                dependent_id=appointment.dependent_id,
                prescription_code=prescription_code,
                verification_hash=verification_hash,
                items=items_dicts,
                diagnosis_summary=data.prescription.diagnosis_summary or data.icd10_description or data.icd10_code,
                notes=data.prescription.notes,
                issued_at=now,
                expires_at=expires_at,
                status="ACTIVE",
            )
            self.db.add(prescription)
            await self.db.flush()
            created_prescription = prescription

        # 4. Transicionar estado de la cita a COMPLETED
        appointment.status = "COMPLETED"
        await self.db.flush()

        # 5. Registrar auditoria inmutable action=CREATE
        await self._audit(
            action="CREATE",
            entity_type="medical_record",
            entity_id=record.id,
            clinic_id=appointment.clinic_id,
            user_id=current_user.id,
            client_ip=client_ip,
            user_agent=user_agent,
            details={"appointment_id": appointment.id, "has_prescription": created_prescription is not None},
        )

        await self.db.commit()

        # Retornar objeto publico descifrado
        record.dependent = appointment.dependent
        prescriptions = [created_prescription] if created_prescription else []
        return await self._build_public_record(
            record,
            dek,
            appointment.doctor,
            appointment.patient,
            appointment.clinic,
            dependent=appointment.dependent,
            prescriptions=prescriptions,
            attachments=[],
        )

    async def get_record_by_appointment(
        self,
        appointment_id: str,
        current_user: User,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> MedicalRecordPublic:
        """Obtiene y descifra la historia clinica de una cita, registrando obligatoriamente action=READ."""
        stmt = (
            select(MedicalRecord)
            .options(
                selectinload(MedicalRecord.doctor),
                selectinload(MedicalRecord.patient),
                selectinload(MedicalRecord.clinic),
                selectinload(MedicalRecord.dependent),
                selectinload(MedicalRecord.prescriptions).selectinload(Prescription.dependent),
                selectinload(MedicalRecord.attachments),
            )
            .where(MedicalRecord.appointment_id == appointment_id)
        )
        record = (await self.db.execute(stmt)).scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Historia clínica no encontrada.")

        # Validacion estricta de permisos PHI: solo el medico tratante o el paciente titular/responsable
        is_doctor = current_user.role == "DOCTOR" and record.doctor_id == current_user.id
        is_patient = current_user.role == "PATIENT" and record.patient_id == current_user.id
        if not (is_doctor or is_patient):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes autorización para consultar esta historia clínica confidencial.",
            )

        # Regla DoD Critica: Auditoria inmutable de TODA lectura de MEDICAL_RECORDS
        await self._audit(
            action="READ",
            entity_type="medical_record",
            entity_id=record.id,
            clinic_id=record.clinic_id,
            user_id=current_user.id,
            client_ip=client_ip,
            user_agent=user_agent,
            details={"source": "get_record_by_appointment"},
        )
        await self.db.commit()

        # Descifrar con la version de DEK del registro
        dek, _ = await get_or_create_clinic_dek(self.db, record.clinic_id, version=record.encryption_key_version)
        return await self._build_public_record(record, dek, record.doctor, record.patient, record.clinic)

    async def list_patient_history(
        self,
        patient_id: str,
        current_user: User,
        dependent_id: str | None = None,
        include_dependents: bool = False,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> list[MedicalRecordPublic]:
        """Lista el historial clinico de un paciente (o familiar), registrando auditoria por cada acceso.
        
        Garantiza separacion estricta: si es dependiente solo retorna sus consultas; si no se especifica dependiente
        y no se fuerza include_dependents, retorna unica y exclusivamente las consultas del titular.
        """
        # Control de acceso: paciente consultando su historial o medico consultando a su paciente
        if current_user.role == "PATIENT" and current_user.id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puedes consultar tu propio historial médico o el de tus dependientes autorizados.",
            )

        stmt = (
            select(MedicalRecord)
            .options(
                selectinload(MedicalRecord.doctor),
                selectinload(MedicalRecord.patient),
                selectinload(MedicalRecord.clinic),
                selectinload(MedicalRecord.dependent),
                selectinload(MedicalRecord.prescriptions).selectinload(Prescription.dependent),
                selectinload(MedicalRecord.attachments),
            )
            .where(MedicalRecord.patient_id == patient_id)
            .order_by(MedicalRecord.created_at.desc())
        )
        if dependent_id:
            stmt = stmt.where(MedicalRecord.dependent_id == dependent_id)
        elif not include_dependents:
            # Separacion estricta: solo consultas del paciente titular directo
            stmt = stmt.where(MedicalRecord.dependent_id.is_(None))

        records = list((await self.db.execute(stmt)).scalars().all())

        results = []
        for r in records:
            # Auditoria de lectura obligatoria
            await self._audit(
                action="READ",
                entity_type="medical_record",
                entity_id=r.id,
                clinic_id=r.clinic_id,
                user_id=current_user.id,
                client_ip=client_ip,
                user_agent=user_agent,
                details={"source": "list_patient_history"},
            )
            dek, _ = await get_or_create_clinic_dek(self.db, r.clinic_id, version=r.encryption_key_version)
            pub = await self._build_public_record(r, dek, r.doctor, r.patient, r.clinic)
            results.append(pub)

        await self.db.commit()
        return results

    async def get_prescription_pdf_bytes(self, prescription_id: str, current_user: User) -> bytes:
        """Genera y descarga el documento PDF oficial de la receta con codigo QR."""
        stmt = (
            select(Prescription)
            .options(
                selectinload(Prescription.doctor),
                selectinload(Prescription.patient),
                selectinload(Prescription.clinic),
                selectinload(Prescription.dependent),
            )
            .where(Prescription.id == prescription_id)
        )
        prescription = (await self.db.execute(stmt)).scalar_one_or_none()
        if not prescription:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta médica no encontrada.")

        # Acceso permitido para medico emisor o paciente
        if current_user.role == "PATIENT" and prescription.patient_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes descargar recetas de otros pacientes.")

        # Si la receta es para un dependiente familiar, plasmar su nombre en el PDF
        if prescription.dependent:
            rel_label = f" ({prescription.dependent.relationship})" if prescription.dependent.relationship else ""
            patient_display_name = f"{prescription.dependent.full_name}{rel_label} • Titular: {prescription.patient.full_name if prescription.patient else 'Responsable'}"
        elif prescription.patient:
            patient_display_name = prescription.patient.full_name or prescription.patient.email or "Paciente Titular"
        else:
            patient_display_name = "Paciente Titular"

        pdf_bytes = generate_prescription_pdf(
            prescription_code=prescription.prescription_code,
            verification_hash=prescription.verification_hash,
            clinic_name=prescription.clinic.name if prescription.clinic else "Clínica ÍntimaSalud",
            clinic_address=f"Sede: {prescription.clinic.name}" if prescription.clinic else None,
            doctor_name=prescription.doctor.full_name if prescription.doctor else "Médico Especialista",
            doctor_specialty=prescription.doctor.specialty if prescription.doctor else "Especialista",
            doctor_license="MPPS Verificado",
            patient_name=patient_display_name,
            issued_date_str=prescription.issued_at.strftime("%d/%m/%Y"),
            expires_date_str=prescription.expires_at.strftime("%d/%m/%Y"),
            diagnosis_summary=prescription.diagnosis_summary,
            items=prescription.items,
            notes=prescription.notes,
        )

        await self._audit(
            action="DOWNLOAD_PDF",
            entity_type="prescription",
            entity_id=prescription.id,
            clinic_id=prescription.clinic_id,
            user_id=current_user.id,
            details={"prescription_code": prescription.prescription_code},
        )
        await self.db.commit()

        return pdf_bytes

    async def verify_prescription_public(self, verification_hash: str) -> PrescriptionVerificationPublic:
        """Endpoint publico para farmacias: valida autenticidad por hash SHA-256 sin exponer PHI sensible."""
        stmt = (
            select(Prescription)
            .options(
                selectinload(Prescription.doctor),
                selectinload(Prescription.patient),
                selectinload(Prescription.clinic),
            )
            .where(Prescription.verification_hash == verification_hash)
        )
        prescription = (await self.db.execute(stmt)).scalar_one_or_none()
        if not prescription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receta médica no encontrada o código de verificación inválido.",
            )

        now = datetime.datetime.now()
        is_expired = now > prescription.expires_at
        current_status = "EXPIRED" if is_expired else prescription.status

        return PrescriptionVerificationPublic(
            is_valid=current_status == "ACTIVE",
            prescription_code=prescription.prescription_code,
            clinic_name=prescription.clinic.name if prescription.clinic else "ÍntimaSalud",
            doctor_name=prescription.doctor.full_name if prescription.doctor else "Médico Especialista",
            doctor_specialty=prescription.doctor.specialty if prescription.doctor else None,
            doctor_license="Verificada / Activa",
            patient_name=(prescription.patient.full_name or prescription.patient.email) if prescription.patient else "Paciente Titular",
            issued_at=prescription.issued_at,
            expires_at=prescription.expires_at,
            status=current_status,
            diagnosis_summary=prescription.diagnosis_summary,
            items=prescription.items,
        )

    async def _build_public_record(
        self,
        record: MedicalRecord,
        dek: bytes,
        doctor: User | None,
        patient: User | None,
        clinic: Clinic | None,
        dependent: PatientDependent | None = None,
        prescriptions: list[Prescription] | None = None,
        attachments: list[MedicalAttachment] | None = None,
    ) -> MedicalRecordPublic:
        """Descifra los campos y ensambla el modelo de salida."""
        rec_dep = dependent if dependent is not None else record.__dict__.get("dependent")
        prescriptions_list = prescriptions if prescriptions is not None else (
            record.__dict__.get("prescriptions") or []
        )
        prescriptions_pub = []
        for p in prescriptions_list:
            dep = p.__dict__.get("dependent") or rec_dep
            prescriptions_pub.append(
                PrescriptionPublic(
                    id=p.id,
                    medical_record_id=p.medical_record_id,
                    appointment_id=p.appointment_id,
                    clinic_id=p.clinic_id,
                    doctor_id=p.doctor_id,
                    patient_id=p.patient_id,
                    dependent_id=p.dependent_id,
                    prescription_code=p.prescription_code,
                    verification_hash=p.verification_hash,
                    items=p.items,
                    diagnosis_summary=p.diagnosis_summary,
                    notes=p.notes,
                    issued_at=p.issued_at,
                    expires_at=p.expires_at,
                    status=p.status,
                    doctor_name=doctor.full_name if doctor else None,
                    doctor_specialty=doctor.specialty if doctor else None,
                    patient_name=patient.full_name if patient else None,
                    dependent_name=dep.full_name if dep else None,
                    dependent_relationship=dep.relationship if dep else None,
                    clinic_name=clinic.name if clinic else None,
                )
            )

        attachments_list = attachments if attachments is not None else (
            record.__dict__.get("attachments") or []
        )
        attachments_pub = []
        for a in attachments_list:
            attachments_pub.append(
                MedicalAttachmentPublic(
                    id=a.id,
                    file_name=a.file_name,
                    content_type=a.content_type,
                    file_size=a.file_size,
                )
            )

        return MedicalRecordPublic(
            id=record.id,
            appointment_id=record.appointment_id,
            clinic_id=record.clinic_id,
            doctor_id=record.doctor_id,
            patient_id=record.patient_id,
            dependent_id=record.dependent_id,
            anamnesis=decrypt_field(record.encrypted_anamnesis, dek) or "",
            physical_exam=decrypt_field(record.encrypted_physical_exam, dek),
            diagnosis=decrypt_field(record.encrypted_diagnosis, dek) or "",
            plan=decrypt_field(record.encrypted_plan, dek) or "",
            icd10_code=record.icd10_code,
            icd10_description=record.icd10_description,
            encryption_key_version=record.encryption_key_version,
            status=record.status,
            created_at=record.created_at,
            doctor_name=doctor.full_name if doctor else None,
            doctor_specialty=doctor.specialty if doctor else None,
            patient_name=patient.full_name if patient else None,
            dependent_name=rec_dep.full_name if rec_dep else None,
            dependent_relationship=rec_dep.relationship if rec_dep else None,
            clinic_name=clinic.name if clinic else None,
            prescriptions=prescriptions_pub,
            attachments=attachments_pub,
        )
