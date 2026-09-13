"""Usuarios, sesiones y su fila mutex como medico (plan/plan.md seccion 2.A, 2.B.2, 2.B.4, 2.B.9)."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_uuid

# Roles validos. Se aplica a nivel de aplicacion (Pydantic/servicio); el
# ENUM nativo de MySQL se evita para no requerir migraciones en cada
# ampliacion de roles.
ROLES = ("SUPERADMIN", "MODERATOR", "COMPLIANCE_REVIEWER", "CLINIC_ADMIN", "DOCTOR", "RECEPTIONIST", "PATIENT")

USER_STATUSES = ("PENDING_ONBOARDING", "PENDING_VERIFICATION", "ACTIVE", "SUSPENDED", "DEACTIVATED")

LICENSE_VERIFICATION_STATUSES = ("NOT_APPLICABLE", "PENDING_VERIFICATION", "VERIFIED", "REJECTED")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_ONBOARDING")
    clinic_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("clinics.id"), index=True)

    # Perfil profesional (medicos)
    specialty: Mapped[str | None] = mapped_column(String(100))
    license_number: Mapped[str | None] = mapped_column(String(100))
    biography: Mapped[str | None] = mapped_column(String(1000))
    profile_picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    academic_degrees: Mapped[list | None] = mapped_column(JSON, default=list)
    work_experience: Mapped[list | None] = mapped_column(JSON, default=list)
    is_public_profile_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Verificacion de matricula profesional (plan/plan.md seccion 2.B.2).
    # Un medico NUNCA pasa a ACTIVE / disponible para emergencias sin que
    # esto sea VERIFIED por un SUPERADMIN o COMPLIANCE_REVIEWER.
    license_verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="NOT_APPLICABLE")
    license_document_url: Mapped[str | None] = mapped_column(String(500))
    verified_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)

    preferred_notification_channels: Mapped[list | None] = mapped_column(JSON, default=list)

    no_show_strikes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_restricted_booking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(64))
    mfa_recovery_codes_hash: Mapped[str | None] = mapped_column(String(255))

    # Solo puede ser true si license_verification_status == VERIFIED;
    # esa regla se aplica en app/services (nunca solo a nivel de columna).
    is_available_for_emergencies: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Datos complementarios de paciente
    identification_number: Mapped[str | None] = mapped_column(String(32))
    birth_date: Mapped[datetime | None] = mapped_column(DateTime)
    gender: Mapped[str | None] = mapped_column(String(16))
    address: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100), default="Venezuela")


class RefreshToken(Base):
    """Sesion / refresh token con soporte de rotacion y deteccion de reuso
    (plan/plan.md seccion 2.B.9)."""

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    device_info: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    replaced_by_token_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("refresh_tokens.id"))


class DoctorScheduleLock(Base):
    """Fila mutex sin datos de negocio para el medico (plan/plan.md seccion 2.B.4)."""

    __tablename__ = "doctor_schedule_locks"

    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
