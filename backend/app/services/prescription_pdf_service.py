"""Generador de Recetas Medicas en PDF con Codigo QR criptografico (plan/plan.md 2.B.8).

Genera documentos PDF conformes con normativas clinicas:
- Membrete institucional de la clinica.
- Datos del facultativo con matricula verificada.
- Datos del paciente titular o dependiente.
- Tabla posologica estructurada de medicamentos.
- Codigo QR con enlace a la URL publica de verificacion criptografica (SHA-256).
- Sello de firma digitalizada.
"""

import io
import os
from pathlib import Path
import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def get_vitarecord_logo_path() -> str | None:
    """Obtiene la ruta del isotipo institucional de VitaRecord para documentos exportados."""
    candidate_paths = [
        Path(__file__).resolve().parent.parent / "assets" / "vitarecord-logo.png",
        Path("/Volumes/M2STORAGE/WorkSpace/intimasalud/appcitas/backend/app/assets/vitarecord-logo.png"),
        Path("/app/app/assets/vitarecord-logo.png"),
    ]
    for p in candidate_paths:
        if p.exists():
            return str(p)
    return None


def generate_prescription_pdf(
    prescription_code: str,
    verification_hash: str,
    clinic_name: str,
    clinic_address: str | None,
    doctor_name: str,
    doctor_specialty: str | None,
    doctor_license: str | None,
    patient_name: str,
    issued_date_str: str,
    expires_date_str: str,
    diagnosis_summary: str | None,
    items: list[dict],
    notes: str | None = None,
    verification_base_url: str = "http://localhost:9000/verify-prescription",
) -> bytes:
    """Genera el documento PDF de la receta medica y retorna sus bytes binarios."""
    clinic_name = clinic_name or "Clínica ÍntimaSalud"
    doctor_name = doctor_name or "Médico Especialista"
    patient_name = patient_name or "Paciente Titular"
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Estilos tipograficos personalizados
    title_style = ParagraphStyle(
        "ClinicTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#0f766e"),  # Teal-700
    )
    subtitle_style = ParagraphStyle(
        "ClinicSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#64748b"),
    )
    rx_header_style = ParagraphStyle(
        "RxHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        textColor=colors.HexColor("#047857"),
    )
    label_style = ParagraphStyle(
        "LabelStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )
    value_style = ParagraphStyle(
        "ValueStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
    )
    cell_head_style = ParagraphStyle(
        "CellHead",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )
    cell_body_style = ParagraphStyle(
        "CellBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1e293b"),
    )

    elements = []

    # 1. Encabezado de la Clinica con Branding VitaRecord
    logo_path = get_vitarecord_logo_path()
    if logo_path:
        logo_img = Image(logo_path, width=42, height=42)
        header_data = [
            [
                logo_img,
                Paragraph(f"<b>{clinic_name}</b>", title_style),
                Paragraph(
                    f"<b>FOLIO:</b> {prescription_code}<br/><b>EMISIÓN:</b> {issued_date_str}<br/><b>VENCE:</b> {expires_date_str}",
                    ParagraphStyle("Folio", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=11, alignment=2),
                ),
            ],
            [
                "",
                Paragraph(clinic_address or "Red Médica Especializada · VitaRecord Platform", subtitle_style),
                "",
            ],
        ]
        header_table = Table(header_data, colWidths=[50, 332, 158])
        header_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("SPAN", (0, 0), (0, 1)),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ])
        )
    else:
        header_data = [
            [
                Paragraph(f"<b>{clinic_name}</b>", title_style),
                Paragraph(
                    f"<b>FOLIO:</b> {prescription_code}<br/><b>EMISIÓN:</b> {issued_date_str}<br/><b>VENCE:</b> {expires_date_str}",
                    ParagraphStyle("Folio", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=11, alignment=2),
                ),
            ],
            [
                Paragraph(clinic_address or "Red Médica Especializada · VitaRecord Platform", subtitle_style),
                "",
            ],
        ]
        header_table = Table(header_data, colWidths=[380, 160])
        header_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ])
        )
    elements.append(header_table)
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f766e"), spaceAfter=10))

    # 2. Datos del Medico y Paciente
    info_data = [
        [
            Paragraph("<b>MÉDICO TRATANTE:</b>", label_style),
            Paragraph(doctor_name, value_style),
            Paragraph("<b>PACIENTE:</b>", label_style),
            Paragraph(patient_name, value_style),
        ],
        [
            Paragraph("<b>ESPECIALIDAD:</b>", label_style),
            Paragraph(doctor_specialty or "Medicina General", value_style),
            Paragraph("<b>DIAGNÓSTICO:</b>", label_style),
            Paragraph(diagnosis_summary or "Atención Médica Integral", value_style),
        ],
    ]
    info_table = Table(info_data, colWidths=[100, 170, 80, 190])
    info_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    elements.append(info_table)
    elements.append(Spacer(1, 14))

    # 3. Seccion RP / Prescripcion
    elements.append(Paragraph("<b>Rp. / PRESCRIPCIÓN MÉDICA</b>", rx_header_style))
    elements.append(Spacer(1, 6))

    # Tabla de Medicamentos
    meds_data = [
        [
            Paragraph("Medicamento / Principio Activo", cell_head_style),
            Paragraph("Dosis", cell_head_style),
            Paragraph("Frecuencia", cell_head_style),
            Paragraph("Duración", cell_head_style),
            Paragraph("Indicaciones Específicas", cell_head_style),
        ]
    ]

    for item in items:
        meds_data.append([
            Paragraph(f"<b>{item.get('medication', '')}</b>", cell_body_style),
            Paragraph(item.get("dosage", "-"), cell_body_style),
            Paragraph(item.get("frequency", "-"), cell_body_style),
            Paragraph(item.get("duration", "-"), cell_body_style),
            Paragraph(item.get("instructions", "-"), cell_body_style),
        ])

    meds_table = Table(meds_data, colWidths=[160, 70, 90, 70, 150])
    meds_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ])
    )
    elements.append(meds_table)
    elements.append(Spacer(1, 12))

    if notes:
        elements.append(Paragraph(f"<b>Instrucciones y Cuidados Generales:</b> {notes}", value_style))
        elements.append(Spacer(1, 14))

    # 4. Generar Codigo QR con URL de Verificacion Publica
    verify_url = f"{verification_base_url}/{verification_hash}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=1,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#0f766e", back_color="white")

    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    reportlab_qr = Image(qr_buffer, width=1.1 * inch, height=1.1 * inch)

    # 5. Footer: QR + Firma + Hash SHA-256
    footer_data = [
        [
            reportlab_qr,
            Paragraph(
                f"<b>VERIFICACIÓN FARMACÉUTICA EN LÍNEA:</b><br/>"
                f"Escanee este código QR para validar la autenticidad y vigencia de esta receta médica.<br/>"
                f"<font size='6.5' color='#64748b'>Token Criptográfico SHA-256: {verification_hash}</font>",
                ParagraphStyle("QRDesc", parent=styles["Normal"], fontName="Helvetica", fontSize=7.5, leading=10, textColor=colors.HexColor("#334155")),
            ),
            Paragraph(
                f"____________________________________<br/>"
                f"<b>{doctor_name}</b><br/>"
                f"<font size='7' color='#475569'>Especialista Clínico · Red VitaRecord<br/>Firma Electrónica Autorizada</font>",
                ParagraphStyle("SignBox", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=11, alignment=1),
            ),
        ]
    ]
    footer_table = Table(footer_data, colWidths=[90, 260, 190])
    footer_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    elements.append(Spacer(1, 16))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))
    elements.append(footer_table)

    # 6. Sello Institucional VitaRecord
    branding_bar = Paragraph(
        "Documento clínico oficial emitido mediante la plataforma <b>VitaRecord</b> · Cifrado y validación criptográfica conforme a normativas de salud.",
        ParagraphStyle("FootBranding", parent=styles["Normal"], fontName="Helvetica", fontSize=6.5, leading=8, alignment=1, textColor=colors.HexColor("#64748b")),
    )
    elements.append(Spacer(1, 4))
    elements.append(branding_bar)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
