"""Servicio de envio de correos electronicos transaccionales (plan/plan.md seccion 2.A)."""

import asyncio
from email.message import EmailMessage
import logging
import smtplib

from app.core.config import settings

logger = logging.getLogger("email_service")


def _send_sync(to_email: str, subject: str, body_html: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "soporte@intimasalud.com"
    msg["To"] = to_email
    msg.set_content(body_html, subtype="html")

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=5) as server:
            server.send_message(msg)
            logger.info("Correo enviado a %s: %s", to_email, subject)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Fallo al enviar correo a %s: %s", to_email, exc)


async def send_email(to_email: str, subject: str, body_html: str) -> None:
    """Envia un correo transaccional asincronamente sin bloquear el event loop."""
    await asyncio.to_thread(_send_sync, to_email, subject, body_html)
