from email.mime.multipart import MIMEMultipart
from unittest.mock import MagicMock, patch

from app.services.email_service import build_branded_email_html, _send_sync, LOGO_PATH


def test_build_branded_email_html_structure():
    html = build_branded_email_html(
        title="¡Tu Cita Médica ha sido Confirmada!",
        subtitle="Turno reservado con éxito.",
        content_html="Hola <strong>Paciente</strong>, tu cita está lista.",
        cta_text="Completar Mi Registro",
        cta_link="http://localhost:9000/#/patient/onboarding?token=xyz",
        details_table=[
            ("Especialista", "Dra. María Pérez"),
            ("Sede / Clínica", "Clínica VitaRecord Norte"),
            ("Fecha y Hora", "15/10/2026 a las 10:00"),
        ],
        alert_box="Al definir tu contraseña tendrás acceso directo al portal.",
    )

    assert "VitaRecord" in html
    assert "ÍntimaSalud" in html
    assert "cid:system_logo" in html
    assert "¡Tu Cita Médica ha sido Confirmada!" in html
    assert "Turno reservado con éxito." in html
    assert "Dra. María Pérez" in html
    assert "Clínica VitaRecord Norte" in html
    assert "Completar Mi Registro" in html
    assert "http://localhost:9000/#/patient/onboarding?token=xyz" in html
    assert "Al definir tu contraseña tendrás acceso directo" in html
    assert "Aviso de Privacidad Médica" in html


def test_send_sync_attaches_system_logo_cid():
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        html_body = build_branded_email_html(
            title="Cita Médica",
            content_html="Detalles de prueba",
            cta_text="Ver Citas",
            cta_link="http://localhost:9000/#/appointments/my-list"
        )

        _send_sync("paciente@ejemplo.com", "[VitaRecord] Cita Confirmada", html_body)

        assert mock_server.send_message.called
        sent_msg = mock_server.send_message.call_args[0][0]
        assert isinstance(sent_msg, MIMEMultipart)
        assert sent_msg["To"] == "paciente@ejemplo.com"
        assert sent_msg["Subject"] == "[VitaRecord] Cita Confirmada"
        assert "VitaRecord" in sent_msg["From"]

        # If logo exists, verify Content-ID
        if LOGO_PATH.exists():
            payload_parts = sent_msg.get_payload()
            cid_found = False
            for part in payload_parts:
                if part.get("Content-ID") == "<system_logo>":
                    cid_found = True
                    break
            assert cid_found is True, "El logo oficial debe estar adjunto como CID <system_logo>"
