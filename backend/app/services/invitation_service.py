"""Servicio de Invitacion y Onboarding de Medicos (plan/plan.md seccion 2.B.2).

Implementa el ciclo completo:
- Caso A: Medico ya registrado -> Invitacion con token firmado -> Aceptar / Rechazar -> Notificacion inmediata a recepcion/admin.
- Caso B: Medico nuevo -> Usuario provisional -> Onboarding con password, perfil profesional y matricula -> PENDING_VERIFICATION.
"""

from datetime import datetime, timedelta, timezone
import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_invitation_token, decode_token, hash_password
from app.models.affiliation import DoctorClinicAffiliation
from app.core.config import settings
from app.models.clinic import Clinic
from app.models.user import DoctorScheduleLock, User
from app.repositories.affiliation_repository import AffiliationRepository
from app.repositories.clinic_repository import ClinicRepository
from app.repositories.user_repository import UserRepository
from app.schemas.invitation import (
    CompleteOnboardingRequest,
    CreateInvitationRequest,
    InvitationResponse,
    ValidateTokenResponse,
)
from app.services.email_service import build_branded_email_html, send_email

logger = logging.getLogger("invitation_service")


class InvitationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.affiliations = AffiliationRepository(db)
        self.clinics = ClinicRepository(db)

    async def _notify_clinic_staff(self, clinic: Clinic, doctor: User, subject: str, message_text: str) -> None:
        """Notifica por email a recepcionistas y administradores de la clinica."""
        stmt = select(User).where(User.role.in_(["RECEPTIONIST", "CLINIC_ADMIN", "SUPERADMIN"]))
        result = await self.db.execute(stmt)
        staff_members = result.scalars().all()

        html_body = build_branded_email_html(
            title=f"Aviso de Personal Médico - {clinic.name}",
            subtitle="Actualización operativa en la plantilla asistencial.",
            content_html=f"Se ha registrado una novedad respecto al profesional médico:<br/><br/>{message_text}",
            details_table=[
                ("Clínica / Sede", clinic.name),
                ("Médico Especialista", doctor.full_name or doctor.email),
                ("Correo Electrónico", doctor.email),
            ],
        )

        for staff in staff_members:
            try:
                await send_email(staff.email, f"[{clinic.name}] {subject}", html_body)
            except Exception as e:
                logger.warning("No se pudo notificar al personal %s: %s", staff.email, e)

    async def invite_doctor(
        self, clinic_id: str, request: CreateInvitationRequest, inviting_user: User | None = None
    ) -> InvitationResponse:
        clinic = await self.clinics.get_by_id(clinic_id)
        if not clinic:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Clínica no encontrada")

        doctor = await self.users.get_by_email(request.email)
        is_new_user = doctor is None

        if is_new_user:
            # Caso B: Crear usuario provisional
            specs = request.specialties
            if specs is not None:
                spec_str = ", ".join(specs) if specs else None
            else:
                spec_str = request.specialty
                specs = [s.strip() for s in spec_str.split(",") if s.strip()] if spec_str else []

            doctor = User(
                email=request.email,
                phone=request.phone,
                full_name=request.full_name,
                role="DOCTOR",
                status="PENDING_ONBOARDING",
                specialty=spec_str,
                specialties=specs,
                license_verification_status="NOT_APPLICABLE",
                mfa_enabled=False,
            )
            await self.users.create(doctor)

            # Fila mutex obligatoria para agendamiento transversal (plan/plan.md 2.B.4)
            schedule_lock = DoctorScheduleLock(doctor_id=doctor.id)
            self.db.add(schedule_lock)
            await self.db.flush()
        else:
            if doctor.role != "DOCTOR":
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"El usuario existe pero tiene el rol {doctor.role}, no puede ser afiliado como médico.",
                )

        # Verificar si ya existe afiliación
        affiliation = await self.affiliations.get_by_doctor_and_clinic(doctor.id, clinic_id)
        if affiliation:
            if affiliation.status == "ACTIVE":
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, "El médico ya se encuentra activo en esta clínica."
                )
        else:
            affiliation = DoctorClinicAffiliation(
                doctor_id=doctor.id,
                clinic_id=clinic_id,
                status="INVITED",
            )
            await self.affiliations.create(affiliation)

        # Generar token de invitación firmado
        token = create_invitation_token(doctor.id, clinic_id)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
        affiliation.invitation_token = token
        affiliation.invitation_expires_at = expires_at.replace(tzinfo=None)
        affiliation.status = "INVITED"

        await self.db.commit()

        # Enlace para responder o completar onboarding
        if is_new_user:
            invitation_link = f"{settings.FRONTEND_URL}/#/invitations/onboarding?token={token}"
            email_subject = f"Invitación de incorporación a {clinic.name} - VitaRecord"
            email_html = build_branded_email_html(
                title=f"Bienvenido/a al equipo de {clinic.name}",
                subtitle="Ha recibido una invitación formal para incorporarse a la plantilla médica.",
                content_html=(
                    f"Estimado/a profesional <strong>{request.full_name or ''}</strong>,<br/><br/>"
                    f"Ha sido invitado/a a formar parte de la plantilla médica de <strong>{clinic.name}</strong> "
                    f"en la plataforma clínica <strong>VitaRecord</strong>.<br/>"
                    f"Para activar su cuenta, establecer su contraseña de acceso y registrar sus credenciales "
                    f"y matrícula médica, por favor ingrese en el siguiente enlace seguro:"
                ),
                cta_text="Completar Registro y Onboarding Médico",
                cta_link=invitation_link,
                details_table=[
                    ("Institución / Clínica", clinic.name),
                    ("Profesional", request.full_name or request.email),
                    ("Especialidad", request.specialty or "Medicina General"),
                ],
                alert_box="Este enlace es seguro, intransferible y tiene una vigencia de 48 horas.",
            )
        else:
            invitation_link = f"{settings.FRONTEND_URL}/#/invitations/respond?token={token}"
            email_subject = f"Nueva invitación de afiliación médica: {clinic.name} - VitaRecord"
            email_html = build_branded_email_html(
                title="Invitación de Afiliación Clínica",
                subtitle=f"La sede {clinic.name} le ha invitado a unirse a su equipo médico.",
                content_html=(
                    f"Estimado/a Dr./Dra. <strong>{doctor.full_name or doctor.email}</strong>,<br/><br/>"
                    f"La clínica <strong>{clinic.name}</strong> le ha invitado a afiliarse formalmente a su equipo "
                    f"médico en <strong>VitaRecord</strong>.<br/>"
                    f"Puede responder directamente a esta solicitud de afiliación haciendo clic en el siguiente botón:"
                ),
                cta_text="Ver y Responder Invitación",
                cta_link=invitation_link,
                details_table=[
                    ("Institución / Clínica", clinic.name),
                    ("Médico Especialista", doctor.full_name or doctor.email),
                ],
                alert_box="Enlace seguro e intransferible. Válido durante 48 horas.",
            )

        await send_email(doctor.email, email_subject, email_html)

        return InvitationResponse(
            affiliation_id=affiliation.id,
            doctor_id=doctor.id,
            clinic_id=clinic.id,
            status=affiliation.status,
            is_new_user=is_new_user,
            invitation_link=invitation_link,
            expires_at=expires_at.isoformat(),
        )

    async def validate_invitation_token(self, token: str) -> ValidateTokenResponse:
        try:
            payload = decode_token(token)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token de invitación inválido o expirado") from exc

        if payload.get("type") != "doctor_invitation":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tipo de token inválido")

        doctor_id = payload.get("sub")
        clinic_id = payload.get("clinic_id")

        affiliation = await self.affiliations.get_by_token(token)
        if not affiliation or affiliation.status != "INVITED":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "La invitación no es válida o ya ha sido respondida"
            )

        if (
            affiliation.invitation_expires_at
            and affiliation.invitation_expires_at < datetime.now(timezone.utc).replace(tzinfo=None)
        ):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "La invitación ha expirado")

        clinic = await self.clinics.get_by_id(clinic_id)
        doctor = await self.users.get_by_id(doctor_id)
        if not clinic or not doctor:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Datos de la invitación no encontrados")

        is_new_user = doctor.status == "PENDING_ONBOARDING" or doctor.hashed_password is None

        raw_specs = getattr(doctor, "specialties", None)
        specs: list[str] = []
        if isinstance(raw_specs, list):
            specs = [str(s).strip() for s in raw_specs if s]
        elif doctor.specialty:
            specs = [s.strip() for s in doctor.specialty.split(",") if s.strip()]

        return ValidateTokenResponse(
            valid=True,
            is_new_user=is_new_user,
            clinic_name=clinic.name,
            clinic_id=clinic.id,
            doctor_email=doctor.email,
            doctor_id=doctor.id,
            full_name=doctor.full_name,
            specialty=doctor.specialty,
            specialties=specs,
        )

    async def respond_invitation(self, token: str, action: str) -> dict:
        """Caso A: Medico con cuenta previa acepta o rechaza."""
        if action not in ("ACCEPT", "REJECT"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Acción debe ser ACCEPT o REJECT")

        validation = await self.validate_invitation_token(token)
        affiliation = await self.affiliations.get_by_token(token)
        clinic = await self.clinics.get_by_id(validation.clinic_id)
        doctor = await self.users.get_by_id(validation.doctor_id)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        affiliation.responded_at = now
        affiliation.invitation_token = None

        if action == "ACCEPT":
            # Si el médico ya tiene matrícula verificada previamente, se activa directamente.
            # De lo contrario queda en INVITED_PENDING_VERIFICATION
            if doctor.license_verification_status == "VERIFIED":
                affiliation.status = "ACTIVE"
            else:
                affiliation.status = "INVITED_PENDING_VERIFICATION"
            status_text = "ha ACEPTADO la invitación de afiliación."
        else:
            affiliation.status = "REJECTED"
            status_text = "ha RECHAZADO la invitación de afiliación."

        await self.db.commit()

        # Notificacion inmediata obligatoria a Recepcion y Administradores
        await self._notify_clinic_staff(
            clinic=clinic,
            doctor=doctor,
            subject=f"Respuesta a invitación médica: {doctor.full_name or doctor.email} ({action})",
            message_text=f"El Dr./Dra. {doctor.full_name or doctor.email} {status_text}",
        )

        return {
            "status": affiliation.status,
            "action": action,
            "message": f"Invitación procesada exitosamente ({action}).",
        }

    async def complete_onboarding(self, request: CompleteOnboardingRequest) -> dict:
        """Caso B: Medico nuevo define contrasena, perfil y acepta vinculacion."""
        validation = await self.validate_invitation_token(request.token)
        affiliation = await self.affiliations.get_by_token(request.token)
        clinic = await self.clinics.get_by_id(validation.clinic_id)
        doctor = await self.users.get_by_id(validation.doctor_id)

        # Asignar credenciales y perfil
        doctor.hashed_password = hash_password(request.password)
        if request.full_name:
            doctor.full_name = request.full_name
        if request.specialties is not None:
            doctor.specialties = request.specialties
            doctor.specialty = ", ".join(request.specialties) if request.specialties else None
        elif request.specialty:
            doctor.specialty = request.specialty
            doctor.specialties = [s.strip() for s in request.specialty.split(",") if s.strip()]
        if request.license_number:
            doctor.license_number = request.license_number
        if request.biography:
            doctor.biography = request.biography

        # Regla de Dominio 2.B.2: Un medico nunca pasa a ACTIVE directamente tras onboarding,
        # pasa a PENDING_VERIFICATION requiriendo revision de matricula.
        doctor.status = "PENDING_VERIFICATION"
        doctor.license_verification_status = "PENDING_VERIFICATION"
        doctor.is_available_for_emergencies = False

        # Afiliacion vinculada
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        affiliation.status = "INVITED_PENDING_VERIFICATION"
        affiliation.responded_at = now
        affiliation.invitation_token = None

        await self.db.commit()

        # Notificar a Recepcion y Administradores
        await self._notify_clinic_staff(
            clinic=clinic,
            doctor=doctor,
            subject=f"Médico completó Onboarding: {doctor.full_name or doctor.email}",
            message_text=(
                f"El Dr./Dra. {doctor.full_name or doctor.email} ha completado su registro inicial y "
                f"ha aceptado la vinculación a {clinic.name}. Su matrícula profesional ({doctor.license_number or 'Pendiente'}) "
                f"se encuentra pendiente de verificación formal."
            ),
        )

        return {
            "status": doctor.status,
            "message": "Onboarding completado exitosamente. Tu cuenta está en proceso de verificación de matrícula.",
        }
