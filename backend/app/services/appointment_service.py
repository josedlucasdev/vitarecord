import datetime
import logging
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models.appointment import Appointment
from app.models.payment_record import PaymentRecord
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.dependent_repository import DependentRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.appointment import AppointmentCreate, AppointmentPublic

logger = logging.getLogger("appointment_service")


class AppointmentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.appointments = AppointmentRepository(db)
        self.payments = PaymentRepository(db)
        self.dependents = DependentRepository(db)
        self.users = UserRepository(db)

    async def _invalidate_redis_slots(self, doctor_id: str, target_dt: datetime.datetime) -> None:
        try:
            r = get_redis()
            date_str = target_dt.strftime("%Y-%m-%d")
            keys = await r.keys(f"slots:*:{doctor_id}:{date_str}")
            if keys:
                await r.delete(*keys)
        except Exception as exc:
            logger.warning("No se pudo invalidar cache en Redis: %s", exc)

    async def book_appointment(
        self, payload: AppointmentCreate, current_user: User
    ) -> AppointmentPublic:
        """Crea una cita médica garantizando exclusión mutua mediante bloqueo pesimista en MySQL."""
        # 1. Determinar paciente titular
        if current_user.role == "PATIENT":
            patient_id = current_user.id
        else:
            if not payload.patient_id:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Debe especificar el ID del paciente para agendar desde recepción.",
                )
            patient_id = payload.patient_id

        # 2. Validar paciente
        patient = await self.users.get_by_id(patient_id)
        if not patient:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Paciente no encontrado.")

        # 3. Validar médico y su verificación legal
        doctor = await self.users.get_by_id(payload.doctor_id)
        if not doctor or doctor.role != "DOCTOR":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Médico no encontrado.")

        if doctor.license_verification_status != "VERIFIED" or doctor.status != "ACTIVE":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "El médico no se encuentra verificado o activo en la plataforma.",
            )

        # 4. Validar familiar si aplica
        if payload.dependent_id:
            dep = await self.dependents.get_by_id(payload.dependent_id)
            if not dep or dep.guardian_user_id != patient_id:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "El familiar dependiente no pertenece al paciente titular.",
                )

        if payload.start_time >= payload.end_time:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "La hora de inicio debe ser anterior a la hora de fin.",
            )

        # 5. Adquisición atómica de cerrojos mutex en MySQL
        await self.appointments.acquire_locks(payload.doctor_id, payload.room_id)

        # 6. Comprobación segura de solapamientos
        conflicts = await self.appointments.find_conflicts(
            doctor_id=payload.doctor_id,
            room_id=payload.room_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
        if conflicts:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Conflicto de horario: el médico o el consultorio físico ya tienen una cita programada en ese rango horario.",
            )

        # 7. Máquina de estados: Si agenda el personal de la clínica -> PENDING_PATIENT_ACCEPTANCE
        #    Si agenda el propio paciente -> SCHEDULED o CONFIRMED
        if current_user.role in ("RECEPTIONIST", "CLINIC_ADMIN", "SUPERADMIN") and current_user.id != patient_id:
            initial_status = "PENDING_PATIENT_ACCEPTANCE"
        else:
            initial_status = "CONFIRMED"

        appointment = Appointment(
            clinic_id=payload.clinic_id,
            doctor_id=payload.doctor_id,
            patient_id=patient_id,
            dependent_id=payload.dependent_id,
            room_id=payload.room_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            status=initial_status,
            reason=payload.reason,
        )
        await self.appointments.create(appointment)

        # 8. Registro contable inicial (UNPAID)
        payment = PaymentRecord(
            appointment_id=appointment.id,
            clinic_id=payload.clinic_id,
            amount=payload.estimated_amount or Decimal("30.00"),
            currency=payload.currency or "USD",
            status="UNPAID",
        )
        await self.payments.create(payment)

        await self.db.commit()

        # 9. Invalidar caché en Redis
        await self._invalidate_redis_slots(payload.doctor_id, payload.start_time)

        fresh_app = await self.appointments.get_by_id(appointment.id)
        return self._to_public(fresh_app)

    async def accept_appointment(
        self, appointment_id: str, current_user: User
    ) -> AppointmentPublic:
        app = await self.appointments.get_by_id(appointment_id)
        if not app:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cita no encontrada.")

        if current_user.role == "PATIENT" and app.patient_id != current_user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes aceptar citas de otro paciente.")

        if app.status != "PENDING_PATIENT_ACCEPTANCE":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"La cita no se encuentra en espera de aceptación (estado actual: {app.status}).",
            )

        await self.appointments.update_status(appointment_id, "CONFIRMED")
        await self.db.commit()

        fresh = await self.appointments.get_by_id(appointment_id)
        return self._to_public(fresh)

    async def reject_appointment(
        self, appointment_id: str, current_user: User
    ) -> AppointmentPublic:
        """Rechazo soberano por el paciente: libera el slot al instante y pasa el cobro a EXEMPT."""
        app = await self.appointments.get_by_id(appointment_id)
        if not app:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cita no encontrada.")

        if current_user.role == "PATIENT" and app.patient_id != current_user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes rechazar citas de otro paciente.")

        if app.status != "PENDING_PATIENT_ACCEPTANCE":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"La cita no se encuentra en espera de aceptación (estado actual: {app.status}).",
            )

        await self.appointments.update_status(
            appointment_id, "REJECTED_BY_PATIENT", cancellation_reason="Rechazada por el paciente"
        )

        # Liberar pago asociado a EXEMPT
        pay_record = await self.payments.get_by_appointment_id(appointment_id)
        if pay_record:
            await self.payments.update_status(pay_record.id, "EXEMPT", notes="Cita rechazada por el paciente")

        await self.db.commit()

        # Invalidar caché en Redis para que el slot vuelva a verse libre de inmediato
        await self._invalidate_redis_slots(app.doctor_id, app.start_time)

        fresh = await self.appointments.get_by_id(appointment_id)
        return self._to_public(fresh)

    async def cancel_appointment(
        self, appointment_id: str, reason: str, current_user: User
    ) -> AppointmentPublic:
        """Cancelación oportuna: libera el slot al instante y pasa el cobro a VOID."""
        app = await self.appointments.get_by_id(appointment_id)
        if not app:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cita no encontrada.")

        # Control de permisos de cancelación
        if current_user.role == "PATIENT" and app.patient_id != current_user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes cancelar citas de otro paciente.")
        if current_user.role == "DOCTOR" and app.doctor_id != current_user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes cancelar citas de otro médico.")
        if current_user.role in ("RECEPTIONIST", "CLINIC_ADMIN") and app.clinic_id != current_user.clinic_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes cancelar citas de otra clínica.")

        if app.status in ("CANCELLED_BY_PATIENT", "CANCELLED_BY_DOCTOR", "CANCELLED_BY_CLINIC", "REJECTED_BY_PATIENT", "COMPLETED"):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"La cita ya se encuentra en estado inactivo o completado ({app.status}).",
            )

        if current_user.id == app.patient_id:
            cancel_status = "CANCELLED_BY_PATIENT"
        elif current_user.id == app.doctor_id:
            cancel_status = "CANCELLED_BY_DOCTOR"
        else:
            cancel_status = "CANCELLED_BY_CLINIC"

        await self.appointments.update_status(appointment_id, cancel_status, cancellation_reason=reason)

        # Cobro asociado pasa a VOID
        pay_record = await self.payments.get_by_appointment_id(appointment_id)
        if pay_record:
            await self.payments.update_status(pay_record.id, "VOID", notes=f"Cancelada: {reason}")

        await self.db.commit()

        # Invalidar caché en Redis para liberar el turno al instante
        await self._invalidate_redis_slots(app.doctor_id, app.start_time)

        fresh = await self.appointments.get_by_id(appointment_id)
        return self._to_public(fresh)

    async def list_appointments(
        self,
        current_user: User,
        clinic_id: str | None = None,
        doctor_id: str | None = None,
        patient_id: str | None = None,
        date: datetime.date | None = None,
        status: str | None = None,
    ) -> list[AppointmentPublic]:
        # Enforzar visibilidad según rol
        if current_user.role == "PATIENT":
            patient_id = current_user.id
        elif current_user.role == "DOCTOR":
            doctor_id = current_user.id
        elif current_user.role in ("RECEPTIONIST", "CLINIC_ADMIN"):
            if current_user.clinic_id:
                clinic_id = current_user.clinic_id

        items = await self.appointments.list_filtered(
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            patient_id=patient_id,
            date=date,
            status=status,
        )
        return [self._to_public(a) for a in items]

    def _to_public(self, app: Appointment) -> AppointmentPublic:
        pay = app.payment_record
        return AppointmentPublic(
            id=app.id,
            clinic_id=app.clinic_id,
            doctor_id=app.doctor_id,
            patient_id=app.patient_id,
            dependent_id=app.dependent_id,
            room_id=app.room_id,
            start_time=app.start_time,
            end_time=app.end_time,
            status=app.status,
            reason=app.reason,
            cancellation_reason=app.cancellation_reason,
            doctor_name=app.doctor.full_name if app.doctor else None,
            patient_name=app.patient.full_name if app.patient else None,
            clinic_name=app.clinic.name if app.clinic else None,
            room_name=app.room.name if app.room else None,
            payment_status=pay.status if pay else None,
            payment_amount=pay.amount if pay else None,
            currency=pay.currency if pay else None,
            created_at=app.created_at,
        )
