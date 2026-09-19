import datetime
from decimal import Decimal
import io
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.appointment import Appointment
from app.models.clinic import Clinic
from app.models.payment_record import PaymentRecord


class AccountingExportService:
    """Servicio de generación y exportación de Libros y Reportes Contables en Excel

    Adaptado para la normativa tributaria y contable de Venezuela (SENIAT / Art. 18 Ley de IVA).
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_accounting_excel(
        self,
        clinic_id: str,
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
        status_filter: str | None = None,
        bcv_rate: Decimal | None = None,
    ) -> tuple[bytes, str]:
        # 1. Obtener clínica
        clinic = await self.db.get(Clinic, clinic_id)
        clinic_name = clinic.name if clinic else "Clínica ÍntimaSalud"
        clinic_address = clinic.address if clinic and clinic.address else "Venezuela"
        clinic_phone = clinic.phone if clinic and clinic.phone else "N/A"
        clinic_rif = "J-50189234-1"  # RIF institucional

        rate = bcv_rate if (bcv_rate and bcv_rate > 0) else Decimal("65.00")

        # 2. Consultar registros de pago y citas asociadas
        stmt = (
            select(PaymentRecord)
            .outerjoin(Appointment, PaymentRecord.appointment_id == Appointment.id)
            .options(
                selectinload(PaymentRecord.appointment).selectinload(Appointment.patient),
                selectinload(PaymentRecord.appointment).selectinload(Appointment.doctor),
                selectinload(PaymentRecord.appointment).selectinload(Appointment.room),
                selectinload(PaymentRecord.recorded_by),
            )
            .where(PaymentRecord.clinic_id == clinic_id)
            .order_by(PaymentRecord.paid_at.desc(), PaymentRecord.created_at.desc())
        )

        if status_filter and status_filter.upper() != "ALL":
            stmt = stmt.where(PaymentRecord.status == status_filter.upper())

        if start_date:
            s_dt = datetime.datetime.combine(start_date, datetime.time.min)
            stmt = stmt.where(
                or_(
                    PaymentRecord.paid_at >= s_dt,
                    and_(PaymentRecord.paid_at.is_(None), PaymentRecord.created_at >= s_dt),
                )
            )

        if end_date:
            e_dt = datetime.datetime.combine(end_date, datetime.time.max)
            stmt = stmt.where(
                or_(
                    PaymentRecord.paid_at <= e_dt,
                    and_(PaymentRecord.paid_at.is_(None), PaymentRecord.created_at <= e_dt),
                )
            )

        res = await self.db.execute(stmt)
        records = list(res.scalars().all())

        # 3. Construir Libro Excel con openpyxl
        wb = openpyxl.Workbook()

        # Estilos reutilizables
        font_title = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
        font_sub = Font(name="Calibri", size=10, italic=True, color="E0F2FE")
        font_meta = Font(name="Calibri", size=9, bold=True, color="334155")
        font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        font_data = Font(name="Calibri", size=9, color="0F172A")
        font_total = Font(name="Calibri", size=10, bold=True, color="0F172A")
        font_legal = Font(name="Calibri", size=8, italic=True, color="64748B")

        fill_banner = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")  # Teal 700
        fill_header = PatternFill(start_color="115E59", end_color="115E59", fill_type="solid")  # Teal 800
        fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        fill_total = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

        thin_side = Side(border_style="thin", color="CBD5E1")
        double_side = Side(border_style="double", color="334155")
        border_cell = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
        border_total = Border(left=thin_side, right=thin_side, top=thin_side, bottom=double_side)

        align_left = Alignment(horizontal="left", vertical="center")
        align_center = Alignment(horizontal="center", vertical="center")
        align_right = Alignment(horizontal="right", vertical="center")

        # ==========================================================
        # PESTAÑA 1: LIBRO DE INGRESOS Y FACTURACIÓN MÉDICA
        # ==========================================================
        ws1 = wb.active
        ws1.title = "Libro de Ingresos y Cobros"
        ws1.views.sheetView[0].showGridLines = True

        # Metadatos del encabezado
        periodo_txt = f"{start_date.strftime('%d/%m/%Y') if start_date else 'Inicio Histórico'} al {end_date.strftime('%d/%m/%Y') if end_date else 'Cierre Actual'}"
        emision_txt = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        ws1.merge_cells("A1:W1")
        ws1["A1"] = f"{clinic_name.upper()} — RIF: {clinic_rif}"
        ws1["A1"].font = font_title
        ws1["A1"].fill = fill_banner
        ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

        ws1.merge_cells("A2:W2")
        ws1["A2"] = "LIBRO AUXILIAR CONTABLE DE INGRESOS Y CAJA (SERVICIOS MÉDICO-ASISTENCIALES)"
        ws1["A2"].font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        ws1["A2"].fill = fill_banner
        ws1["A2"].alignment = Alignment(horizontal="center", vertical="center")

        ws1.merge_cells("A3:W3")
        ws1["A3"] = f"Dirección: {clinic_address} | Teléfono: {clinic_phone} | Moneda Base: USD | Tasa Ref. BCV: Bs. {rate:,.2f} por USD"
        ws1["A3"].font = font_sub
        ws1["A3"].fill = fill_banner
        ws1["A3"].alignment = Alignment(horizontal="center", vertical="center")

        ws1.merge_cells("A4:L4")
        ws1["A4"] = f"Período de Liquidación: {periodo_txt}"
        ws1["A4"].font = font_meta
        ws1["A4"].alignment = align_left

        ws1.merge_cells("M4:W4")
        ws1["M4"] = f"Fecha y Hora de Emisión: {emision_txt} | Total Registros: {len(records)}"
        ws1["M4"].font = font_meta
        ws1["M4"].alignment = align_right

        # Altura de filas cabecera
        ws1.row_dimensions[1].height = 24
        ws1.row_dimensions[2].height = 20
        ws1.row_dimensions[3].height = 18
        ws1.row_dimensions[4].height = 18
        ws1.row_dimensions[5].height = 6

        # Fila 6: Encabezados de Columna
        headers = [
            "N°",
            "Fecha Operación",
            "Hora",
            "N° Comprobante",
            "Cédula / RIF",
            "Nombre del Paciente",
            "Teléfono",
            "Médico Tratante",
            "Especialidad",
            "Concepto / Motivo",
            "Estado",
            "Condición IVA",
            "Método de Pago",
            "N° Referencia",
            "Moneda",
            "Monto USD",
            "Monto Exento USD",
            "Base Imponible",
            "IVA Débito (0%)",
            "Tasa BCV (Bs.)",
            "Monto Total (VES)",
            "Cajero / Operador",
            "Observaciones",
        ]

        header_row = 6
        ws1.row_dimensions[header_row].height = 26

        for col_idx, h_text in enumerate(headers, 1):
            cell = ws1.cell(row=header_row, column=col_idx, value=h_text)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = align_center
            cell.border = border_cell

        # Filas de Datos
        current_row = 7
        data_start_row = 7

        by_method_stats: dict[str, dict[str, Any]] = {}
        by_doctor_stats: dict[str, dict[str, Any]] = {}

        for idx, rec in enumerate(records, 1):
            op_dt = rec.paid_at or rec.created_at
            fecha_str = op_dt.strftime("%d/%m/%Y") if op_dt else "N/A"
            hora_str = op_dt.strftime("%H:%M") if op_dt else "N/A"

            app = rec.appointment
            patient_name = app.patient.full_name if (app and app.patient and app.patient.full_name) else "Paciente General"
            patient_phone = app.patient.phone if (app and app.patient and app.patient.phone) else "N/A"
            patient_doc = "S/D"
            if app and app.intake_data and isinstance(app.intake_data, dict):
                patient_doc = app.intake_data.get("id_document") or "S/D"

            doc_name = app.doctor.full_name if (app and app.doctor and app.doctor.full_name) else "Médico de Guardia"
            doc_spec = app.doctor.specialty if (app and app.doctor and app.doctor.specialty) else "Medicina General"
            reason = app.reason if (app and app.reason) else "Consulta Médica Especializada"
            cajero = rec.recorded_by.full_name if (rec.recorded_by and rec.recorded_by.full_name) else "Recepción"

            amount_usd = float(rec.amount)
            method = rec.payment_method or "OTRO"
            ref_num = rec.reference or "S/R"
            notes = rec.notes or ""

            # Acumular para pestaña de resumen
            if rec.status == "PAID":
                if method not in by_method_stats:
                    by_method_stats[method] = {"count": 0, "usd": Decimal("0.00")}
                by_method_stats[method]["count"] += 1
                by_method_stats[method]["usd"] += rec.amount

                if doc_name not in by_doctor_stats:
                    by_doctor_stats[doc_name] = {"specialty": doc_spec, "count": 0, "usd": Decimal("0.00")}
                by_doctor_stats[doc_name]["count"] += 1
                by_doctor_stats[doc_name]["usd"] += rec.amount

            # Escribir celdas
            row_fill = fill_zebra if idx % 2 == 0 else PatternFill(fill_type=None)

            c1 = ws1.cell(row=current_row, column=1, value=idx)
            c2 = ws1.cell(row=current_row, column=2, value=fecha_str)
            c3 = ws1.cell(row=current_row, column=3, value=hora_str)
            c4 = ws1.cell(row=current_row, column=4, value=f"REC-{rec.id[:8].upper()}")
            c5 = ws1.cell(row=current_row, column=5, value=patient_doc)
            c6 = ws1.cell(row=current_row, column=6, value=patient_name)
            c7 = ws1.cell(row=current_row, column=7, value=patient_phone)
            c8 = ws1.cell(row=current_row, column=8, value=doc_name)
            c9 = ws1.cell(row=current_row, column=9, value=doc_spec)
            c10 = ws1.cell(row=current_row, column=10, value=reason)
            c11 = ws1.cell(row=current_row, column=11, value=rec.status)
            c12 = ws1.cell(row=current_row, column=12, value="EXENTO (Art. 18 L-IVA)")
            c13 = ws1.cell(row=current_row, column=13, value=method)
            c14 = ws1.cell(row=current_row, column=14, value=ref_num)
            c15 = ws1.cell(row=current_row, column=15, value=rec.currency or "USD")

            # Montos
            c16 = ws1.cell(row=current_row, column=16, value=amount_usd)
            c16.number_format = "$#,##0.00"

            c17 = ws1.cell(row=current_row, column=17, value=amount_usd)  # Exento
            c17.number_format = "$#,##0.00"

            c18 = ws1.cell(row=current_row, column=18, value=0.00)  # Base imponible
            c18.number_format = "$#,##0.00"

            c19 = ws1.cell(row=current_row, column=19, value=0.00)  # IVA 0
            c19.number_format = "$#,##0.00"

            c20 = ws1.cell(row=current_row, column=20, value=float(rate))
            c20.number_format = "#,##0.00"

            c21 = ws1.cell(row=current_row, column=21, value=f"=P{current_row}*T{current_row}")
            c21.number_format = 'Bs. #,##0.00'

            c22 = ws1.cell(row=current_row, column=22, value=cajero)
            c23 = ws1.cell(row=current_row, column=23, value=notes)

            # Formatear alineaciones y bordes
            for col_i in range(1, 24):
                cell_obj = ws1.cell(row=current_row, column=col_i)
                cell_obj.font = font_data
                cell_obj.border = border_cell
                if row_fill.fill_type:
                    cell_obj.fill = row_fill

                if col_i in (1, 2, 3, 4, 5, 11, 12, 13, 15):
                    cell_obj.alignment = align_center
                elif col_i in (16, 17, 18, 19, 20, 21):
                    cell_obj.alignment = align_right
                else:
                    cell_obj.alignment = align_left

            current_row += 1

        # Fila de Totales
        tot_row = current_row
        ws1.merge_cells(start_row=tot_row, start_column=1, end_row=tot_row, end_column=15)
        cell_tot_label = ws1.cell(row=tot_row, column=1, value="TOTALES GENERALES RECAUDADOS:")
        cell_tot_label.font = font_total
        cell_tot_label.alignment = Alignment(horizontal="right", vertical="center")
        cell_tot_label.fill = fill_total

        for col_j in range(1, 16):
            ws1.cell(row=tot_row, column=col_j).border = border_total
            ws1.cell(row=tot_row, column=col_j).fill = fill_total

        # Fórmulas de suma
        last_data_row = current_row - 1 if current_row > data_start_row else data_start_row
        for col_sum, f_fmt in [(16, "$#,##0.00"), (17, "$#,##0.00"), (18, "$#,##0.00"), (19, "$#,##0.00"), (21, 'Bs. #,##0.00')]:
            c_sum = ws1.cell(row=tot_row, column=col_sum)
            col_letter = get_column_letter(col_sum)
            if len(records) > 0:
                c_sum.value = f"=SUM({col_letter}{data_start_row}:{col_letter}{last_data_row})"
            else:
                c_sum.value = 0.00
            c_sum.font = font_total
            c_sum.fill = fill_total
            c_sum.alignment = align_right
            c_sum.border = border_total
            c_sum.number_format = f_fmt

        ws1.cell(row=tot_row, column=20).border = border_total
        ws1.cell(row=tot_row, column=20).fill = fill_total
        ws1.cell(row=tot_row, column=22).border = border_total
        ws1.cell(row=tot_row, column=22).fill = fill_total
        ws1.cell(row=tot_row, column=23).border = border_total
        ws1.cell(row=tot_row, column=23).fill = fill_total

        # Nota al pie
        legal_row = tot_row + 2
        ws1.merge_cells(start_row=legal_row, start_column=1, end_row=legal_row, end_column=23)
        ws1.cell(
            row=legal_row,
            column=1,
            value="* NOTA TRIBUTARIA VENEZUELA: Los servicios médico-asistenciales prestados por clínicas y centros de salud se encuentran EXENTOS del Impuesto al Valor Agregado (IVA) según el Artículo 18, Numeral 4 de la Ley de IVA vigente (G.O. 6.507 Extraordinario).",
        ).font = font_legal

        # Congelar paneles bajo la cabecera
        ws1.freeze_panes = "A7"

        # Autoajustar ancho de columnas
        for col in ws1.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for c in col:
                if c.row > 4 and c.value:
                    val_str = str(c.value)
                    if not val_str.startswith("="):
                        max_len = max(max_len, len(val_str))
            ws1.column_dimensions[col_letter].width = max(max_len + 3, 12)

        # ==========================================================
        # PESTAÑA 2: RESUMEN CONTABLE Y DESGLOSE FISCAL
        # ==========================================================
        ws2 = wb.create_sheet(title="Resumen Contable y Métodos")
        ws2.views.sheetView[0].showGridLines = True

        ws2.merge_cells("A1:G1")
        ws2["A1"] = f"{clinic_name.upper()} — RESUMEN CONTABLE DE RECAUDACIÓN"
        ws2["A1"].font = font_title
        ws2["A1"].fill = fill_banner
        ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws2.row_dimensions[1].height = 24

        # Tabla 1: Desglose por Método de Pago
        ws2.cell(row=3, column=1, value="1. DESGLOSE POR MÉTODO DE PAGO").font = Font(name="Calibri", size=11, bold=True, color="0F766E")
        r_headers = ["Método de Pago", "Cant. Operaciones", "Total Recaudado (USD)", "Tasa Ref. BCV", "Total Equivalente (VES)", "% Participación"]
        for c_idx, h_t in enumerate(r_headers, 1):
            cl = ws2.cell(row=4, column=c_idx, value=h_t)
            cl.font = font_header
            cl.fill = fill_header
            cl.alignment = align_center
            cl.border = border_cell

        tot_usd_all = sum((v["usd"] for v in by_method_stats.values()), Decimal("0.00"))
        res_row = 5
        for m_name, m_data in sorted(by_method_stats.items(), key=lambda x: x[1]["usd"], reverse=True):
            pct = (float(m_data["usd"] / tot_usd_all) * 100.0) if tot_usd_all > 0 else 0.0

            ws2.cell(row=res_row, column=1, value=m_name).alignment = align_left
            ws2.cell(row=res_row, column=2, value=m_data["count"]).alignment = align_center
            c_u = ws2.cell(row=res_row, column=3, value=float(m_data["usd"]))
            c_u.number_format = "$#,##0.00"
            c_u.alignment = align_right

            c_t = ws2.cell(row=res_row, column=4, value=float(rate))
            c_t.number_format = "#,##0.00"
            c_t.alignment = align_right

            c_v = ws2.cell(row=res_row, column=5, value=f"=C{res_row}*D{res_row}")
            c_v.number_format = 'Bs. #,##0.00'
            c_v.alignment = align_right

            c_p = ws2.cell(row=res_row, column=6, value=f"{pct:.1f}%")
            c_p.alignment = align_center

            for c_i in range(1, 7):
                ws2.cell(row=res_row, column=c_i).border = border_cell
                ws2.cell(row=res_row, column=c_i).font = font_data

            res_row += 1

        # Fila Total Métodos
        ws2.merge_cells(start_row=res_row, start_column=1, end_row=res_row, end_column=2)
        tot_lbl = ws2.cell(row=res_row, column=1, value="TOTAL POR MÉTODOS:")
        tot_lbl.font = font_total
        tot_lbl.alignment = align_right
        tot_lbl.fill = fill_total

        c_tu = ws2.cell(row=res_row, column=3, value=float(tot_usd_all))
        c_tu.font = font_total
        c_tu.fill = fill_total
        c_tu.number_format = "$#,##0.00"
        c_tu.alignment = align_right

        ws2.cell(row=res_row, column=4).fill = fill_total
        c_tv = ws2.cell(row=res_row, column=5, value=f"=C{res_row}*D4")  # formula or empty
        c_tv.value = float(tot_usd_all * rate)
        c_tv.font = font_total
        c_tv.fill = fill_total
        c_tv.number_format = 'Bs. #,##0.00'
        c_tv.alignment = align_right

        ws2.cell(row=res_row, column=6, value="100.0%").font = font_total
        ws2.cell(row=res_row, column=6).alignment = align_center
        ws2.cell(row=res_row, column=6).fill = fill_total

        for c_k in range(1, 7):
            ws2.cell(row=res_row, column=c_k).border = border_total

        # Tabla 2: Rendimiento por Médico (Para Honorarios y Retenciones)
        doc_start_row = res_row + 3
        ws2.cell(row=doc_start_row, column=1, value="2. REPORTE POR MÉDICO ESPECIALISTA (BASE DE HONORARIOS)").font = Font(name="Calibri", size=11, bold=True, color="0F766E")

        d_headers = ["Médico Especialista", "Especialidad", "N° Consultas Atendidas", "Total Facturado (USD)", "Total Facturado (VES)"]
        for c_idx, h_t in enumerate(d_headers, 1):
            cl = ws2.cell(row=doc_start_row + 1, column=c_idx, value=h_t)
            cl.font = font_header
            cl.fill = fill_header
            cl.alignment = align_center
            cl.border = border_cell

        d_row = doc_start_row + 2
        for d_name, d_info in sorted(by_doctor_stats.items(), key=lambda x: x[1]["usd"], reverse=True):
            ws2.cell(row=d_row, column=1, value=d_name).alignment = align_left
            ws2.cell(row=d_row, column=2, value=d_info["specialty"]).alignment = align_left
            ws2.cell(row=d_row, column=3, value=d_info["count"]).alignment = align_center

            c_du = ws2.cell(row=d_row, column=4, value=float(d_info["usd"]))
            c_du.number_format = "$#,##0.00"
            c_du.alignment = align_right

            c_dv = ws2.cell(row=d_row, column=5, value=float(d_info["usd"] * rate))
            c_dv.number_format = 'Bs. #,##0.00'
            c_dv.alignment = align_right

            for c_x in range(1, 6):
                ws2.cell(row=d_row, column=c_x).border = border_cell
                ws2.cell(row=d_row, column=c_x).font = font_data

            d_row += 1

        # Autoajuste de columnas pestaña 2
        for col in ws2.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for c in col:
                if c.value:
                    max_len = max(max_len, len(str(c.value)))
            ws2.column_dimensions[col_letter].width = max(max_len + 3, 16)

        # 4. Guardar archivo en memoria BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"Libro_Contable_{clinic.slug if clinic else 'Clinica'}_{datetime.date.today().isoformat()}.xlsx"
        return output.getvalue(), filename
