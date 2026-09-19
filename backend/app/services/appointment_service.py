import datetime
import logging
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select
from app.core.config import settings
from app.core.redis import get_redis
from app.core.security import create_patient_invitation_token
from app.models.affiliation import DoctorClinicAffiliation
from app.models.appointment import Appointment
from app.models.payment_record import PaymentRecord
from app.models.procedure import AppointmentProcedure, MedicalProcedure
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.clinic_repository import ClinicRepository
from app.repositories.dependent_repository import DependentRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.room_repository import RoomRepository
from app.repositories.user_repository import UserRepository
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentPublic,
    PublicAppointmentCreate,
)
from app.schemas.procedure import (
    AppointmentProcedureCreate,
    AppointmentProcedurePublic,
)
from app.services.availability_service import is_room_open_at, is_specialty_compatible
from app.services.email_service import build_branded_email_html, send_email


logger = logging.getLogger("appointment_service")


class AppointmentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.appointments = AppointmentRepository(db)
        self.payments = PaymentRepository(db)
        self.dependents = DependentRepository(db)
        self.users = UserRepository(db)
        self.clinics = ClinicRepository(db)
        self.rooms = RoomRepository(db)

    async def _invalidate_redis_slots(self, clinic_id: str, doctor_id: str, target_dt: datetime.datetime) -> None:
        try:
            r = get_redis()
            date_str = target_dt.strftime("%Y-%m-%d")
            keys_doc = await r.keys(f"slots:*:{doctor_id}:{date_str}")
            keys_clinic = await r.keys(f"slots:{clinic_id}:*:{date_str}")
            all_keys = set(keys_doc + keys_clinic)
            if all_keys:
                await r.delete(*all_keys)
        except Exception as exc:
            logger.warning("No se pudo invalidar cache en Redis: %s", exc)

    async def _resolve_and_lock_room(
        self,
        clinic_id: str,
        doctor: User,
        requested_room_id: str | None,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
    ) -> str:
        """Valida o asigna automáticamente un consultorio compatible y adquiere cerrojo mutex."""
        if requested_room_id:
            room = await self.rooms.get_by_id(requested_room_id)
            if not room or room.clinic_id != clinic_id:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Consultorio no encontrado en esta clínica.")
            if not room.is_active or getattr(room, "status", "ACTIVE") != "ACTIVE":
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"El consultorio '{room.name}' se encuentra en {getattr(room, 'status', 'inactivo')} y no admite reservas.",
                )
            if not is_specialty_compatible(doctor.specialty, getattr(room, "specialty", None)):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"El consultorio '{room.name}' ({room.specialty or 'Polivalente'}) no es compatible con la especialidad del médico ({doctor.specialty}).",
                )
            selected_room_id = room.id
        else:
            clinic_rooms = await self.rooms.list_by_clinic(clinic_id, active_only=True)
            active_rooms = [r for r in clinic_rooms if getattr(r, "status", "ACTIVE") == "ACTIVE"]
            compatible_rooms = [
                r for r in active_rooms
                if is_specialty_compatible(doctor.specialty, getattr(r, "specialty", None))
            ]
            if not compatible_rooms:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"La sede no cuenta con consultorios operativos compatibles con la especialidad '{doctor.specialty or 'General'}'.",
                )

            day_of_week = start_time.weekday()
            assigned_room = None
            for cand_room in compatible_rooms:
                if not is_room_open_at(cand_room, start_time.time(), end_time.time(), day_of_week):
                    continue
                conflicts = await self.appointments.find_conflicts(
                    doctor_id=doctor.id,
                    room_id=cand_room.id,
                    start_time=start_time,
                    end_time=end_time,
                )
                room_conflicts = [c for c in conflicts if c.room_id == cand_room.id]
                if not room_conflicts:
                    assigned_room = cand_room
                    break

            if not assigned_room:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "No hay consultorios disponibles en esta sede para la especialidad solicitada en ese horario.",
                )
            selected_room_id = assigned_room.id

        await self.appointments.acquire_locks(doctor.id, selected_room_id)

        conflicts = await self.appointments.find_conflicts(
            doctor_id=doctor.id,
            room_id=selected_room_id,
            start_time=start_time,
            end_time=end_time,
        )
        if conflicts:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Conflicto de horario: el médico o el consultorio físico ya tienen una cita programada en ese rango horario.",
            )

        return selected_room_id

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

        # 5. Adquisición atómica de cerrojos mutex y resolución de consultorio físico compatible
        selected_room_id = await self._resolve_and_lock_room(
            clinic_id=payload.clinic_id,
            doctor=doctor,
            requested_room_id=payload.room_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )

        # 6. Máquina de estados: Si agenda el personal de la clínica -> PENDING_PATIENT_ACCEPTANCE
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
            room_id=selected_room_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            status=initial_status,
            reason=payload.reason,
        )
        await self.appointments.create(appointment)

        # 7. Obtener tarifa de consulta del médico en la sede y registrar procedimientos
        aff_stmt = select(DoctorClinicAffiliation).where(
            DoctorClinicAffiliation.doctor_id == payload.doctor_id,
            DoctorClinicAffiliation.clinic_id == payload.clinic_id,
            DoctorClinicAffiliation.status == "ACTIVE",
        )
        aff = (await self.db.execute(aff_stmt)).scalar_one_or_none()
        base_fee = aff.consultation_fee if (aff and aff.consultation_fee is not None) else Decimal("30.00")
        curr = aff.currency if (aff and aff.currency) else (payload.currency or "USD")

        procedures_total = Decimal("0.00")
        if payload.procedure_ids:
            p_stmt = select(MedicalProcedure).where(MedicalProcedure.id.in_(payload.procedure_ids))
            selected_procs = list((await self.db.execute(p_stmt)).scalars().all())
            for sp in selected_procs:
                ap = AppointmentProcedure(
                    appointment_id=appointment.id,
                    procedure_id=sp.id,
                    name=sp.name,
                    price=sp.price,
                    currency=sp.currency,
                )
                self.db.add(ap)
                procedures_total += sp.price

        total_amount = base_fee + procedures_total

        # Registro contable inicial (UNPAID)
        payment = PaymentRecord(
            appointment_id=appointment.id,
            clinic_id=payload.clinic_id,
            amount=total_amount,
            currency=curr,
            status="UNPAID",
        )
        await self.payments.create(payment)

        await self.db.commit()


        # 8. Invalidar caché en Redis para el médico y toda la clínica
        await self._invalidate_redis_slots(payload.clinic_id, payload.doctor_id, payload.start_time)

        fresh_app = await self.appointments.get_by_id(appointment.id)

        # 9. Notificación multicanal interactiva (Módulo 6 / 2.B.5)
        try:
            from app.services.notification_service import NotificationService
            notif_service = NotificationService(self.db)
            clinic_name = fresh_app.clinic.name if (fresh_app and fresh_app.clinic) else "ÍntimaSalud"
            if initial_status == "PENDING_PATIENT_ACCEPTANCE":
                await notif_service.send_appointment_proposal(
                    appointment=fresh_app,
                    patient=patient,
                    doctor=doctor,
                    clinic_name=clinic_name,
                )
            else:
                # Cita confirmada agendada directamente: Notificar al médico en tiempo real
                await notif_service.send_new_appointment_to_doctor(
                    appointment=fresh_app,
                    doctor=doctor,
                    patient=patient,
                    clinic_name=clinic_name,
                    is_pending_approval=False,
                )
        except Exception as exc:
            logger.warning("No se pudo despachar notificación de cita: %s", exc)

        return self._to_public(fresh_app)

    async def get_appointment(self, appointment_id: str, current_user: User) -> AppointmentPublic:
        app = await self.appointments.get_by_id(appointment_id)
        if not app:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cita no encontrada.")
        return self._to_public(app)

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
        await self._invalidate_redis_slots(app.clinic_id, app.doctor_id, app.start_time)

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
        await self._invalidate_redis_slots(app.clinic_id, app.doctor_id, app.start_time)

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

    async def public_book_appointment(
        self, payload: PublicAppointmentCreate
    ) -> AppointmentPublic:
        """Crea una cita médica desde el portal público sin requerir inicio de sesión previo.
        
        Captura datos personales del paciente, dirección de residencia, medidas biométricas
        y cuestionario de triage. La cita queda en PENDING_DOCTOR_APPROVAL hasta que el médico
        la acepte desde su panel, momento en el cual se envía la invitación por correo.
        """
        # 1. Validar médico
        doctor = await self.users.get_by_id(payload.doctor_id)
        if not doctor or doctor.role != "DOCTOR":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Médico no encontrado.")

        if doctor.license_verification_status != "VERIFIED" or doctor.status != "ACTIVE":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "El médico no se encuentra verificado o activo en la plataforma.",
            )

        if payload.start_time >= payload.end_time:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "La hora de inicio debe ser anterior a la hora de fin.",
            )

        # 2. Adquisición atómica de cerrojos mutex y resolución de consultorio físico compatible
        selected_room_id = await self._resolve_and_lock_room(
            clinic_id=payload.clinic_id,
            doctor=doctor,
            requested_room_id=payload.room_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )

        # 4. Localizar o registrar al paciente provisional
        patient = await self.users.get_by_email(payload.email)
        b_date = None
        if payload.birth_date:
            try:
                b_date = datetime.datetime.strptime(payload.birth_date, "%Y-%m-%d")
            except Exception:
                pass

        needs_onboarding = False
        if not patient:
            patient = User(
                email=payload.email,
                full_name=payload.full_name,
                phone=payload.phone,
                role="PATIENT",
                status="PENDING_ONBOARDING",
                identification_number=payload.id_document,
                birth_date=b_date,
                gender=payload.gender,
                address=payload.address,
                city=payload.city,
                country=payload.country or "Venezuela",
                mfa_enabled=False,
            )
            await self.users.create(patient)
            await self.db.flush()
            needs_onboarding = True
        else:
            if payload.full_name:
                patient.full_name = payload.full_name
            if payload.phone and not patient.phone:
                patient.phone = payload.phone
            if payload.id_document and not patient.identification_number:
                patient.identification_number = payload.id_document
            if payload.address and not patient.address:
                patient.address = payload.address
            if payload.city and not patient.city:
                patient.city = payload.city
            if b_date and not patient.birth_date:
                patient.birth_date = b_date
            if payload.gender and not patient.gender:
                patient.gender = payload.gender

            # Si el usuario no era un paciente activo con clave establecida:
            if patient.role != "PATIENT" or patient.status != "ACTIVE" or not patient.hashed_password:
                patient.role = "PATIENT"
                patient.status = "PENDING_ONBOARDING"
                patient.hashed_password = None
                needs_onboarding = True

        # 5. Calcular IMC si se proporcionan talla y peso
        bmi = payload.bmi
        bmi_cat = None
        if payload.weight_kg and payload.height_cm and payload.height_cm > 0:
            h_m = payload.height_cm / 100.0
            bmi = round(payload.weight_kg / (h_m * h_m), 2)
            if bmi < 18.5:
                bmi_cat = "Bajo peso"
            elif bmi < 25.0:
                bmi_cat = "Peso normal"
            elif bmi < 30.0:
                bmi_cat = "Sobrepeso"
            else:
                bmi_cat = "Obesidad"

        intake_data = {
            "height_cm": payload.height_cm,
            "weight_kg": payload.weight_kg,
            "bmi": bmi,
            "bmi_category": bmi_cat,
            "blood_type": payload.blood_type,
            "allergies": payload.allergies,
            "chronic_conditions": payload.chronic_conditions,
            "current_medications": payload.current_medications,
            "symptoms": payload.reason,
            "address": payload.address,
            "city": payload.city,
            "country": payload.country,
            "id_document": payload.id_document,
            "birth_date": payload.birth_date,
            "gender": payload.gender,
            "needs_patient_onboarding": needs_onboarding,
        }

        # 6. Crear Cita en estado PENDING_DOCTOR_APPROVAL
        appointment = Appointment(
            clinic_id=payload.clinic_id,
            doctor_id=payload.doctor_id,
            patient_id=patient.id,
            room_id=selected_room_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            status="PENDING_DOCTOR_APPROVAL",
            reason=payload.reason,
            intake_data=intake_data,
        )
        await self.appointments.create(appointment)

        # 7. Obtener tarifa de consulta del médico en la sede y registrar procedimientos
        aff_stmt = select(DoctorClinicAffiliation).where(
            DoctorClinicAffiliation.doctor_id == payload.doctor_id,
            DoctorClinicAffiliation.clinic_id == payload.clinic_id,
            DoctorClinicAffiliation.status == "ACTIVE",
        )
        aff = (await self.db.execute(aff_stmt)).scalar_one_or_none()
        base_fee = aff.consultation_fee if (aff and aff.consultation_fee is not None) else Decimal("30.00")
        curr = aff.currency if (aff and aff.currency) else (payload.currency or "USD")

        procedures_total = Decimal("0.00")
        if payload.procedure_ids:
            p_stmt = select(MedicalProcedure).where(MedicalProcedure.id.in_(payload.procedure_ids))
            selected_procs = list((await self.db.execute(p_stmt)).scalars().all())
            for sp in selected_procs:
                ap = AppointmentProcedure(
                    appointment_id=appointment.id,
                    procedure_id=sp.id,
                    name=sp.name,
                    price=sp.price,
                    currency=sp.currency,
                )
                self.db.add(ap)
                procedures_total += sp.price

        total_amount = base_fee + procedures_total

        # Registro contable inicial (UNPAID)
        payment = PaymentRecord(
            appointment_id=appointment.id,
            clinic_id=payload.clinic_id,
            amount=total_amount,
            currency=curr,
            status="UNPAID",
        )
        await self.payments.create(payment)

        await self.db.commit()


        # 8. Invalidar caché en Redis para el médico y toda la clínica
        await self._invalidate_redis_slots(payload.clinic_id, payload.doctor_id, payload.start_time)

        fresh_app = await self.appointments.get_by_id(appointment.id)
        # Notificar al médico de nueva cita / solicitud pendiente
        try:
            from app.services.notification_service import NotificationService
            notif_service = NotificationService(self.db)
            clinic_name = fresh_app.clinic.name if (fresh_app and fresh_app.clinic) else "ÍntimaSalud"
            await notif_service.send_new_appointment_to_doctor(
                appointment=fresh_app,
                doctor=doctor,
                patient=patient,
                clinic_name=clinic_name,
                is_pending_approval=True,
            )
        except Exception as exc:
            logger.warning("No se pudo notificar al médico sobre solicitud pública: %s", exc)

        return self._to_public(fresh_app)

    async def doctor_accept_appointment(
        self, appointment_id: str, current_user: User
    ) -> AppointmentPublic:
        """Aprobación formal de la cita por parte del médico.
        
        Transiciona a CONFIRMED y envía un correo con enlace seguro de invitación
        al paciente para completar su registro en VitaRecord y fijar su contraseña.
        """
        app = await self.appointments.get_by_id(appointment_id)
        if not app:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cita no encontrada.")

        if current_user.role != "DOCTOR" or app.doctor_id != current_user.id:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Solo el médico asignado a esta cita puede aceptarla.",
            )

        if app.status not in ("PENDING_DOCTOR_APPROVAL", "SCHEDULED"):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"La cita no se encuentra en espera de aprobación médica (estado actual: {app.status}).",
            )

        await self.appointments.update_status(appointment_id, "CONFIRMED")

        # Cargar paciente, médico y clínica
        patient = await self.users.get_by_id(app.patient_id)
        doctor = current_user
        clinic = app.clinic or await self.clinics.get_by_id(app.clinic_id)
        clinic_name = clinic.name if clinic else "Clínica VitaRecord"
        doctor_name = doctor.full_name or f"Dr. {doctor.email}"
        patient_name = patient.full_name or "Paciente"
        date_str = app.start_time.strftime("%d/%m/%Y a las %H:%M")

        # Si el paciente es nuevo, no tiene clave activa o no ha completado el onboarding:
        needs_patient_onboarding = False
        if not patient:
            needs_patient_onboarding = False
        elif (
            patient.role != "PATIENT"
            or patient.status != "ACTIVE"
            or not patient.hashed_password
            or (app.intake_data and app.intake_data.get("needs_patient_onboarding") is True)
        ):
            needs_patient_onboarding = True

        if patient and needs_patient_onboarding:
            # Asegurar rol PATIENT y estado PENDING_ONBOARDING
            if patient.role != "PATIENT":
                patient.role = "PATIENT"
            if patient.status != "ACTIVE":
                patient.status = "PENDING_ONBOARDING"
            await self.db.flush()

            token = create_patient_invitation_token(
                subject=patient.id,
                clinic_id=app.clinic_id,
                appointment_id=app.id,
            )
            onboarding_link = f"{settings.FRONTEND_URL}/#/patient/onboarding?token={token}"

            doctor_spec = f"{doctor_name} ({doctor.specialty})" if doctor.specialty else doctor_name
            details = [
                ("Especialista", doctor_spec),
                ("Sede / Clínica", clinic_name),
                ("Fecha y Hora", date_str),
                ("Paciente", patient_name),
            ]
            if app.reason:
                details.append(("Motivo", app.reason))

            content_p = (
                f"Hola <strong>{patient_name}</strong>, te informamos que el especialista "
                f"<strong>{doctor_name}</strong> ha revisado tu solicitud de atención médica y "
                f"ha <strong>confirmado tu cita</strong>.<br/><br/>"
                f"Para que puedas acceder a tu cita, recibir tus <strong>recetas médicas electrónicas con código QR</strong>, "
                f"consultar tu historia clínica, informes de consulta y resultados de exámenes, por favor completa tu registro "
                f"creando tu contraseña personal de acceso a la plataforma:"
            )

            html_body = build_branded_email_html(
                title="¡Tu Cita Médica ha sido Confirmada!",
                subtitle="El especialista ha aceptado tu consulta y ha reservado tu turno.",
                content_html=content_p,
                cta_text="Completar Mi Registro y Crear Contraseña",
                cta_link=onboarding_link,
                details_table=details,
                alert_box="Al definir tu contraseña tendrás acceso directo e inmediato al sistema de pacientes de VitaRecord.",
            )
            try:
                await send_email(
                    patient.email,
                    f"[VitaRecord] Cita Confirmada por el {doctor_name} - Completa tu Registro",
                    html_body,
                )
            except Exception as e:
                logger.warning("No se pudo enviar correo de onboarding a %s: %s", patient.email, e)
        else:
            # Paciente ya registrado
            my_appointments_link = f"{settings.FRONTEND_URL}/#/appointments/my-list"
            doctor_spec = f"{doctor_name} ({doctor.specialty})" if doctor.specialty else doctor_name
            details = [
                ("Especialista", doctor_spec),
                ("Sede / Clínica", clinic_name),
                ("Fecha y Hora", date_str),
                ("Paciente", patient_name),
            ]
            if app.reason:
                details.append(("Motivo", app.reason))

            content_p = (
                f"Estimado/a <strong>{patient_name}</strong>,<br/><br/>"
                f"El <strong>{doctor_name}</strong> ha confirmado tu cita programada para el "
                f"<strong>{date_str}</strong> en <strong>{clinic_name}</strong>.<br/>"
                f"Podrás consultar tus recetas digitales, órdenes e historial médico directamente en tu cuenta de VitaRecord."
            )

            html_body = build_branded_email_html(
                title="¡Tu Cita Médica ha sido Confirmada!",
                subtitle="Tu turno de atención médica ha sido agendado exitosamente.",
                content_html=content_p,
                cta_text="Ver Mis Citas en VitaRecord",
                cta_link=my_appointments_link,
                details_table=details,
            )
            try:
                await send_email(patient.email, f"[VitaRecord] Cita Confirmada con el {doctor_name}", html_body)
            except Exception as e:
                logger.warning("No se pudo enviar correo de confirmacion a %s: %s", patient.email, e)

        await self.db.commit()
        fresh = await self.appointments.get_by_id(appointment_id)
        return self._to_public(fresh)

    async def doctor_reject_appointment(
        self, appointment_id: str, reason: str, current_user: User
    ) -> AppointmentPublic:
        """Rechazo justificado de cita médica por el especialista."""
        app = await self.appointments.get_by_id(appointment_id)
        if not app:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cita no encontrada.")

        if current_user.role != "DOCTOR" or app.doctor_id != current_user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el médico asignado puede rechazar esta cita.")

        if app.status not in ("PENDING_DOCTOR_APPROVAL", "SCHEDULED"):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"La cita no se encuentra en estado cancelable por el médico ({app.status}).",
            )

        await self.appointments.update_status(
            appointment_id, "REJECTED_BY_DOCTOR", cancellation_reason=reason
        )

        pay_record = await self.payments.get_by_appointment_id(appointment_id)
        if pay_record:
            await self.payments.update_status(pay_record.id, "VOID", notes=f"Rechazada por el médico: {reason}")

        await self.db.commit()
        await self._invalidate_redis_slots(app.clinic_id, app.doctor_id, app.start_time)

        fresh = await self.appointments.get_by_id(appointment_id)
        return self._to_public(fresh)

    async def add_procedure_to_appointment(
        self,
        appointment_id: str,
        payload: AppointmentProcedureCreate,
        current_user: User,
    ) -> AppointmentPublic:
        """Agrega un procedimiento realizado durante la consulta médica y actualiza la caja automáticamente."""
        app = await self.appointments.get_by_id(appointment_id)
        if not app:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cita no encontrada.")

        if current_user.role == "DOCTOR" and app.doctor_id != current_user.id:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Solo el médico asignado a esta cita puede registrar procedimientos adicionales.",
            )
        elif current_user.role not in ("DOCTOR", "CLINIC_ADMIN", "RECEPTIONIST", "SUPERADMIN"):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos para agregar procedimientos.")

        proc_name = payload.name
        proc_price = payload.price
        proc_currency = payload.currency or "USD"

        if payload.procedure_id:
            mp = await self.db.get(MedicalProcedure, payload.procedure_id)
            if mp:
                proc_name = mp.name
                if proc_price is None:
                    proc_price = mp.price
                proc_currency = mp.currency

        if not proc_name:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Debe especificar el nombre o ID del procedimiento.")
        if proc_price is None:
            proc_price = Decimal("0.00")

        ap = AppointmentProcedure(
            appointment_id=app.id,
            procedure_id=payload.procedure_id,
            name=proc_name,
            price=proc_price,
            currency=proc_currency,
            notes=payload.notes,
        )
        self.db.add(ap)
        if app.procedures is not None:
            app.procedures.append(ap)

        # Actualizar automáticamente el monto en el registro de cobro (PaymentRecord)
        payment = app.payment_record
        if payment:
            payment.amount = (payment.amount or Decimal("0.00")) + proc_price
        else:
            payment = PaymentRecord(
                appointment_id=app.id,
                clinic_id=app.clinic_id,
                amount=proc_price,
                currency=proc_currency,
                status="UNPAID",
            )
            self.db.add(payment)

        await self.db.commit()
        self.db.expire_all()
        fresh = await self.appointments.get_by_id(appointment_id)
        return self._to_public(fresh)


    def _to_public(self, app: Appointment) -> AppointmentPublic:
        pay = app.payment_record
        procs = [
            AppointmentProcedurePublic(
                id=p.id,
                appointment_id=p.appointment_id,
                procedure_id=p.procedure_id,
                name=p.name,
                price=p.price,
                currency=p.currency,
                notes=p.notes,
            )
            for p in (app.procedures or [])
        ]
        procs_sum = sum((p.price for p in procs), Decimal("0.00"))
        total_amount = pay.amount if pay else Decimal("30.00")
        base_consultation_fee = max(Decimal("0.00"), total_amount - procs_sum)

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
            intake_data=app.intake_data,
            doctor_name=app.doctor.full_name if app.doctor else None,
            patient_name=app.patient.full_name if app.patient else None,
            patient_email=app.patient.email if app.patient else None,
            patient_phone=app.patient.phone if app.patient else None,
            clinic_name=app.clinic.name if app.clinic else None,
            room_name=app.room.name if app.room else None,
            payment_status=pay.status if pay else "UNPAID",
            payment_amount=total_amount,
            payment_method=pay.payment_method if pay else None,
            currency=pay.currency if pay else "USD",
            consultation_fee=base_consultation_fee,
            procedures=procs,
            created_at=app.created_at,
        )

