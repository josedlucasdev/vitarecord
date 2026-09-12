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
from app.services.email_service import send_email

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

        html_body = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
            <h2 style="color: #0284c7;">Aviso de Personal Médico - {clinic.name}</h2>
            <p><strong>Médico:</strong> {doctor.full_name or doctor.email} ({doctor.email})</p>
            <p>{message_text}</p>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;" />
            <p style="font-size: 12px; color: #777;">Sistema de Gestión Clínica - ÍntimaSalud</p>
        </div>
        """

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
            doctor = User(
                email=request.email,
                full_name=request.full_name,
                phone=request.phone,
                role="DOCTOR",
                status="PENDING_ONBOARDING",
                specialty=request.specialty,
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
            invitation_link = f"http://localhost:9000/#/invitations/onboarding?token={token}"
            email_subject = f"Invitación de incorporación a {clinic.name} - ÍntimaSalud"
            email_html = f"""
            <div style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #0284c7;">Bienvenido al equipo médico de {clinic.name}</h2>
                <p>Estimado/a profesional {request.full_name or ''},</p>
                <p>Ha sido invitado/a a formar parte de la plantilla médica de <strong>{clinic.name}</strong> en la plataforma ÍntimaSalud.</p>
                <p>Para activar su cuenta, establecer su contraseña de acceso y registrar sus credenciales médicas, por favor ingrese en el siguiente enlace seguro (válido por 48 horas):</p>
                <p style="margin: 25px 0;">
                    <a href="{invitation_link}" style="background-color: #0284c7; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                        Completar Registro y Onboarding
                    </a>
                </p>
                <p style="font-size: 12px; color: #666;">Si no esperaba este correo, puede ignorarlo.</p>
            </div>
            """
        else:
            invitation_link = f"http://localhost:9000/#/invitations/respond?token={token}"
            email_subject = f"Nueva invitación de afiliación médica: {clinic.name}"
            email_html = f"""
            <div style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #0284c7;">Invitación de Afiliación Clínica</h2>
                <p>Estimado/a Dr./Dra. {doctor.full_name or doctor.email},</p>
                <p>La clínica <strong>{clinic.name}</strong> le ha invitado a unirse a su equipo médico en ÍntimaSalud.</p>
                <p>Puede responder directamente a esta solicitud haciendo clic en el siguiente enlace:</p>
                <p style="margin: 25px 0;">
                    <a href="{invitation_link}" style="background-color: #0284c7; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                        Ver y Responder Invitación
                    </a>
                </p>
                <p style="font-size: 12px; color: #666;">Este enlace expira en 48 horas.</p>
            </div>
            """

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

        return ValidateTokenResponse(
            valid=True,
            is_new_user=is_new_user,
            clinic_name=clinic.name,
            clinic_id=clinic.id,
            doctor_email=doctor.email,
            doctor_id=doctor.id,
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
        if request.specialty:
            doctor.specialty = request.specialty
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
