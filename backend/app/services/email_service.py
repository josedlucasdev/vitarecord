"""Servicio de envio de correos electronicos transaccionales con branding y logo institucional (plan/plan.md seccion 1.C y 2.A)."""

import asyncio
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from pathlib import Path
import smtplib

from app.core.config import settings

logger = logging.getLogger("email_service")

# Ruta al logo oficial institucional
LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "vitarecord-logo.png"


def build_branded_email_html(
    title: str,
    subtitle: str | None = None,
    content_html: str | None = None,
    cta_text: str | None = None,
    cta_link: str | None = None,
    details_table: list[tuple[str, str]] | None = None,
    alert_box: str | None = None,
    footer_note: str | None = None,
) -> str:
    """Genera el HTML estandarizado con el branding oficial, colores, logo y estructura de VitaRecord / ÍntimaSalud."""
    subtitle_section = (
        f'<p style="font-size: 14px; color: #475569; margin: 0 0 20px 0; line-height: 1.6;">{subtitle}</p>'
        if subtitle
        else ""
    )

    content_section = (
        f'<div style="font-size: 14px; color: #334155; line-height: 1.6; margin-bottom: 20px;">{content_html}</div>'
        if content_html
        else ""
    )

    table_section = ""
    if details_table:
        rows_html = ""
        for idx, (label, val) in enumerate(details_table):
            border_style = "border-bottom: 1px solid #f1f5f9;" if idx < len(details_table) - 1 else ""
            rows_html += f"""
            <tr style="{border_style}">
                <td style="padding: 9px 0; color: #64748b; width: 130px; font-weight: 500;">{label}:</td>
                <td style="padding: 9px 0; font-weight: 600; color: #0f172a;">{val}</td>
            </tr>
            """
        table_section = f"""
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px; padding: 18px 22px; margin: 22px 0;">
            <p style="margin: 0 0 10px 0; font-size: 11px; color: #0d9488; text-transform: uppercase; font-weight: 800; letter-spacing: 0.8px;">
                Información del Servicio
            </p>
            <table style="width: 100%; font-size: 13.5px; border-collapse: collapse;">
                {rows_html}
            </table>
        </div>
        """

    alert_section = ""
    if alert_box:
        alert_section = f"""
        <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 14px 18px; margin: 20px 0; font-size: 13px; color: #166534; line-height: 1.5;">
            {alert_box}
        </div>
        """

    cta_section = ""
    if cta_text and cta_link:
        cta_section = f"""
        <div style="text-align: center; margin: 32px 0 24px 0;">
            <a href="{cta_link}" style="display: inline-block; background: linear-gradient(135deg, #0d9488 0%, #0891b2 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; font-weight: 700; font-size: 14px; border-radius: 12px; box-shadow: 0 4px 12px -2px rgba(13, 148, 136, 0.35); letter-spacing: 0.2px;">
                {cta_text} &rarr;
            </a>
            <p style="font-size: 11px; color: #94a3b8; margin-top: 12px;">Enlace seguro e intransferible. Válido por 48 horas.</p>
        </div>
        """

    footer_note_section = (
        f'<p style="font-size: 12px; color: #64748b; margin: 16px 0; line-height: 1.5;">{footer_note}</p>'
        if footer_note
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="margin: 0; padding: 24px 12px; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 20px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.08);">
        <!-- Cabecera Institucional VitaRecord / ÍntimaSalud -->
        <div style="background: linear-gradient(135deg, #0f766e 0%, #0e7490 50%, #1d4ed8 100%); padding: 32px 24px; text-align: center; color: #ffffff;">
            <div style="margin-bottom: 12px;">
                <table align="center" border="0" cellpadding="0" cellspacing="0" style="margin: 0 auto;">
                    <tr>
                        <td style="background-color: #ffffff; border-radius: 16px; padding: 10px 14px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.15);">
                            <img src="cid:system_logo" alt="VitaRecord" width="48" height="48" style="display: block; width: 48px; height: 48px; object-fit: contain;" />
                        </td>
                    </tr>
                </table>
            </div>
            <h1 style="margin: 0; font-size: 25px; font-weight: 800; letter-spacing: -0.5px; color: #ffffff;">
                VitaRecord
            </h1>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #ccfbf1; font-weight: 500;">
                Plataforma Clínica y Expediente Médico Digital • ÍntimaSalud
            </p>
        </div>

        <!-- Cuerpo del Mensaje -->
        <div style="padding: 32px 26px 24px 26px; color: #334155;">
            <h2 style="margin: 0 0 16px 0; font-size: 19px; color: #0f172a; font-weight: 700; letter-spacing: -0.3px;">
                {title}
            </h2>
            
            {subtitle_section}
            {content_section}
            {table_section}
            {alert_section}
            {cta_section}
            {footer_note_section}

            <!-- Pie de Página Institucional -->
            <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 28px 0 20px 0;" />
            <p style="font-size: 12px; color: #64748b; text-align: center; margin: 0 0 4px 0; font-weight: 700;">
                VitaRecord • Identidad y Expediente Médico Digital
            </p>
            <p style="font-size: 11px; color: #94a3b8; text-align: center; margin: 0 0 12px 0;">
                ÍntimaSalud — Red Integral de Cuidado de la Salud
            </p>
            <p style="font-size: 10px; color: #cbd5e1; text-align: center; margin: 0; line-height: 1.5;">
                Aviso de Privacidad Médica: Este correo electrónico y cualquier archivo adjunto contienen información confidencial dirigida exclusivamente a su destinatario. Si usted no es el receptor autorizado, se le notifica que cualquier divulgación o copia está prohibida.
            </p>
        </div>
    </div>
</body>
</html>"""


def _send_sync(to_email: str, subject: str, body_html: str) -> None:
    """Envía un correo multipart con el logo embebido via CID."""
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = "VitaRecord • ÍntimaSalud <soporte@intimasalud.com>"
    msg["To"] = to_email

    msg_alt = MIMEMultipart("alternative")
    msg.attach(msg_alt)

    plain_fallback = "Por favor visualice este mensaje en un cliente de correo con soporte para HTML."
    msg_alt.attach(MIMEText(plain_fallback, "plain", "utf-8"))
    msg_alt.attach(MIMEText(body_html, "html", "utf-8"))

    # Adjuntar el logo institucional oficial si existe en assets
    if LOGO_PATH.exists():
        try:
            with open(LOGO_PATH, "rb") as f:
                logo_data = f.read()
            img = MIMEImage(logo_data, _subtype="png")
            img.add_header("Content-ID", "<system_logo>")
            img.add_header("Content-Disposition", "inline", filename="vitarecord-logo.png")
            msg.attach(img)
        except Exception as exc:  # noqa: BLE001
            logger.warning("No se pudo adjuntar el logo institucional al correo: %s", exc)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=5) as server:
            server.send_message(msg)
            logger.info("Correo enviado exitosamente a %s: %s", to_email, subject)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Fallo al enviar correo a %s: %s", to_email, exc)


async def send_email(to_email: str, subject: str, body_html: str) -> None:
    """Envia un correo transaccional asincronamente sin bloquear el event loop."""
    await asyncio.to_thread(_send_sync, to_email, subject, body_html)

