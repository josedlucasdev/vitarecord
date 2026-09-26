"""Servicio de Urgencias Médicas, Escalamiento Multicanal y Torre de Control (plan/plan.md 2.B.7).

Cadena de escalamiento (niveles):

    1..N   Médico de guardia k (N = clinic.emergency_doctor_attempts, mínimo 2).
           Se despacha Push FCM (alta prioridad) + WhatsApp en paralelo. Si
           ningún canal confirma entrega (DELIVERED/READ) en
           EMERGENCY_DELIVERY_CONFIRM_SECONDS (15 s) se hace una llamada de voz
           de refuerzo al mismo médico. Si no acepta en
           EMERGENCY_DOCTOR_ACCEPT_TIMEOUT_SECONDS (60 s) se pasa al siguiente.
    N+1    Moderador / SuperAdmin de turno: alarma en la Torre de Control +
           llamada de voz automática. SLA de reconocimiento
           EMERGENCY_MODERATOR_SLA_SECONDS (2 min).
    N+2    Línea de respaldo de la clínica (o la global): llamada de voz,
           reintentada cada SLA hasta EMERGENCY_BACKUP_MAX_CALLS veces.

El avance lo hace `process_emergency_escalations()` (tarea periódica en
app.tasks.emergency_escalation) y también puede forzarse manualmente desde la
Torre de Control con POST /emergencies/{id}/escalate.
"""

import datetime
import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.emergency_hub import emergency_hub
from app.models.clinic import Clinic
from app.models.emergency_incident import EmergencyIncident
from app.models.notification_log import NotificationLog
from app.models.user import User
from app.models.user_device_token import UserDeviceToken
from app.repositories.emergency_repository import CLOSED_STATUSES, EmergencyRepository, is_unattended
from app.schemas.emergency import EmergencyResolveRequest, EmergencySosRequest

logger = logging.getLogger("emergency")

MIN_DOCTOR_ATTEMPTS = 2
DELIVERED_STATUSES = ("DELIVERED", "READ", "ACKNOWLEDGED")


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _as_utc(value: datetime.datetime | None) -> datetime.datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)


class EmergencyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = EmergencyRepository(db)

    # ------------------------------------------------------------------ utils
    async def _resolve_clinic_id(self, preferred_clinic_id: str | None, user: User) -> str:
        if preferred_clinic_id:
            clinic = await self.db.get(Clinic, preferred_clinic_id)
            if not clinic or not clinic.is_active:
                raise HTTPException(status_code=400, detail="La clínica indicada no existe o está inactiva.")
            return preferred_clinic_id
        if user.clinic_id:
            return user.clinic_id
        stmt = select(Clinic).where(Clinic.is_active.is_(True)).order_by(Clinic.created_at.asc()).limit(1)
        res = await self.db.execute(stmt)
        first_clinic = res.scalars().first()
        if not first_clinic:
            raise HTTPException(status_code=400, detail="No hay clínicas activas registradas en el sistema.")
        return first_clinic.id

    def _enrich_incident(self, incident: EmergencyIncident) -> EmergencyIncident:
        if incident.patient:
            incident.patient_name = incident.patient.full_name or incident.patient.email
        if incident.assigned_doctor:
            incident.doctor_name = incident.assigned_doctor.full_name or incident.assigned_doctor.email
        if incident.clinic:
            incident.clinic_name = incident.clinic.name
        if incident.accepted_at and incident.triggered_at:
            incident.response_time_seconds = max(
                0.0, (_as_utc(incident.accepted_at) - _as_utc(incident.triggered_at)).total_seconds()
            )
        else:
            incident.response_time_seconds = None
        return incident

    @staticmethod
    def doctor_attempts_for(clinic: Clinic | None) -> int:
        configured = getattr(clinic, "emergency_doctor_attempts", None) or MIN_DOCTOR_ATTEMPTS
        return max(MIN_DOCTOR_ATTEMPTS, int(configured))

    def moderator_level(self, clinic: Clinic | None) -> int:
        return self.doctor_attempts_for(clinic) + 1

    def backup_level(self, clinic: Clinic | None) -> int:
        return self.doctor_attempts_for(clinic) + 2

    async def _log(
        self,
        incident: EmergencyIncident,
        channel: str,
        message: str,
        attempt_number: int,
        recipient_id: str | None = None,
        ok: bool = True,
        external_id: str | None = None,
        status_value: str | None = None,
    ) -> NotificationLog:
        now = _utcnow()
        log = NotificationLog(
            incident_id=incident.id,
            recipient_id=recipient_id,
            channel=channel,
            status=status_value or ("SENT" if ok else "FAILED"),
            attempt_number=attempt_number,
            sent_at=now,
            external_message_id=external_id,
            error_message=message[:255],
        )
        return await self.repo.add_notification_log(log)

    def _contacted_doctor_ids(self, incident: EmergencyIncident) -> list[str]:
        """Médicos ya contactados como guardia, en orden (para no repetirlos)."""
        seen: list[str] = []
        for log in sorted(incident.notification_logs or [], key=lambda l: (l.attempt_number, _as_utc(l.sent_at))):
            if log.recipient_id and log.channel in ("PUSH", "WHATSAPP") and log.recipient_id not in seen:
                seen.append(log.recipient_id)
        return seen

    # ------------------------------------------------------- canales de envío
    async def _dispatch_to_doctor(self, incident: EmergencyIncident, doctor: User, level: int) -> None:
        """Push FCM alta prioridad + WhatsApp EN PARALELO (no uno como fallback del otro)."""
        from app.services.notification_service import FCMProvider, WhatsAppProvider

        title = "URGENCIA SOS - VitaRecord"
        body = f"Paciente requiere orientación remota: {incident.chief_complaint}. Abra la app para tomar el caso."

        tokens = (
            await self.db.execute(
                select(UserDeviceToken).where(UserDeviceToken.user_id == doctor.id, UserDeviceToken.is_active.is_(True))
            )
        ).scalars().all()
        push_sent = False
        for dev in tokens:
            ok, ext_id, err = await FCMProvider().send_push(
                token=dev.fcm_token,
                title=title,
                body=body,
                data_payload={"incident_id": incident.id, "type": "EMERGENCY_SOS"},
                priority="high",
            )
            push_sent = push_sent or ok
            await self._log(
                incident, "PUSH",
                f"Alerta SOS despachada a Médico de Guardia {level}: Dr(a). {doctor.full_name}." if ok else f"Push fallido: {err}",
                level, doctor.id, ok=ok, external_id=ext_id,
            )
        if not tokens:
            await self._log(
                incident, "PUSH",
                f"Alerta SOS despachada a Médico de Guardia {level}: Dr(a). {doctor.full_name} (sin dispositivo Push registrado).",
                level, doctor.id, ok=False,
            )

        if doctor.phone:
            ok, ext_id, err = await WhatsAppProvider().send_text(doctor.phone, f"{title}: {body}")
            await self._log(
                incident, "WHATSAPP",
                f"WhatsApp SOS a Dr(a). {doctor.full_name}." if ok else f"WhatsApp fallido: {err}",
                level, doctor.id, ok=ok, external_id=ext_id,
            )

    async def _voice_call(self, incident: EmergencyIncident, phone: str | None, speech: str, level: int,
                          recipient_id: str | None, label: str) -> bool:
        from app.services.notification_service import TwilioVoiceProvider

        if not phone:
            await self._log(incident, "VOICE_CALL", f"{label}: sin teléfono configurado.", level, recipient_id, ok=False)
            return False
        ok, ext_id, err = await TwilioVoiceProvider().make_call(phone, speech)
        await self._log(
            incident, "VOICE_CALL", f"{label}." if ok else f"{label} fallida: {err}",
            level, recipient_id, ok=ok, external_id=ext_id,
        )
        return ok

    async def _call_moderators(self, incident: EmergencyIncident, level: int, log_alarm: bool = True) -> None:
        moderators = (
            await self.db.execute(
                select(User).where(
                    User.role.in_(("MODERATOR", "SUPERADMIN")),
                    User.status == "ACTIVE",
                    User.phone.is_not(None),
                )
            )
        ).scalars().all()
        if log_alarm:
            await self._log(
                incident, "WEBSOCKET",
                "Escalamiento a Torre de Control / Moderador: alarma crítica y llamada de voz automática.",
                level,
            )
        for mod in moderators:
            await self._voice_call(
                incident, mod.phone,
                "Alerta VitaRecord. Urgencia médica sin médico asignado. Ingrese a la Torre de Control de inmediato.",
                level, mod.id, f"Llamada de voz al moderador {mod.full_name or mod.email}",
            )

    async def _call_backup_line(self, incident: EmergencyIncident, level: int) -> None:
        clinic = incident.clinic or await self.db.get(Clinic, incident.clinic_id)
        phone = getattr(clinic, "emergency_backup_phone", None) or settings.EMERGENCY_BACKUP_PHONE or getattr(clinic, "phone", None)
        await self._voice_call(
            incident, phone,
            "Alerta VitaRecord. Incidente de urgencia sin atender. Requiere acción inmediata. "
            "Si hay riesgo vital, coordine con los servicios de emergencia oficiales.",
            level, None, "Llamada a Línea Telefónica de Contingencia de la sede",
        )

    # ------------------------------------------------------------ ciclo de vida
    async def trigger_sos(self, patient: User, payload: EmergencySosRequest) -> EmergencyIncident:
        if not payload.disclaimer_acknowledged:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe aceptar el descargo legal de responsabilidad de urgencias (Directorio 911).",
            )

        if payload.dependent_id:
            from app.models.patient_dependent import PatientDependent

            dep = await self.db.get(PatientDependent, payload.dependent_id)
            if not dep or dep.guardian_user_id != patient.id:
                raise HTTPException(status_code=400, detail="El familiar indicado no pertenece a su grupo familiar.")

        now = _utcnow()
        clinic_id = await self._resolve_clinic_id(payload.clinic_id, patient)
        clinic = await self.db.get(Clinic, clinic_id)

        incident = EmergencyIncident(
            patient_id=patient.id,
            clinic_id=clinic_id,
            dependent_id=payload.dependent_id,
            status="DISPATCHED",
            escalation_level=1,
            latitude=payload.latitude,
            longitude=payload.longitude,
            chief_complaint=payload.chief_complaint,
            disclaimer_acknowledged_at=now,
            triggered_at=now,
            last_escalated_at=now,
        )
        incident = await self.repo.create_incident(incident)

        doctors = await self.repo.find_eligible_doctors(clinic_id=clinic_id)
        if doctors:
            await self._dispatch_to_doctor(incident, doctors[0], level=1)
        else:
            # Sin médicos de guardia: directo a Torre de Control / Moderador.
            incident.status = "ESCALATED_MODERATOR"
            incident.escalation_level = self.moderator_level(clinic)
            await self._log(
                incident, "WEBSOCKET",
                "No se hallaron médicos verificados disponibles. Escalamiento inmediato a Torre de Control / Moderadores.",
                incident.escalation_level,
            )
            await self._call_moderators(incident, incident.escalation_level, log_alarm=False)

        await self.db.commit()
        incident = await self.repo.get_by_id(incident.id)
        self._enrich_incident(incident)

        await emergency_hub.publish_event(
            "INCIDENT_CREATED",
            {
                "incident_id": incident.id,
                "patient_id": incident.patient_id,
                "patient_name": incident.patient_name,
                "status": incident.status,
                "escalation_level": incident.escalation_level,
                "chief_complaint": incident.chief_complaint,
                "triggered_at": incident.triggered_at.isoformat(),
            },
        )
        return incident

    async def escalate_incident(self, incident_id: str, automatic: bool = False) -> EmergencyIncident:
        locked = await self.repo.get_for_update(incident_id)
        if not locked:
            raise HTTPException(status_code=404, detail="Incidente no encontrado.")
        if locked.status in CLOSED_STATUSES or locked.status == "ACCEPTED":
            raise HTTPException(
                status_code=400,
                detail=f"No se puede escalar un incidente en estado '{locked.status}'.",
            )

        incident = await self.repo.get_by_id(incident_id)
        clinic = incident.clinic
        now = _utcnow()
        current_level = incident.escalation_level
        doctor_attempts = self.doctor_attempts_for(clinic)
        mod_level = self.moderator_level(clinic)
        backup_level = self.backup_level(clinic)
        prefix = "SLA vencido: " if automatic else "Escalamiento manual: "

        next_doctor = None
        if current_level < doctor_attempts:
            contacted = set(self._contacted_doctor_ids(incident))
            eligible = await self.repo.find_eligible_doctors(clinic_id=incident.clinic_id)
            next_doctor = next((d for d in eligible if d.id not in contacted), None)

        if next_doctor is not None:
            new_level = current_level + 1
            incident.status = f"ESCALATED_DOCTOR_{new_level}"
            incident.escalation_level = new_level
            msg = f"{prefix}Escalamiento a Médico de Guardia {new_level}: Dr(a). {next_doctor.full_name}."
            await self._log(incident, "WEBSOCKET", msg, new_level)
            await self._dispatch_to_doctor(incident, next_doctor, new_level)
        elif current_level < mod_level:
            incident.status = "ESCALATED_MODERATOR"
            incident.escalation_level = mod_level
            msg = f"{prefix}sin más médicos de guardia disponibles. Escalamiento a Torre de Control / Moderador."
            await self._call_moderators(incident, mod_level)
        elif current_level == mod_level:
            incident.status = "ESCALATED_BACKUP"
            incident.escalation_level = backup_level
            msg = f"{prefix}Torre no intervino en SLA. Escalamiento crítico a Línea Telefónica de Contingencia y 911."
            await self._call_backup_line(incident, backup_level)
        else:
            msg = f"{prefix}Reintento de llamada a Línea Telefónica de Contingencia (nivel máximo)."
            await self._call_backup_line(incident, incident.escalation_level)

        incident.last_escalated_at = now
        await self.db.commit()
        incident = await self.repo.get_by_id(incident.id)
        self._enrich_incident(incident)

        await emergency_hub.publish_event(
            "INCIDENT_ESCALATED",
            {
                "incident_id": incident.id,
                "status": incident.status,
                "escalation_level": incident.escalation_level,
                "message": msg,
                "automatic": automatic,
            },
        )
        return incident

    async def send_delivery_reinforcement(self, incident: EmergencyIncident) -> bool:
        """Llamada de voz de refuerzo al médico del nivel actual si ningún canal
        confirmó entrega en EMERGENCY_DELIVERY_CONFIRM_SECONDS. Idempotente."""
        level = incident.escalation_level
        logs = [l for l in (incident.notification_logs or []) if l.attempt_number == level]
        doctor_logs = [l for l in logs if l.recipient_id and l.channel in ("PUSH", "WHATSAPP")]
        if not doctor_logs:
            return False
        if any(l.status in DELIVERED_STATUSES for l in doctor_logs):
            return False
        if any(l.channel == "VOICE_CALL" for l in logs):
            return False
        doctor = await self.db.get(User, doctor_logs[0].recipient_id)
        if not doctor:
            return False
        await self._voice_call(
            incident, doctor.phone,
            "Alerta VitaRecord. Tiene una urgencia médica pendiente de aceptar. Abra la aplicación de inmediato.",
            level, doctor.id,
            f"Sin confirmación de entrega en {settings.EMERGENCY_DELIVERY_CONFIRM_SECONDS}s: llamada de voz de refuerzo a Dr(a). {doctor.full_name}",
        )
        await self.db.commit()
        return True

    async def acknowledge_incident(self, incident_id: str, user: User) -> EmergencyIncident:
        """El moderador/SuperAdmin de turno reconoce el incidente (detiene el paso a la línea de respaldo)."""
        locked = await self.repo.get_for_update(incident_id)
        if not locked:
            raise HTTPException(status_code=404, detail="Incidente no encontrado.")
        if locked.status in CLOSED_STATUSES:
            raise HTTPException(status_code=400, detail=f"El incidente ya está '{locked.status}'.")
        now = _utcnow()
        locked.acknowledged_at = now
        locked.acknowledged_by_id = user.id
        incident = await self.repo.get_by_id(incident_id)
        await self._log(
            incident, "WEBSOCKET",
            f"Incidente reconocido por {user.full_name or user.email} ({user.role}).",
            incident.escalation_level, user.id, status_value="ACKNOWLEDGED",
        )
        await self.db.commit()
        incident = await self.repo.get_by_id(incident_id)
        self._enrich_incident(incident)
        await emergency_hub.publish_event(
            "INCIDENT_ACKNOWLEDGED",
            {"incident_id": incident.id, "acknowledged_by": user.full_name, "status": incident.status},
        )
        return incident

    async def assign_doctor(self, incident_id: str, doctor_id: str, user: User) -> EmergencyIncident:
        """Asignación manual de un médico disponible desde la Torre de Control (1 clic)."""
        locked = await self.repo.get_for_update(incident_id)
        if not locked:
            raise HTTPException(status_code=404, detail="Incidente no encontrado.")
        if locked.status in CLOSED_STATUSES or locked.status == "ACCEPTED":
            raise HTTPException(status_code=400, detail=f"El incidente está '{locked.status}'.")
        doctor = await self.db.get(User, doctor_id)
        if (
            not doctor or doctor.role != "DOCTOR" or doctor.status != "ACTIVE"
            or doctor.license_verification_status != "VERIFIED"
        ):
            raise HTTPException(status_code=400, detail="El médico indicado no está verificado o activo.")
        now = _utcnow()
        if locked.acknowledged_at is None:
            locked.acknowledged_at = now
            locked.acknowledged_by_id = user.id
        incident = await self.repo.get_by_id(incident_id)
        await self._log(
            incident, "WEBSOCKET",
            f"Asignación manual por {user.full_name or user.email}: Dr(a). {doctor.full_name}.",
            incident.escalation_level, user.id,
        )
        await self._dispatch_to_doctor(incident, doctor, incident.escalation_level)
        await self._voice_call(
            incident, doctor.phone,
            "Alerta VitaRecord. La Torre de Control le asignó una urgencia médica. Abra la aplicación de inmediato.",
            incident.escalation_level, doctor.id, f"Llamada de voz por asignación manual a Dr(a). {doctor.full_name}",
        )
        await self.db.commit()
        incident = await self.repo.get_by_id(incident_id)
        self._enrich_incident(incident)
        await emergency_hub.publish_event(
            "INCIDENT_ASSIGNED",
            {"incident_id": incident.id, "doctor_id": doctor.id, "doctor_name": doctor.full_name},
        )
        return incident

    async def accept_incident(self, incident_id: str, doctor: User) -> EmergencyIncident:
        if doctor.role != "DOCTOR" or doctor.license_verification_status != "VERIFIED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo médicos con cédula/licencia verificada pueden tomar urgencias médicas.",
            )

        # Bloqueo de fila: dos médicos no pueden tomar el mismo caso a la vez.
        incident = await self.repo.get_for_update(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incidente no encontrado.")
        if incident.status in CLOSED_STATUSES:
            raise HTTPException(status_code=400, detail=f"El incidente ya está '{incident.status}'.")
        if incident.status == "ACCEPTED":
            raise HTTPException(status_code=400, detail="El incidente ya fue tomado por otro médico.")

        now = _utcnow()
        response_time = max(0.0, float((now - _as_utc(incident.triggered_at)).total_seconds()))

        incident.status = "ACCEPTED"
        incident.assigned_doctor_id = doctor.id
        incident.accepted_at = now

        log = NotificationLog(
            incident_id=incident.id,
            recipient_id=doctor.id,
            channel="PUSH",
            status="DELIVERED",
            attempt_number=incident.escalation_level,
            sent_at=now,
            delivered_at=now,
            response_time_seconds=response_time,
            error_message=f"Dr(a). {doctor.full_name} tomó el caso SOS. Tiempo de respuesta SLA: {int(response_time)}s.",
        )
        await self.repo.add_notification_log(log)
        await self.db.commit()

        incident = await self.repo.get_by_id(incident.id)
        self._enrich_incident(incident)

        await emergency_hub.publish_event(
            "INCIDENT_ACCEPTED",
            {
                "incident_id": incident.id,
                "doctor_id": doctor.id,
                "doctor_name": doctor.full_name,
                "response_time_seconds": response_time,
                "status": "ACCEPTED",
            },
        )
        return incident

    async def resolve_incident(
        self, incident_id: str, user: User, payload: EmergencyResolveRequest
    ) -> EmergencyIncident:
        incident = await self.repo.get_by_id(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incidente no encontrado.")

        if incident.status == "RESOLVED":
            raise HTTPException(status_code=400, detail="El incidente ya está resuelto.")

        # Solo el médico asignado o el staff global de turno cierra el caso.
        if user.role == "DOCTOR" and incident.assigned_doctor_id != user.id:
            raise HTTPException(status_code=403, detail="Solo el médico asignado puede cerrar este incidente.")

        now = _utcnow()
        incident.status = "RESOLVED"
        incident.triage_notes = payload.triage_notes
        incident.resolved_at = now

        log = NotificationLog(
            incident_id=incident.id,
            recipient_id=user.id,
            channel="WEBSOCKET",
            status="DELIVERED",
            attempt_number=incident.escalation_level,
            sent_at=now,
            delivered_at=now,
            error_message=f"Caso cerrado y finalizado por {user.full_name} ({user.role}). Triaje: {payload.triage_notes}"[:255],
        )
        await self.repo.add_notification_log(log)
        await self.db.commit()

        incident = await self.repo.get_by_id(incident.id)
        self._enrich_incident(incident)

        await emergency_hub.publish_event(
            "INCIDENT_RESOLVED",
            {
                "incident_id": incident.id,
                "resolved_by": user.full_name,
                "status": "RESOLVED",
                "resolved_at": now.isoformat(),
            },
        )
        return incident

    async def get_active_incidents(self, clinic_id: str | None = None) -> list[EmergencyIncident]:
        incidents = await self.repo.list_active(clinic_id=clinic_id)
        return [self._enrich_incident(inc) for inc in incidents]

    async def get_incident_audit_logs(self, incident_id: str) -> list[NotificationLog]:
        logs = await self.repo.list_logs_for_incident(incident_id)
        for log in logs:
            if log.recipient:
                log.recipient_name = log.recipient.full_name or log.recipient.email
        return logs

    async def get_patient_incidents(self, patient_id: str) -> list[EmergencyIncident]:
        incidents = await self.repo.list_patient_incidents(patient_id)
        return [self._enrich_incident(inc) for inc in incidents]


async def process_emergency_escalations(now: datetime.datetime | None = None) -> dict[str, int]:
    """Un ciclo del orquestador automático (plan 2.B.7). Se ejecuta cada
    EMERGENCY_CHECK_INTERVAL_SECONDS desde app.tasks.emergency_escalation.

    `now` es inyectable para las pruebas (simular el paso del tiempo)."""
    from app.core.database import AsyncSessionLocal

    now = _as_utc(now) or _utcnow()
    stats = {"reinforcements": 0, "escalations": 0}

    async with AsyncSessionLocal() as db:
        service = EmergencyService(db)
        incident_ids = [i.id for i in await service.repo.list_unattended()]

    for incident_id in incident_ids:
        # Sesión propia por incidente: un fallo en uno no bloquea a los demás.
        async with AsyncSessionLocal() as db:
            service = EmergencyService(db)
            try:
                incident = await service.repo.get_by_id(incident_id)
                if not incident or not is_unattended(incident.status):
                    continue
                clinic = incident.clinic
                since = _as_utc(incident.last_escalated_at or incident.triggered_at)
                elapsed = (now - since).total_seconds()
                level = incident.escalation_level
                doctor_attempts = service.doctor_attempts_for(clinic)
                mod_level = service.moderator_level(clinic)

                if level <= doctor_attempts and not incident.status.startswith("ESCALATED_MODERATOR"):
                    if elapsed >= settings.EMERGENCY_DOCTOR_ACCEPT_TIMEOUT_SECONDS:
                        await service.escalate_incident(incident_id, automatic=True)
                        stats["escalations"] += 1
                    elif elapsed >= settings.EMERGENCY_DELIVERY_CONFIRM_SECONDS:
                        if await service.send_delivery_reinforcement(incident):
                            stats["reinforcements"] += 1
                elif level == mod_level:
                    if incident.acknowledged_at is None and elapsed >= settings.EMERGENCY_MODERATOR_SLA_SECONDS:
                        await service.escalate_incident(incident_id, automatic=True)
                        stats["escalations"] += 1
                else:
                    # Línea de respaldo: reintentar cada SLA hasta el máximo de llamadas.
                    backup_calls = sum(
                        1 for l in incident.notification_logs or []
                        if l.channel == "VOICE_CALL" and l.recipient_id is None and l.attempt_number >= level
                    )
                    if (
                        incident.acknowledged_at is None
                        and elapsed >= settings.EMERGENCY_MODERATOR_SLA_SECONDS
                        and backup_calls < settings.EMERGENCY_BACKUP_MAX_CALLS
                    ):
                        await service.escalate_incident(incident_id, automatic=True)
                        stats["escalations"] += 1
            except HTTPException:
                # Estado cambió entre la lectura y el bloqueo (p. ej. un médico aceptó).
                await db.rollback()
            except Exception as exc:  # noqa: BLE001
                await db.rollback()
                logger.exception("Error procesando escalamiento del incidente %s: %s", incident_id, exc)
    return stats
