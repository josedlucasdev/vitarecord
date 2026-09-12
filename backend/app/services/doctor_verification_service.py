"""Servicio de Verificacion de Matricula Profesional y Auditoria (plan/plan.md seccion 2.B.2 y 2.B.8)."""

from datetime import datetime, timezone
import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.affiliation import DoctorClinicAffiliation
from app.models.clinic import Clinic
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.core.config import settings
from app.repositories.clinic_repository import ClinicRepository
from app.repositories.user_repository import UserRepository
from app.schemas.doctor_verification import (
    DoctorPendingVerificationPublic,
    VerifyDoctorRequest,
    VerifyDoctorResponse,
)
from app.services.email_service import build_branded_email_html, send_email

logger = logging.getLogger("doctor_verification_service")


class DoctorVerificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.clinics = ClinicRepository(db)
        self.audit = AuditRepository(db)

    def _ensure_reviewer_permission(self, reviewer: User) -> None:
        if reviewer.role not in ("SUPERADMIN", "COMPLIANCE_REVIEWER"):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Permisos insuficientes. Se requiere rol SUPERADMIN o COMPLIANCE_REVIEWER.",
            )

    async def list_pending(self, reviewer: User) -> list[User]:
        self._ensure_reviewer_permission(reviewer)

        stmt = (
            select(User)
            .where(
                User.role == "DOCTOR",
                User.license_verification_status == "PENDING_VERIFICATION",
            )
            .order_by(User.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def verify_doctor(
        self,
        doctor_id: str,
        request: VerifyDoctorRequest,
        reviewer: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> VerifyDoctorResponse:
        self._ensure_reviewer_permission(reviewer)

        if request.action not in ("APPROVE", "REJECT"):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Acción debe ser APPROVE o REJECT."
            )

        doctor = await self.users.get_by_id(doctor_id)
        if not doctor or doctor.role != "DOCTOR":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Médico no encontrado.")

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        doctor.verified_by_user_id = reviewer.id
        doctor.verified_at = now

        if request.document_url:
            doctor.license_document_url = request.document_url

        if request.action == "APPROVE":
            doctor.license_verification_status = "VERIFIED"
            doctor.status = "ACTIVE"

            # Actualizar afiliaciones pendientes a ACTIVE
            stmt = select(DoctorClinicAffiliation).where(
                DoctorClinicAffiliation.doctor_id == doctor.id,
                DoctorClinicAffiliation.status.in_(["INVITED_PENDING_VERIFICATION", "INVITED"]),
            )
            res_aff = await self.db.execute(stmt)
            for aff in res_aff.scalars().all():
                aff.status = "ACTIVE"

            # Registrar en audit_logs
            await self.audit.log_event(
                action="DOCTOR_VERIFICATION_APPROVE",
                entity_type="USER",
                entity_id=doctor.id,
                user_id=reviewer.id,
                details={
                    "action": "APPROVE",
                    "reason": request.reason or "Matrícula profesional validada formalmente",
                    "license_number": doctor.license_number,
                    "document_url": doctor.license_document_url,
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )

            await self.db.commit()

            # Notificar al médico por correo
            email_html = build_branded_email_html(
                title="¡Matrícula Profesional Verificada con Éxito!",
                subtitle="Su expediente médico ha sido acreditado por el comité de cumplimiento institucional.",
                content_html=(
                    f"Estimado/a Dr./Dra. <strong>{doctor.full_name or doctor.email}</strong>,<br/><br/>"
                    f"Nos complace informarle que su matrícula médica (<strong>{doctor.license_number}</strong>) "
                    f"ha sido verificada y aprobada por el comité de cumplimiento de <strong>VitaRecord</strong>.<br/>"
                    f"Su cuenta profesional ha sido activada y sus vinculaciones clínicas están operativas para "
                    f"atender citas médicas y emitir recetas electrónicas oficiales con código QR."
                ),
                cta_text="Ingresar a Mi Portal Médico",
                cta_link=f"{settings.FRONTEND_URL}/#/login",
                details_table=[
                    ("Profesional Médico", doctor.full_name or doctor.email),
                    ("Matrícula Verificada", doctor.license_number or "Acreditada"),
                    ("Especialidad", doctor.specialty or "Medicina General"),
                    ("Estado", "Verificado y Habilitado"),
                ],
                alert_box="Su firma y credenciales constan debidamente registradas para la emisión de recetas médicas oficiales y expedientes clínicos.",
            )
            await send_email(doctor.email, "Matrícula Médica Verificada y Aprobada - VitaRecord", email_html)

            # Notificar al personal de la clínica
            stmt_staff = select(User).where(User.role.in_(["RECEPTIONIST", "CLINIC_ADMIN"]))
            staff_res = await self.db.execute(stmt_staff)
            for staff in staff_res.scalars().all():
                staff_html = build_branded_email_html(
                    title="Médico Verificado en Plantilla",
                    subtitle="Nuevo profesional médico habilitado para consultas.",
                    content_html=(
                        f"El Dr./Dra. <strong>{doctor.full_name or doctor.email}</strong> "
                        f"(Matrícula: <strong>{doctor.license_number}</strong>) ha completado satisfactoriamente "
                        f"la auditoría de credenciales y ha sido activado en la plataforma."
                    ),
                    details_table=[
                        ("Médico", doctor.full_name or doctor.email),
                        ("Matrícula Profesional", doctor.license_number or "N/A"),
                        ("Especialidad", doctor.specialty or "General"),
                    ],
                )
                await send_email(staff.email, f"Médico Activado: {doctor.full_name or doctor.email}", staff_html)

            return VerifyDoctorResponse(
                doctor_id=doctor.id,
                status=doctor.status,
                license_verification_status=doctor.license_verification_status,
                action="APPROVE",
                message="Médico verificado y activado exitosamente.",
            )

        else:
            doctor.license_verification_status = "REJECTED"
            # Registrar en audit_logs
            await self.audit.log_event(
                action="DOCTOR_VERIFICATION_REJECT",
                entity_type="USER",
                entity_id=doctor.id,
                user_id=reviewer.id,
                details={
                    "action": "REJECT",
                    "reason": request.reason or "Documentación o número de colegiatura no coincidente",
                    "license_number": doctor.license_number,
                    "document_url": doctor.license_document_url,
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )

            await self.db.commit()

            # Notificar al médico por correo con motivo
            email_html = build_branded_email_html(
                title="Aviso sobre Verificación de Matrícula Profesional",
                subtitle="Observaciones del comité de cumplimiento médico.",
                content_html=(
                    f"Estimado/a Dr./Dra. <strong>{doctor.full_name or doctor.email}</strong>,<br/><br/>"
                    f"El comité de cumplimiento ha revisado el registro de su matrícula profesional "
                    f"(<strong>{doctor.license_number}</strong>) y no fue posible validarlo de forma concluyente.<br/><br/>"
                    f"<strong>Motivo indicado:</strong> {request.reason or 'Documentación insuficiente o datos no concordantes'}.<br/><br/>"
                    f"Por favor ingrese a su portal o contacte al equipo de soporte para subsanar los recaudos requeridos."
                ),
                cta_text="Acceder al Portal Médico",
                cta_link=f"{settings.FRONTEND_URL}/#/login",
                details_table=[
                    ("Profesional", doctor.full_name or doctor.email),
                    ("Matrícula Registrada", doctor.license_number or "N/A"),
                    ("Dictamen", "Observado / Subsanación requerida"),
                ],
                alert_box="Puede volver a cargar una copia legible de su carnet de colegiatura o certificación médica vigente.",
            )
            await send_email(doctor.email, "Observación sobre Verificación de Matrícula - VitaRecord", email_html)

            return VerifyDoctorResponse(
                doctor_id=doctor.id,
                status=doctor.status,
                license_verification_status=doctor.license_verification_status,
                action="REJECT",
                message="Matrícula médica rechazada y registrada en auditoría.",
            )

    async def toggle_emergency_availability(
        self, doctor_id: str, is_available: bool, current_user: User
    ) -> dict:
        """Regla de dominio (plan.md 2.B.2): un medico NO puede activarse para emergencias si no esta VERIFIED."""
        doctor = await self.users.get_by_id(doctor_id)
        if not doctor or doctor.role != "DOCTOR":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Médico no encontrado.")

        # Solo el propio medico o un superadmin puede cambiar su disponibilidad
        if current_user.id != doctor.id and current_user.role not in ("SUPERADMIN", "CLINIC_ADMIN"):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para modificar esta disponibilidad.")

        if is_available and doctor.license_verification_status != "VERIFIED":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Bloqueo de seguridad: No es posible activar disponibilidad de emergencias sin contar con matrícula médica verificada.",
            )

        doctor.is_available_for_emergencies = is_available
        await self.db.commit()

        return {
            "doctor_id": doctor.id,
            "is_available_for_emergencies": doctor.is_available_for_emergencies,
            "license_verification_status": doctor.license_verification_status,
        }
