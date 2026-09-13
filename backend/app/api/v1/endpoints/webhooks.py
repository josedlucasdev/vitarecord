"""Webhooks de Meta WhatsApp Cloud API y Twilio para recepción de estados y respuestas interactivas de pacientes (plan/plan.md Módulo 6 y 2.B.5)."""

import datetime
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.notification_log import NotificationLog
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.appointment_service import AppointmentService
from app.services.notification_service import NotificationService

logger = logging.getLogger("webhooks")

router = APIRouter()


# =====================================================================
# META WHATSAPP WEBHOOKS
# =====================================================================

@router.get("/whatsapp", summary="Verificación del Webhook de Meta WhatsApp")
async def verify_whatsapp_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
):
    """Endpoint exigido por Meta Graph API para validar la suscripción del webhook.
    
    Verifica que hub.verify_token coincida con WHATSAPP_VERIFY_TOKEN configurado en el servidor
    y devuelve hub.challenge como texto plano con HTTP 200.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook de WhatsApp verificado exitosamente por Meta.")
        return PlainTextResponse(content=hub_challenge or "", status_code=200)

    logger.warning("Fallo en verificación de Webhook de WhatsApp: token inválido")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Token de verificación inválido o modo incorrecto.",
    )


@router.post("/whatsapp", summary="Recepción de eventos y mensajes de Meta WhatsApp")
async def receive_whatsapp_event(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Procesa eventos de entrega y respuestas de pacientes desde WhatsApp en tiempo real.
    
    1. Confirmaciones de entrega (sent, delivered, read, failed) -> actualizan NotificationLog.
    2. Respuestas interactivas con botones [Aceptar] o [Rechazar] -> confirman la cita o liberan
       el slot/consultorio al instante y marcan el cobro como EXEMPT.
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Cuerpo de petición JSON inválido")

    notif_repo = NotificationRepository(db)
    notif_service = NotificationService(db)
    app_repo = AppointmentRepository(db)
    pay_repo = PaymentRepository(db)

    entries = data.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})

            # 1. Estados de entrega (sent, delivered, read, failed)
            statuses = value.get("statuses", [])
            for st in statuses:
                wamid = st.get("id")
                new_status = st.get("status", "").upper()
                if wamid:
                    log_entry = await notif_repo.get_by_external_id(wamid)
                    if log_entry:
                        now = datetime.datetime.utcnow()
                        mapped_status = "DELIVERED" if new_status in ("DELIVERED", "READ") else new_status
                        await notif_repo.update_status(
                            log_id=log_entry.id,
                            status=mapped_status,
                            delivered_at=now,
                        )
                        await db.commit()
                        logger.info("Estado de notificación %s actualizado a %s vía Webhook", wamid, mapped_status)

            # 2. Mensajes entrantes del paciente
            messages = value.get("messages", [])
            for msg in messages:
                from_phone = msg.get("from")
                msg_type = msg.get("type")
                action_id = None
                text_content = ""

                if msg_type == "interactive":
                    interactive = msg.get("interactive", {})
                    btn_reply = interactive.get("button_reply", {})
                    action_id = btn_reply.get("id")
                    text_content = btn_reply.get("title", "")
                elif msg_type == "text":
                    text_content = msg.get("text", {}).get("body", "").strip().upper()
                    if "ACEPTAR" in text_content:
                        action_id = "TEXT_ACCEPT"
                    elif "RECHAZAR" in text_content:
                        action_id = "TEXT_REJECT"

                if not action_id and not text_content:
                    continue

                # Procesar acción sobre la cita
                await _handle_patient_whatsapp_action(
                    db=db,
                    from_phone=from_phone,
                    action_id=action_id,
                    text_content=text_content,
                    notif_service=notif_service,
                    app_repo=app_repo,
                    pay_repo=pay_repo,
                )

    return {"status": "processed"}


async def _handle_patient_whatsapp_action(
    db: AsyncSession,
    from_phone: str | None,
    action_id: str | None,
    text_content: str,
    notif_service: NotificationService,
    app_repo: AppointmentRepository,
    pay_repo: PaymentRepository,
) -> None:
    """Procesa el clic del paciente en [Aceptar] o [Rechazar] o respuesta de texto."""
    target_appointment_id = None
    is_accept = False
    is_reject = False

    if action_id and action_id.startswith("accept_appointment_"):
        target_appointment_id = action_id.replace("accept_appointment_", "").strip()
        is_accept = True
    elif action_id and action_id.startswith("reject_appointment_"):
        target_appointment_id = action_id.replace("reject_appointment_", "").strip()
        is_reject = True
    elif action_id in ("TEXT_ACCEPT", "TEXT_REJECT") and from_phone:
        # Buscar la cita más reciente en PENDING_PATIENT_ACCEPTANCE para este número de teléfono
        stmt = (
            select(Appointment)
            .join(User, Appointment.patient_id == User.id)
            .where(
                User.phone.like(f"%{from_phone[-8:]}%"),
                Appointment.status == "PENDING_PATIENT_ACCEPTANCE",
            )
            .order_by(Appointment.created_at.desc())
        )
        res = await db.execute(stmt)
        matched_app = res.scalar_one_or_none()
        if matched_app:
            target_appointment_id = matched_app.id
            is_accept = (action_id == "TEXT_ACCEPT")
            is_reject = (action_id == "TEXT_REJECT")

    if not target_appointment_id:
        return

    appointment = await app_repo.get_by_id(target_appointment_id)
    if not appointment:
        logger.warning("Cita no encontrada para acción de WhatsApp: %s", target_appointment_id)
        return

    if is_accept:
        # Aceptar cita
        await app_repo.update_status(appointment.id, "CONFIRMED")
        await db.commit()
        logger.info("Cita %s confirmada exitosamente vía WhatsApp por el paciente", appointment.id)
        if from_phone:
            await notif_service.whatsapp.send_text(
                phone=from_phone,
                text="✅ ¡Cita Confirmada! Su asistencia ha sido registrada formalmente en ÍntimaSalud. ¡Le esperamos!",
            )

    elif is_reject:
        # Rechazo soberano: libera slot y sala de inmediato, pasa cobro a EXEMPT
        await app_repo.update_status(
            appointment.id,
            "REJECTED_BY_PATIENT",
            cancellation_reason="Rechazada por el paciente vía WhatsApp",
        )
        pay_record = await pay_repo.get_by_appointment_id(appointment.id)
        if pay_record:
            await pay_repo.update_status(
                pay_record.id,
                "EXEMPT",
                notes="Cita rechazada por el paciente vía WhatsApp",
            )

        # Invalidar caché en Redis para disponibilidad inmediata
        try:
            from app.core.redis import get_redis
            r = get_redis()
            keys = await r.keys(f"slots:{appointment.clinic_id}:*")
            if keys:
                await r.delete(*keys)
        except Exception as exc:
            logger.warning("No se pudo invalidar cache de slots en Redis: %s", exc)

        await db.commit()

        logger.info("Cita %s rechazada vía WhatsApp por el paciente. Slot liberado y cobro EXEMPT.", appointment.id)
        if from_phone:
            await notif_service.whatsapp.send_text(
                phone=from_phone,
                text="ℹ️ Su cita ha sido cancelada y el horario ha quedado liberado. Gracias por avisarnos.",
            )


# =====================================================================
# TWILIO WEBHOOKS
# =====================================================================

@router.post("/twilio", summary="Recepción de estados de entrega de Twilio SMS y Voz")
async def receive_twilio_event(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Callback de estado de entrega de Twilio (Messages y Calls)."""
    form_data = await request.form()
    message_sid = form_data.get("MessageSid") or form_data.get("CallSid")
    message_status = form_data.get("MessageStatus") or form_data.get("CallStatus")

    if message_sid and message_status:
        notif_repo = NotificationRepository(db)
        log_entry = await notif_repo.get_by_external_id(message_sid)
        if log_entry:
            now = datetime.datetime.utcnow()
            mapped = "DELIVERED" if message_status in ("delivered", "completed") else "FAILED" if message_status in ("failed", "undelivered", "busy", "no-answer") else "SENT"
            await notif_repo.update_status(
                log_id=log_entry.id,
                status=mapped,
                delivered_at=now if mapped == "DELIVERED" else None,
            )
            await db.commit()
            logger.info("Twilio callback recibido para %s: %s", message_sid, mapped)

    return {"status": "received"}
