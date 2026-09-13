"""Servicio integral de notificaciones multicanal con tolerancia a fallos y fallback automático (plan/plan.md Módulo 6 y 2.B.7).

Abstracción unificada sobre:
- WhatsApp Cloud API (Meta Oficial) con soporte para mensajes interactivos y plantillas
- Twilio SMS
- Twilio Voice (Llamadas de voz TTS)
- Email transaccional (Mailpit / SMTP)
- Notificaciones Push (FCM)

Incluye registro inmutable en notification_logs y reintento/fallback por canal alternativo.
"""

import asyncio
import datetime
import json
import logging
import os
import time
import uuid
from typing import Any

import httpx
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.appointment import Appointment
from app.models.notification_log import NotificationLog
from app.models.user import User
from app.repositories.device_token_repository import DeviceTokenRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.email_service import build_branded_email_html, send_email

logger = logging.getLogger("notification_service")



# =====================================================================
# PROVEEDORES DE MENSAJERÍA
# =====================================================================

class WhatsAppProvider:
    """Proveedor para WhatsApp Cloud API (Meta Oficial)."""

    def __init__(self) -> None:
        self.api_url = settings.WHATSAPP_API_URL
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        # Flag de pruebas para simular fallos controlados en tests de fallback
        self._simulate_failure: bool = False

    async def send_text(self, phone: str, text: str) -> tuple[bool, str | None, str | None]:
        """Envía un mensaje de texto simple."""
        if self._simulate_failure:
            return False, None, "Meta WhatsApp API Error: Simulación de fallo o número sin WhatsApp"

        clean_phone = phone.replace(" ", "").replace("-", "")
        if (
            self.access_token.startswith("dev_")
            or clean_phone.startswith("+1555")
            or clean_phone.startswith("+555")
            or clean_phone.startswith("+000")
            or "000000" in clean_phone
            or settings.ENVIRONMENT == "testing"
        ):
            # Modo emulado para desarrollo local y suites de tests automatizados
            wamid = f"wamid.HBgM{uuid.uuid4().hex[:12]}"
            logger.info("[DEV WHATSAPP] Enviando texto a %s: %s (id: %s)", phone, text, wamid)
            return True, wamid, None

        # Llamada HTTP real a Meta Graph API
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": text},
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code in (200, 201):
                    data = res.json()
                    msg_id = data.get("messages", [{}])[0].get("id")
                    return True, msg_id, None
                err_msg = f"HTTP {res.status_code}: {res.text}"
                logger.error("Error enviando WhatsApp: %s", err_msg)
                return False, None, err_msg
        except Exception as exc:
            logger.exception("Excepción conectando a WhatsApp Cloud API")
            return False, None, str(exc)

    async def send_interactive_buttons(
        self,
        phone: str,
        body_text: str,
        buttons: list[dict[str, str]],
        header_text: str | None = None,
        footer_text: str | None = None,
    ) -> tuple[bool, str | None, str | None]:
        """Envía un mensaje interactivo con botones (Aceptar / Rechazar cita)."""
        if self._simulate_failure:
            return False, None, "Meta WhatsApp API Error: Servicio no disponible"

        clean_phone = phone.replace(" ", "").replace("-", "")
        if (
            self.access_token.startswith("dev_")
            or clean_phone.startswith("+1555")
            or clean_phone.startswith("+555")
            or clean_phone.startswith("+000")
            or "000000" in clean_phone
            or settings.ENVIRONMENT == "testing"
        ):
            wamid = f"wamid.HBgM{uuid.uuid4().hex[:12]}"
            logger.info(
                "[DEV WHATSAPP INTERACTIVO] A %s: %s | Botones: %s (id: %s)",
                phone,
                body_text,
                [b.get("title") for b in buttons],
                wamid,
            )
            return True, wamid, None

        url = f"{self.api_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        button_elements = [
            {
                "type": "reply",
                "reply": {
                    "id": b["id"],
                    "title": b["title"][:20],  # Máximo 20 caracteres exigido por Meta
                },
            }
            for b in buttons
        ]

        action_payload: dict[str, Any] = {"buttons": button_elements}
        interactive_data: dict[str, Any] = {
            "type": "button",
            "body": {"text": body_text},
            "action": action_payload,
        }
        if header_text:
            interactive_data["header"] = {"type": "text", "text": header_text}
        if footer_text:
            interactive_data["footer"] = {"text": footer_text}

        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "interactive",
            "interactive": interactive_data,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code in (200, 201):
                    data = res.json()
                    msg_id = data.get("messages", [{}])[0].get("id")
                    return True, msg_id, None
                err_msg = f"HTTP {res.status_code}: {res.text}"
                return False, None, err_msg
        except Exception as exc:
            return False, None, str(exc)

    async def send_template(
        self,
        phone: str,
        template_name: str = "hello_world",
        language_code: str = "en_US",
        components: list[dict[str, Any]] | None = None,
    ) -> tuple[bool, str | None, str | None]:
        """Envía una plantilla oficial de Meta WhatsApp (requerida fuera de ventana de 24h)."""
        if self._simulate_failure:
            return False, None, "Meta WhatsApp API Error: Simulación de fallo"

        clean_phone = phone.replace(" ", "").replace("-", "")
        if (
            self.access_token.startswith("dev_")
            or clean_phone.startswith("+1555")
            or clean_phone.startswith("+555")
            or clean_phone.startswith("+000")
            or "000000" in clean_phone
            or settings.ENVIRONMENT == "testing"
        ):
            wamid = f"wamid.HBgM{uuid.uuid4().hex[:12]}"
            logger.info("[DEV WHATSAPP TEMPLATE] A %s: plantilla %s", phone, template_name)
            return True, wamid, None

        url = f"{self.api_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }
        if components:
            payload["template"]["components"] = components

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code in (200, 201):
                    data = res.json()
                    msg_id = data.get("messages", [{}])[0].get("id")
                    return True, msg_id, None
                err_msg = f"HTTP {res.status_code}: {res.text}"
                logger.error("Error enviando WhatsApp Template: %s", err_msg)
                return False, None, err_msg
        except Exception as exc:
            logger.exception("Excepción enviando plantilla WhatsApp")
            return False, None, str(exc)


class TwilioSMSProvider:
    """Proveedor para envío de SMS transaccionales vía Twilio REST API."""

    def __init__(self) -> None:
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_FROM_NUMBER
        self._simulate_failure: bool = False

    async def send_sms(self, phone: str, text: str) -> tuple[bool, str | None, str | None]:
        if self._simulate_failure:
            return False, None, "Twilio SMS Error: Simulación de fallo en red telefónica"

        if self.account_sid.startswith("dev_"):
            sid = f"SM{uuid.uuid4().hex}"
            logger.info("[DEV TWILIO SMS] Enviando SMS a %s: %s (Sid: %s)", phone, text, sid)
            return True, sid, None

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = {
            "To": phone,
            "From": self.from_number,
            "Body": text,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, data=data, auth=(self.account_sid, self.auth_token))
                if res.status_code in (200, 201):
                    sid = res.json().get("sid")
                    return True, sid, None
                err = f"Twilio HTTP {res.status_code}: {res.text}"
                return False, None, err
        except Exception as exc:
            return False, None, str(exc)


class TwilioVoiceProvider:
    """Proveedor para llamadas telefónicas automáticas TTS (Text-to-Speech) vía Twilio."""

    def __init__(self) -> None:
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_FROM_NUMBER

    async def make_call(self, phone: str, speech_text: str) -> tuple[bool, str | None, str | None]:
        if self.account_sid.startswith("dev_"):
            sid = f"CA{uuid.uuid4().hex}"
            logger.info("[DEV TWILIO VOICE] Llamando a %s: '%s' (Sid: %s)", phone, speech_text, sid)
            return True, sid, None

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Calls.json"
        twiml = f"<Response><Say language='es-ES' voice='Polly.Conchita'>{speech_text}</Say></Response>"
        data = {
            "To": phone,
            "From": self.from_number,
            "Twiml": twiml,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, data=data, auth=(self.account_sid, self.auth_token))
                if res.status_code in (200, 201):
                    sid = res.json().get("sid")
                    return True, sid, None
                return False, None, f"Twilio Voice HTTP {res.status_code}: {res.text}"
        except Exception as exc:
            return False, None, str(exc)


class EmailProvider:
    """Proveedor de correos electrónicos transaccionales con branding oficial."""

    async def send(
        self,
        to_email: str,
        subject: str,
        title: str,
        content_html: str,
        cta_text: str | None = None,
        cta_link: str | None = None,
        details_table: list[tuple[str, str]] | None = None,
    ) -> tuple[bool, str | None, str | None]:
        try:
            html = build_branded_email_html(
                title=title,
                content_html=content_html,
                cta_text=cta_text,
                cta_link=cta_link,
                details_table=details_table,
            )
            await send_email(to_email=to_email, subject=subject, body_html=html)
            return True, f"email_{uuid.uuid4().hex[:12]}", None
        except Exception as exc:

            logger.exception("Error enviando email")
            return False, None, str(exc)


class FCMProvider:
    """Proveedor para Firebase Cloud Messaging (FCM HTTP v1 Oficial de Google).
    
    Envía notificaciones push a dispositivos móviles (Android / iOS con Capacitor)
    y navegadores web (Web Push) mediante la API HTTP v1 con autenticación OAuth2
    Service Account y fallback automático.
    """

    def __init__(self) -> None:
        self.credentials_file = settings.FIREBASE_CREDENTIALS_FILE
        self.project_id = settings.FCM_PROJECT_ID
        self.api_url = settings.FCM_API_URL
        self._simulate_failure: bool = False
        self._cached_token: str | None = None
        self._token_expires_at: float = 0.0

    async def _get_oauth2_access_token(self) -> str | None:
        """Obtiene o renueva el token Bearer de Google Cloud mediante el Service Account."""
        now = time.time()
        if self._cached_token and now < (self._token_expires_at - 120):
            return self._cached_token

        if not self.credentials_file or not os.path.exists(self.credentials_file):
            return None

        try:
            with open(self.credentials_file, "r") as f:
                sa = json.load(f)

            now_int = int(now)
            payload = {
                "iss": sa["client_email"],
                "sub": sa["client_email"],
                "aud": "https://oauth2.googleapis.com/token",
                "iat": now_int,
                "exp": now_int + 3600,
                "scope": "https://www.googleapis.com/auth/firebase.messaging",
            }
            assertion = jwt.encode(payload, sa["private_key"], algorithm="RS256")
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                        "assertion": assertion,
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    self._cached_token = data.get("access_token")
                    expires_in = data.get("expires_in", 3600)
                    self._token_expires_at = now + expires_in
                    logger.info("Google OAuth2 Bearer token para FCM renovado con éxito (expira en %ds)", expires_in)
                    return self._cached_token
                logger.error("Error obteniendo token Google OAuth2: %s", res.text)
                return None
        except Exception as exc:
            logger.exception("Excepción obteniendo OAuth2 token de Firebase: %s", exc)
            return None

    async def send_push(
        self,
        token: str,
        title: str,
        body: str,
        data_payload: dict[str, Any] | None = None,
        priority: str = "high",
    ) -> tuple[bool, str | None, str | None]:
        """Envía una notificación Push a un dispositivo registrado vía Google HTTP v1."""
        if self._simulate_failure:
            return False, None, "FCM Error: Simulación de fallo en Firebase Cloud Messaging"

        # Modo emulado para tests o si el token es ficticio de prueba
        if token.startswith("fcm_test_") or token.startswith("fcm_fail_") or token.startswith("fcm_web_"):
            fcm_id = f"fcm_projects_{self.project_id}_messages_{uuid.uuid4().hex[:12]}"
            logger.info(
                "[DEV FCM PUSH] Enviando Push a token de prueba %s...: '%s - %s' (id: %s)",
                token[:12], title, body, fcm_id,
            )
            return True, fcm_id, None

        access_token = await self._get_oauth2_access_token()
        if not access_token:
            # Si no hay credenciales disponibles, responder en modo simulado para desarrollo
            fcm_id = f"fcm_projects_{self.project_id}_messages_{uuid.uuid4().hex[:12]}"
            logger.info(
                "[DEV FCM PUSH] Modo desarrollo sin credenciales reales para token %s: '%s - %s'",
                token[:12], title, body,
            )
            return True, fcm_id, None

        # Despacho real a Google Firebase HTTP v1 API
        url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        message_body = {
            "message": {
                "token": token,
                "notification": {
                    "title": title,
                    "body": body,
                },
                "data": {k: str(v) for k, v in (data_payload or {}).items()},
                "android": {
                    "priority": "HIGH" if priority == "high" else "NORMAL",
                    "notification": {"sound": "default"},
                },
                "apns": {
                    "payload": {
                        "aps": {"sound": "default", "content-available": 1}
                    }
                },
            }
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=message_body, headers=headers)
                if res.status_code == 200:
                    name = res.json().get("name", f"fcm_{uuid.uuid4().hex[:12]}")
                    logger.info("Notificación FCM HTTP v1 entregada con éxito: %s", name)
                    return True, name, None

                res_err = res.text
                if res.status_code == 404 or "UNREGISTERED" in res_err or "NOT_FOUND" in res_err:
                    return False, None, "FCM Error: NotRegistered - Dispositivo no registrado o token revocado"
                return False, None, f"FCM HTTP {res.status_code}: {res_err}"
        except Exception as exc:
            logger.exception("Error de red conectando con Firebase FCM HTTP v1: %s", exc)
            return False, None, str(exc)


# =====================================================================
# SERVICIO CENTRAL Y ORQUESTADOR DE NOTIFICACIONES
# =====================================================================

class NotificationService:
    """Orquestador de notificaciones multicanal con fallback y registro de auditoría (plan/plan.md 2.B.7)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = NotificationRepository(db)
        self.device_repo = DeviceTokenRepository(db)
        self.whatsapp = WhatsAppProvider()
        self.twilio_sms = TwilioSMSProvider()
        self.twilio_voice = TwilioVoiceProvider()
        self.email = EmailProvider()
        self.fcm = FCMProvider()

    def determine_channels_for_user(self, user: User | None) -> list[str]:
        """Determina la lista priorizada de canales según preferencias y reglas de seguridad."""
        if not user:
            return ["PUSH", "EMAIL", "SMS"]

        preferred = user.preferred_notification_channels or []
        if preferred and isinstance(preferred, list):
            channels = [ch.upper() for ch in preferred]
        else:
            # Por defecto omnicanal seguro (Push FCM + WhatsApp + Email)
            channels = ["PUSH", "WHATSAPP", "EMAIL"]

        # Si el usuario tiene teléfono registrado pero no incluyó SMS/Voz como respaldo,
        # asegurar respaldo telefónico en la cadena de fallback
        if user.phone:
            if "SMS" not in channels:
                channels.append("SMS")
            if "VOICE_CALL" not in channels and user.role == "PATIENT":
                channels.append("VOICE_CALL")

        return channels

    async def send_multichannel_notification(
        self,
        recipient: User | None,
        subject: str,
        message: str,
        phone: str | None = None,
        email: str | None = None,
        appointment_id: str | None = None,
        incident_id: str | None = None,
        interactive_buttons: list[dict[str, str]] | None = None,
        metadata_payload: dict[str, Any] | None = None,
    ) -> list[NotificationLog]:
        """Envía notificación respetando la cadena de fallback automático.
        
        Si el canal primario falla (ej. WhatsApp no disponible o sin entrega),
        se ejecuta de inmediato el canal secundario (SMS / Voz / Email) registrando
        cada intento en notification_logs.
        """
        dest_phone = phone or (recipient.phone if recipient else None)
        dest_email = email or (recipient.email if recipient else None)
        channels = self.determine_channels_for_user(recipient)

        logs_created: list[NotificationLog] = []
        delivery_succeeded = False
        attempt_number = 1

        for channel in channels:
            if delivery_succeeded:
                break

            now = datetime.datetime.utcnow()
            success = False
            external_id = None
            error_msg = None

            if channel == "PUSH" and recipient:
                tokens = await self.device_repo.get_active_tokens_for_user(recipient.id)
                if not tokens:
                    logger.info("Usuario %s no tiene dispositivos Push (FCM) registrados, continuando fallback", recipient.id)
                    continue

                push_succeeded = False
                fcm_ext_ids: list[str] = []
                last_err = None
                for dev in tokens:
                    p_ok, p_id, p_err = await self.fcm.send_push(
                        token=dev.fcm_token,
                        title=subject,
                        body=message,
                        data_payload={
                            "appointment_id": appointment_id or "",
                            "incident_id": incident_id or "",
                            **(metadata_payload or {}),
                        },
                        priority="high" if incident_id else "normal",
                    )
                    if p_ok:
                        push_succeeded = True
                        if p_id:
                            fcm_ext_ids.append(p_id)
                    else:
                        last_err = p_err
                        if p_err and ("NotRegistered" in p_err or "InvalidRegistration" in p_err):
                            await self.device_repo.deactivate_token(dev.fcm_token)

                if push_succeeded:
                    success = True
                    external_id = fcm_ext_ids[0] if fcm_ext_ids else None
                    if metadata_payload is None:
                        metadata_payload = {}
                    metadata_payload["fcm_message_ids"] = fcm_ext_ids
                else:
                    success = False
                    error_msg = last_err or "No se pudo entregar Push a ningún dispositivo registrado"

            elif channel == "WHATSAPP" and dest_phone:
                if interactive_buttons:
                    success, external_id, error_msg = await self.whatsapp.send_interactive_buttons(
                        phone=dest_phone,
                        body_text=message,
                        buttons=interactive_buttons,
                        header_text=subject,
                    )
                else:
                    success, external_id, error_msg = await self.whatsapp.send_text(
                        phone=dest_phone,
                        text=f"*{subject}*\n\n{message}",
                    )

            elif channel == "SMS" and dest_phone:
                sms_body = f"{subject}: {message}"
                # Recorte de longitud estándar para SMS
                if len(sms_body) > 160:
                    sms_body = sms_body[:157] + "..."
                success, external_id, error_msg = await self.twilio_sms.send_sms(
                    phone=dest_phone,
                    text=sms_body,
                )

            elif channel == "VOICE_CALL" and dest_phone:
                call_text = f"Hola. Mensaje de ÍntimaSalud: {message}"
                success, external_id, error_msg = await self.twilio_voice.make_call(
                    phone=dest_phone,
                    speech_text=call_text,
                )

            elif channel == "EMAIL" and dest_email:
                success, external_id, error_msg = await self.email.send(
                    to_email=dest_email,
                    subject=subject,
                    title=subject,
                    content_html=f"<p>{message}</p>",
                )

            else:
                # Canal no ejecutable por falta de dato (ej. sin teléfono o email)
                continue

            # Crear log inmutable del intento
            log = NotificationLog(
                incident_id=incident_id,
                appointment_id=appointment_id,
                recipient_id=recipient.id if recipient else None,
                channel=channel,
                status="SENT" if success else "FAILED",
                attempt_number=attempt_number,
                sent_at=now,
                delivered_at=now if success and channel in ("EMAIL", "SMS", "WHATSAPP", "PUSH") else None,
                error_message=error_msg[:250] if error_msg else None,
                external_message_id=external_id,
                metadata_payload=metadata_payload,
            )
            await self.repo.create(log)
            logs_created.append(log)

            if success:
                delivery_succeeded = True
                logger.info(
                    "Notificación entregada con éxito vía %s a %s (intento %d)",
                    channel,
                    dest_phone or dest_email,
                    attempt_number,
                )
            else:
                logger.warning(
                    "Fallo en envío vía %s a %s: %s. Activando fallback a siguiente canal...",
                    channel,
                    dest_phone or dest_email,
                    error_msg,
                )
                attempt_number += 1

        # Emitir notificación In-App en tiempo real si el destinatario es un usuario registrado
        if recipient:
            in_app_log = NotificationLog(
                incident_id=incident_id,
                appointment_id=appointment_id,
                recipient_id=recipient.id,
                channel="IN_APP",
                status="DELIVERED",
                attempt_number=1,
                sent_at=datetime.datetime.utcnow(),
                delivered_at=datetime.datetime.utcnow(),
                is_read=False,
                metadata_payload={
                    **(metadata_payload or {}),
                    "subject": subject,
                    "message": message,
                },
            )
            await self.repo.create(in_app_log)
            logs_created.append(in_app_log)

            try:
                from app.core.notification_hub import notification_hub
                await notification_hub.notify_user(
                    user_id=recipient.id,
                    event_type="IN_APP_NOTIFICATION",
                    data={
                        "id": in_app_log.id,
                        "subject": subject,
                        "message": message,
                        "appointment_id": appointment_id,
                        "incident_id": incident_id,
                        "channel": "IN_APP",
                        "metadata": metadata_payload,
                        "created_at": in_app_log.sent_at.isoformat(),
                    },
                )
            except Exception as exc:
                logger.warning("No se pudo emitir evento WebSocket In-App: %s", exc)

        await self.db.commit()
        return logs_created


    # -----------------------------------------------------------------
    # CASOS DE USO DE NEGOCIO
    # -----------------------------------------------------------------

    async def send_appointment_proposal(
        self,
        appointment: Appointment,
        patient: User,
        doctor: User,
        clinic_name: str,
    ) -> list[NotificationLog]:
        """Notifica al paciente una cita asignada por recepción en PENDING_PATIENT_ACCEPTANCE con botones interactivos."""
        date_str = appointment.start_time.strftime("%d/%m/%Y a las %H:%M")
        doctor_name = doctor.full_name or f"Dr. {doctor.email}"

        subject = "Propuesta de Cita Médica • ÍntimaSalud"
        message = (
            f"Estimado(a) {patient.full_name or 'paciente'}, el centro médico {clinic_name} "
            f"le ha agendado una consulta con {doctor_name} para el {date_str}. "
            "Por favor, confirme su asistencia o rechace la cita para liberar el turno."
        )

        buttons = [
            {"id": f"accept_appointment_{appointment.id}", "title": "Aceptar Cita"},
            {"id": f"reject_appointment_{appointment.id}", "title": "Rechazar Cita"},
        ]

        metadata = {
            "type": "APPOINTMENT_PROPOSAL",
            "appointment_id": appointment.id,
            "clinic_name": clinic_name,
            "doctor_name": doctor_name,
        }

        # Despachar por canales del paciente
        return await self.send_multichannel_notification(
            recipient=patient,
            subject=subject,
            message=message,
            appointment_id=appointment.id,
            interactive_buttons=buttons,
            metadata_payload=metadata,
        )

    async def send_appointment_reminder(
        self,
        appointment: Appointment,
        patient: User,
        doctor: User,
        clinic_name: str,
        room_name: str | None,
        reminder_stage: str,  # '24H' o '2H'
    ) -> list[NotificationLog]:
        """Envía recordatorio programado de cita (24 horas o 2 horas previas)."""
        date_str = appointment.start_time.strftime("%d/%m/%Y a las %H:%M")
        doctor_name = doctor.full_name or f"Dr. {doctor.email}"
        room_info = f" en el consultorio {room_name}" if room_name else ""

        if reminder_stage == "24H":
            time_label = "mañana"
            subject = "Recordatorio de Cita Médica (24 Horas) • ÍntimaSalud"
        else:
            time_label = "en 2 horas"
            subject = "Recordatorio de Cita Próxima (2 Horas) • ÍntimaSalud"

        message = (
            f"Hola {patient.full_name or 'paciente'}, le recordamos que tiene cita médica programada {time_label} "
            f"({date_str}) con {doctor_name}{room_info} en {clinic_name}."
        )

        metadata = {
            "type": "APPOINTMENT_REMINDER",
            "reminder_stage": reminder_stage,
            "appointment_id": appointment.id,
            "scheduled_time": appointment.start_time.isoformat(),
        }

        return await self.send_multichannel_notification(
            recipient=patient,
            subject=subject,
            message=message,
            appointment_id=appointment.id,
            metadata_payload=metadata,
        )

    async def send_new_appointment_to_doctor(
        self,
        appointment: Appointment,
        doctor: User,
        patient: User,
        clinic_name: str,
        is_pending_approval: bool = False,
    ) -> list[NotificationLog]:
        """Notifica al médico que un paciente ha reservado o solicitado una cita en su agenda."""
        date_str = appointment.start_time.strftime("%d/%m/%Y a las %H:%M")
        patient_name = patient.full_name or patient.email
        reason_text = appointment.reason or "Consulta médica general"

        if is_pending_approval:
            subject = f"Nueva solicitud de cita médica: {patient_name}"
            message = (
                f"El paciente {patient_name} ha solicitado una cita para el {date_str} "
                f"en {clinic_name}. Motivo: {reason_text}. Pendiente de tu aprobación."
            )
            event_type = "APPOINTMENT_REQUEST"
        else:
            subject = f"Nueva cita agendada: {patient_name}"
            message = (
                f"El paciente {patient_name} ha confirmado una cita para el {date_str} "
                f"en {clinic_name}. Motivo: {reason_text}."
            )
            event_type = "NEW_APPOINTMENT"

        metadata = {
            "type": event_type,
            "appointment_id": appointment.id,
            "patient_name": patient_name,
            "scheduled_time": appointment.start_time.isoformat(),
            "clinic_name": clinic_name,
        }

        return await self.send_multichannel_notification(
            recipient=doctor,
            subject=subject,
            message=message,
            appointment_id=appointment.id,
            metadata_payload=metadata,
        )
