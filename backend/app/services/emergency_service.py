"""Servicio de Urgencias Médicas, Escalamiento Multicanal y Torre de Control (plan/plan.md 2.B.7)."""

import datetime
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.emergency_hub import emergency_hub
from app.models.clinic import Clinic
from app.models.emergency_incident import EmergencyIncident
from app.models.notification_log import NotificationLog
from app.models.user import User
from app.repositories.emergency_repository import EmergencyRepository
from app.schemas.emergency import EmergencyResolveRequest, EmergencySosRequest


class EmergencyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = EmergencyRepository(db)

    async def _resolve_clinic_id(self, preferred_clinic_id: str | None, user: User) -> str:
        if preferred_clinic_id:
            return preferred_clinic_id
        if user.clinic_id:
            return user.clinic_id
        stmt = select(Clinic).where(Clinic.is_active.is_(True)).limit(1)
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
                0.0,
                (
                    (incident.accepted_at.replace(tzinfo=datetime.timezone.utc) if not incident.accepted_at.tzinfo else incident.accepted_at)
                    - (incident.triggered_at.replace(tzinfo=datetime.timezone.utc) if not incident.triggered_at.tzinfo else incident.triggered_at)
                ).total_seconds(),
            )
        else:
            incident.response_time_seconds = None
        return incident

    async def trigger_sos(self, patient: User, payload: EmergencySosRequest) -> EmergencyIncident:
        if not payload.disclaimer_acknowledged:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe aceptar el descargo legal de responsabilidad de urgencias (Directorio 911).",
            )

        now = datetime.datetime.now(datetime.timezone.utc)
        clinic_id = await self._resolve_clinic_id(payload.clinic_id, patient)

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
        )

        incident = await self.repo.create_incident(incident)

        # Buscar médicos de guardia verificados
        doctors = await self.repo.find_eligible_doctors(clinic_id=clinic_id)

        if doctors:
            first_doctor = doctors[0]
            log = NotificationLog(
                incident_id=incident.id,
                recipient_id=first_doctor.id,
                channel="PUSH",
                status="SENT",
                attempt_number=1,
                sent_at=now,
                error_message=f"Alerta SOS despachada a Médico de Guardia 1: Dr(a). {first_doctor.full_name}.",
            )
            await self.repo.add_notification_log(log)
        else:
            # Sin médicos disponibles de inmediato -> escalar directamente a Moderador / Torre de Control
            incident.status = "ESCALATED_MODERATOR"
            incident.escalation_level = 3
            log = NotificationLog(
                incident_id=incident.id,
                recipient_id=None,
                channel="WEBSOCKET",
                status="SENT",
                attempt_number=1,
                sent_at=now,
                error_message="No se hallaron médicos verificados disponibles. Escalamiento inmediato a Torre de Control / Moderadores.",
            )
            await self.repo.add_notification_log(log)

        await self.db.commit()
        # Recargar con relaciones
        incident = await self.repo.get_by_id(incident.id)
        self._enrich_incident(incident)

        # Notificar por WebSocket / Redis
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

    async def escalate_incident(self, incident_id: str) -> EmergencyIncident:
        incident = await self.repo.get_by_id(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incidente no encontrado.")

        if incident.status in ("RESOLVED", "CANCELLED", "EXPIRED"):
            raise HTTPException(
                status_code=400,
                detail=f"No se puede escalar un incidente en estado '{incident.status}'.",
            )

        now = datetime.datetime.now(datetime.timezone.utc)
        current_level = incident.escalation_level

        if current_level == 1:
            eligible_docs = await self.repo.find_eligible_doctors(clinic_id=incident.clinic_id)
            second_doc = eligible_docs[1] if len(eligible_docs) > 1 else None
            if second_doc:
                incident.status = "ESCALATED_DOCTOR_2"
                incident.escalation_level = 2
                msg = f"Escalamiento a Médico de Guardia 2: Dr(a). {second_doc.full_name}."
                log = NotificationLog(
                    incident_id=incident.id,
                    recipient_id=second_doc.id,
                    channel="PUSH",
                    status="SENT",
                    attempt_number=2,
                    sent_at=now,
                    error_message=msg,
                )
            else:
                incident.status = "ESCALATED_MODERATOR"
                incident.escalation_level = 3
                msg = "Sin segundo médico en turno. Escalamiento a Torre de Control / Moderador."
                log = NotificationLog(
                    incident_id=incident.id,
                    recipient_id=None,
                    channel="WEBSOCKET",
                    status="SENT",
                    attempt_number=2,
                    sent_at=now,
                    error_message=msg,
                )
        elif current_level == 2:
            incident.status = "ESCALATED_MODERATOR"
            incident.escalation_level = 3
            msg = "Médico 2 SLA superado. Escalamiento a Torre de Control / Moderador."
            log = NotificationLog(
                incident_id=incident.id,
                recipient_id=None,
                channel="WEBSOCKET",
                status="SENT",
                attempt_number=3,
                sent_at=now,
                error_message=msg,
            )
        elif current_level == 3:
            incident.status = "ESCALATED_BACKUP"
            incident.escalation_level = 4
            msg = "Torre no intervino en SLA. Escalamiento crítico a Línea Telefónica de Contingencia y 911."
            log = NotificationLog(
                incident_id=incident.id,
                recipient_id=None,
                channel="VOICE_CALL",
                status="SENT",
                attempt_number=4,
                sent_at=now,
                error_message=msg,
            )
        else:
            msg = "Reintento de llamada a Línea Telefónica de Contingencia (Nivel 4 Máximo)."
            log = NotificationLog(
                incident_id=incident.id,
                recipient_id=None,
                channel="VOICE_CALL",
                status="SENT",
                attempt_number=incident.escalation_level + 1,
                sent_at=now,
                error_message=msg,
            )

        await self.repo.add_notification_log(log)
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
            },
        )

        return incident

    async def accept_incident(self, incident_id: str, doctor: User) -> EmergencyIncident:
        incident = await self.repo.get_by_id(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incidente no encontrado.")

        if incident.status in ("RESOLVED", "CANCELLED", "EXPIRED"):
            raise HTTPException(
                status_code=400,
                detail=f"El incidente ya está '{incident.status}'.",
            )

        if incident.status == "ACCEPTED":
            raise HTTPException(
                status_code=400,
                detail="El incidente ya fue tomado por otro médico.",
            )

        if doctor.role != "DOCTOR" or doctor.license_verification_status != "VERIFIED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo médicos con cédula/licencia verificada pueden tomar urgencias médicas.",
            )

        now = datetime.datetime.now(datetime.timezone.utc)
        triggered_dt = (
            incident.triggered_at
            if incident.triggered_at.tzinfo
            else incident.triggered_at.replace(tzinfo=datetime.timezone.utc)
        )
        response_time = max(0.0, float((now - triggered_dt).total_seconds()))

        incident.status = "ACCEPTED"
        incident.assigned_doctor_id = doctor.id
        incident.accepted_at = now

        log = NotificationLog(
            incident_id=incident.id,
            recipient_id=doctor.id,
            channel="PUSH",
            status="DELIVERED",
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

        now = datetime.datetime.now(datetime.timezone.utc)
        incident.status = "RESOLVED"
        incident.triage_notes = payload.triage_notes
        incident.resolved_at = now

        log = NotificationLog(
            incident_id=incident.id,
            recipient_id=user.id,
            channel="WEBSOCKET",
            status="DELIVERED",
            sent_at=now,
            delivered_at=now,
            error_message=f"Caso cerrado y finalizado por {user.full_name} ({user.role}). Triaje: {payload.triage_notes}",
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
