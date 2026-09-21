"""Generador de Historia Clínica Integral en PDF (plan/plan.md 2.B.8).

Genera documentos PDF clínicos completos, individualizados y paginados:
- Membrete institucional con isotipo de VitaRecord y datos de la clínica.
- Ficha basal del paciente (datos demográficos, grupo sanguíneo, alergias y antecedentes).
- Diferenciación explícita si se trata de un paciente titular o familiar dependiente.
- Cronología completa de consultas médicas (diagnósticos, CIE-10, anamnesis, examen físico, planes y recetas).
- Numeración dinámica de páginas (Página X de Y) y pie legal de confidencialidad médica.
"""

import datetime
import io
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.prescription_pdf_service import get_vitarecord_logo_path


class NumberedCanvas(canvas.Canvas):
    """Canvas de ReportLab de dos pasadas para calcular dinámicamente el número total de páginas (Página X de Y)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748b"))

        # Línea separadora de pie de página
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(36, 32, letter[0] - 36, 32)

        # Texto del pie de página
        footer_text = "VitaRecord • Expediente Clínico Confidencial • Documento médico oficial de uso asistencial."
        page_str = f"Página {self._pageNumber} de {page_count}"

        self.drawString(36, 20, footer_text)
        self.drawRightString(letter[0] - 36, 20, page_str)
        self.restoreState()


def generate_medical_history_pdf(
    patient_data: dict,
    records: list[dict],
    doctor_emitter_name: str | None = None,
    doctor_emitter_specialty: str | None = None,
    clinic_name: str | None = None,
) -> bytes:
    """Construye el documento PDF de la historia médica completa y devuelve sus bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=46,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0f766e"),  # Teal-700
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#64748b"),
    )
    section_head_style = ParagraphStyle(
        "SectionHead",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0f766e"),
    )
    label_style = ParagraphStyle(
        "LabelStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#334155"),
    )
    value_style = ParagraphStyle(
        "ValueStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#0f172a"),
    )
    badge_dependent_style = ParagraphStyle(
        "BadgeDep",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#7c2d12"),
    )
    consultation_head_style = ParagraphStyle(
        "ConsultationHead",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
    )
    body_text_style = ParagraphStyle(
        "BodyTextClinical",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1e293b"),
    )
    diag_style = ParagraphStyle(
        "DiagStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#047857"),
    )

    elements = []

    # 1. Encabezado Institucional
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    logo_path = get_vitarecord_logo_path()
    logo_flowable = Image(logo_path, width=38, height=38) if logo_path else ""

    clinic_display = clinic_name or "Red Médica VitaRecord"
    emitter_display = f"Dr. {doctor_emitter_name}" if doctor_emitter_name else "Cuerpo Médico Asistencial"
    if doctor_emitter_specialty:
        emitter_display += f" ({doctor_emitter_specialty})"

    header_table_data = [
        [
            logo_flowable,
            Paragraph(f"<b>{clinic_display}</b><br/><font size=10 color='#0f766e'><b>HISTORIA CLÍNICA INTEGRAL</b></font>", title_style),
            Paragraph(
                f"<b>EMISIÓN:</b> {now_str}<br/><b>MÉDICO:</b> {emitter_display}<br/><b>EXPEDIENTE:</b> HC-{patient_data.get('id', '')[:8].upper()}",
                subtitle_style,
            ),
        ]
    ]
    header_table = Table(header_table_data, colWidths=[45, 310, 185])
    header_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ])
    )
    elements.append(header_table)
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f766e"), spaceAfter=8))

    # 2. Ficha Basal y Demográfica del Paciente
    is_dep = patient_data.get("is_dependent", False)
    rel = patient_data.get("relationship", "TITULAR")
    guardian = patient_data.get("guardian_name")

    tipo_paciente_text = "<b>PACIENTE TITULAR</b>"
    if is_dep:
        tipo_paciente_text = f"<b>FAMILIAR DEPENDIENTE</b> ({rel}) • <b>Titular:</b> {guardian or 'Responsable'}"

    # Cálculo de edad
    birth_date = patient_data.get("birth_date")
    age_str = "No registrada"
    if birth_date:
        if isinstance(birth_date, str):
            try:
                b_date = datetime.date.fromisoformat(birth_date)
            except Exception:
                b_date = None
        else:
            b_date = birth_date
        if b_date:
            today = datetime.date.today()
            calc_age = today.year - b_date.year - ((today.month, today.day) < (b_date.month, b_date.day))
            age_str = f"{calc_age} años ({b_date.strftime('%d/%m/%Y')})"

    pat_name = patient_data.get("full_name") or "Paciente"
    id_doc = patient_data.get("identification_number") or "No registrado"
    gender_str = patient_data.get("gender") or "No especificado"
    phone_str = patient_data.get("phone") or "No registrado"
    email_str = patient_data.get("email") or "No registrado"
    blood_str = patient_data.get("blood_type") or "Sin registrar"
    height_str = f"{patient_data.get('height_cm')} cm" if patient_data.get("height_cm") else "Sin registrar"
    allergies_str = patient_data.get("allergies") or "Ninguna conocida / No refiere"
    chronic_str = patient_data.get("chronic_conditions") or "Ninguno conocido / No refiere"

    patient_box_data = [
        [
            Paragraph("<b>PACIENTE:</b>", label_style),
            Paragraph(f"<b>{pat_name}</b>", value_style),
            Paragraph("<b>CONDICIÓN:</b>", label_style),
            Paragraph(tipo_paciente_text, value_style),
        ],
        [
            Paragraph("<b>IDENTIFICACIÓN:</b>", label_style),
            Paragraph(str(id_doc), value_style),
            Paragraph("<b>EDAD / NAC.:</b>", label_style),
            Paragraph(age_str, value_style),
        ],
        [
            Paragraph("<b>GÉNERO:</b>", label_style),
            Paragraph(str(gender_str).capitalize(), value_style),
            Paragraph("<b>GRUPO SANGUÍNEO:</b>", label_style),
            Paragraph(f"<b>{blood_str}</b>  •  <b>Talla:</b> {height_str}", value_style),
        ],
        [
            Paragraph("<b>CONTACTO:</b>", label_style),
            Paragraph(f"{phone_str} • {email_str}", value_style),
            Paragraph("<b>ALERGIAS:</b>", label_style),
            Paragraph(f"<font color='#dc2626'><b>{allergies_str}</b></font>", value_style),
        ],
        [
            Paragraph("<b>ANTECEDENTES:</b>", label_style),
            Paragraph(chronic_str, value_style),
            Paragraph("<b>CONSULTAS:</b>", label_style),
            Paragraph(f"<b>{len(records)} atención(es) registrada(s)</b>", value_style),
        ],
    ]

    pat_table = Table(patient_box_data, colWidths=[90, 180, 100, 170])
    pat_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    elements.append(pat_table)
    elements.append(Spacer(1, 12))

    # 3. Listado Cronológico de Consultas
    elements.append(Paragraph(f"<b>CRONOLOGÍA CLÍNICA Y EVOLUCIÓN MÉDICA ({len(records)} CONSULTAS)</b>", section_head_style))
    elements.append(Spacer(1, 4))

    if not records:
        empty_table = Table(
            [[Paragraph("<i>No se registran atenciones clínicas previas en este expediente.</i>", body_text_style)]],
            colWidths=[540],
        )
        empty_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("PADDING", (0, 0), (-1, -1), 12),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ])
        )
        elements.append(empty_table)
    else:
        # Iterar cada consulta
        for idx, rec in enumerate(records, 1):
            created_at = rec.get("created_at")
            if isinstance(created_at, datetime.datetime):
                date_str = created_at.strftime("%d/%m/%Y %H:%M")
            elif isinstance(created_at, str):
                try:
                    dt = datetime.datetime.fromisoformat(created_at)
                    date_str = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    date_str = created_at[:16]
            else:
                date_str = "Fecha no disponible"

            c_name = rec.get("clinic_name") or "Sede Principal"
            doc_name = rec.get("doctor_name") or "Médico Especialista"
            doc_spec = rec.get("doctor_specialty") or "Especialista"

            # Tira superior de la consulta
            consult_header_text = (
                f"<b>CONSULTA #{idx}</b> &nbsp;|&nbsp; <b>FECHA:</b> {date_str} &nbsp;|&nbsp; "
                f"<b>SEDE:</b> {c_name} &nbsp;|&nbsp; <b>MÉDICO:</b> Dr. {doc_name} ({doc_spec})"
            )
            head_table = Table([[Paragraph(consult_header_text, consultation_head_style)]], colWidths=[540])
            head_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0f766e")),
                    ("PADDING", (0, 0), (-1, -1), 4),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ])
            )

            # Contenido clínico de la consulta
            icd_code = rec.get("icd10_code")
            icd_desc = rec.get("icd10_description")
            diag_text = rec.get("diagnosis") or "Sin diagnóstico registrado"
            if icd_code:
                diag_full = f"<b>[{icd_code}] {icd_desc or ''}</b><br/>{diag_text}"
            else:
                diag_full = diag_text

            anamnesis_text = rec.get("anamnesis") or "No consignada"
            exam_text = rec.get("physical_exam") or "Sin hallazgos particulares registrados"
            plan_text = rec.get("plan") or "Continuar controles habituales"

            # Recetas asociadas
            prescriptions = rec.get("prescriptions") or []
            rx_rows = []
            if prescriptions:
                rx_summary = []
                for p in prescriptions:
                    items = p.get("items") or []
                    for itm in items:
                        med = itm.get("medication", "")
                        dose = itm.get("dosage", "")
                        freq = itm.get("frequency", "")
                        dur = itm.get("duration", "")
                        rx_summary.append(f"• <b>{med}</b> {dose} — {freq} ({dur})")
                if rx_summary:
                    rx_content = "<br/>".join(rx_summary)
                else:
                    rx_content = "Receta emitida sin medicamentos detallados."
            else:
                rx_content = "No se emitieron recetas farmacológicas en esta consulta."

            # Anexos asociados
            attachments = rec.get("attachments") or []
            if attachments:
                att_list = [f"• {a.get('file_name', 'Anexo')}" for a in attachments]
                att_content = "<br/>".join(att_list)
            else:
                att_content = "Sin anexos o estudios adjuntos."

            content_table_data = [
                [
                    Paragraph("<b>DIAGNÓSTICO:</b>", label_style),
                    Paragraph(diag_full, diag_style),
                ],
                [
                    Paragraph("<b>ANAMNESIS:</b>", label_style),
                    Paragraph(anamnesis_text.replace("\n", "<br/>"), body_text_style),
                ],
                [
                    Paragraph("<b>EXAMEN FÍSICO:</b>", label_style),
                    Paragraph(exam_text.replace("\n", "<br/>"), body_text_style),
                ],
                [
                    Paragraph("<b>PLAN / CONDUCTA:</b>", label_style),
                    Paragraph(plan_text.replace("\n", "<br/>"), body_text_style),
                ],
                [
                    Paragraph("<b>FARMACOTERAPIA:</b>", label_style),
                    Paragraph(rx_content, body_text_style),
                ],
                [
                    Paragraph("<b>ESTUDIOS / ANEXOS:</b>", label_style),
                    Paragraph(att_content, body_text_style),
                ],
            ]

            content_table = Table(content_table_data, colWidths=[110, 430])
            content_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ])
            )

            elements.append(head_table)
            elements.append(content_table)
            elements.append(Spacer(1, 8))

    # 4. Bloque de Firma y Validación
    elements.append(Spacer(1, 10))
    signature_table_data = [
        [
            Paragraph(
                "<b>AVISO DE CONFIDENCIALIDAD MÉDICA</b><br/>"
                "La información contenida en este expediente clínico está protegida por secreto profesional y normativas de confidencialidad de datos de salud. Prohibida su divulgación o copia no autorizada.",
                subtitle_style,
            ),
            Paragraph(
                "<br/><br/>________________________________________<br/>"
                f"<b>{emitter_display}</b><br/>"
                "Firma y Sello del Facultativo Emisor",
                ParagraphStyle("SignStyle", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=10, alignment=1),
            ),
        ]
    ]
    sign_table = Table(signature_table_data, colWidths=[320, 220])
    sign_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    elements.append(sign_table)

    # Construir documento con NumberedCanvas
    doc.build(elements, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()
