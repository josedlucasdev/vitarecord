import datetime
from decimal import Decimal
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.affiliation import DoctorClinicAffiliation
from app.models.appointment import Appointment
from app.models.clinic import Clinic, ClinicRoom
from app.models.payment_record import PaymentRecord
from app.models.user import User
from app.schemas.analytics import (
    ClinicAnalyticsResponse,
    ClinicKpis,
    DailyTrendItem,
    DoctorPerformanceItem,
    PaymentMethodItem,
    RoomUtilizationItem,
    SpecialtyItem,
    StatusDistributionItem,
    TodayAppointmentItem,
)

STATUS_LABELS = {
    "CONFIRMED": "Confirmadas",
    "COMPLETED": "Completadas",
    "PENDING_DOCTOR_APPROVAL": "Pendiente Aprobación Médico",
    "PENDING_PATIENT_ACCEPTANCE": "Pendiente Aceptación Paciente",
    "SCHEDULED": "Agendadas",
    "CHECKED_IN": "En Sala de Espera",
    "IN_CONSULTATION": "En Consulta",
    "CANCELLED_BY_PATIENT": "Cancelada por Paciente",
    "CANCELLED_BY_DOCTOR": "Cancelada por Médico",
    "CANCELLED_BY_CLINIC": "Cancelada por Clínica",
    "REJECTED_BY_PATIENT": "Rechazada por Paciente",
    "REJECTED_BY_DOCTOR": "Rechazada por Médico",
    "NO_SHOW": "No Asistió (No Show)",
    "RESCHEDULED": "Reagendada",
}

STATUS_COLORS = {
    "CONFIRMED": "#0d9488",
    "COMPLETED": "#10b981",
    "PENDING_DOCTOR_APPROVAL": "#f59e0b",
    "PENDING_PATIENT_ACCEPTANCE": "#3b82f6",
    "SCHEDULED": "#0284c7",
    "CHECKED_IN": "#6366f1",
    "IN_CONSULTATION": "#8b5cf6",
    "CANCELLED_BY_PATIENT": "#ef4444",
    "CANCELLED_BY_DOCTOR": "#dc2626",
    "CANCELLED_BY_CLINIC": "#b91c1c",
    "REJECTED_BY_PATIENT": "#f97316",
    "REJECTED_BY_DOCTOR": "#ea580c",
    "NO_SHOW": "#64748b",
    "RESCHEDULED": "#a855f7",
}

PAYMENT_METHOD_LABELS = {
    "CASH": "Efectivo",
    "CARD": "Tarjeta de Débito/Crédito",
    "PAGO_MOVIL": "Pago Móvil",
    "ZELLE": "Zelle",
    "TRANSFER": "Transferencia Bancaria",
}

PAYMENT_COLORS = {
    "CASH": "#10b981",
    "CARD": "#3b82f6",
    "PAGO_MOVIL": "#f59e0b",
    "ZELLE": "#8b5cf6",
    "TRANSFER": "#0d9488",
    "EXEMPT": "#94a3b8",
}


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_clinic_analytics(self, clinic_id: str, days: int = 30) -> ClinicAnalyticsResponse:
        clinic = await self.db.get(Clinic, clinic_id)
        if not clinic:
            raise ValueError("Clínica no encontrada")

        cutoff = None
        if days > 0:
            cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)

        # 1. KPIs de Citas
        appt_query = select(Appointment).where(Appointment.clinic_id == clinic_id)
        if cutoff:
            appt_query = appt_query.where(Appointment.start_time >= cutoff)

        appt_result = await self.db.execute(appt_query)
        all_appts = list(appt_result.scalars().all())

        total_appts = len(all_appts)
        completed_count = sum(1 for a in all_appts if a.status == "COMPLETED")
        confirmed_count = sum(1 for a in all_appts if a.status in ("CONFIRMED", "SCHEDULED", "CHECKED_IN", "IN_CONSULTATION"))
        pending_count = sum(1 for a in all_appts if a.status in ("PENDING_DOCTOR_APPROVAL", "PENDING_PATIENT_ACCEPTANCE"))
        cancelled_count = sum(1 for a in all_appts if "CANCELLED" in a.status or "REJECTED" in a.status or a.status == "NO_SHOW")

        effective_base = completed_count + confirmed_count + cancelled_count
        attendance_rate = round(((completed_count + confirmed_count) / effective_base * 100), 1) if effective_base > 0 else 100.0

        unique_patient_ids = {a.patient_id for a in all_appts if a.patient_id}
        unique_patients = len(unique_patient_ids)

        # 2. KPIs de Pagos / Ingresos
        pay_query = select(PaymentRecord).where(PaymentRecord.clinic_id == clinic_id)
        if cutoff:
            pay_query = pay_query.where(PaymentRecord.created_at >= cutoff)

        pay_result = await self.db.execute(pay_query)
        all_payments = list(pay_result.scalars().all())

        paid_payments = [p for p in all_payments if p.status == "PAID"]
        total_revenue = sum((p.amount for p in paid_payments), Decimal("0.00"))
        paid_count = len(paid_payments)

        # 3. Médicos Activos Afiliados
        doc_aff_stmt = select(func.count(DoctorClinicAffiliation.id)).where(
            DoctorClinicAffiliation.clinic_id == clinic_id,
            DoctorClinicAffiliation.status == "ACTIVE",
        )
        active_doctors = (await self.db.scalar(doc_aff_stmt)) or 0

        # Si no hay afiliaciones formales, contar médicos con clinic_id directo
        if active_doctors == 0:
            doc_stmt = select(func.count(User.id)).where(
                User.clinic_id == clinic_id,
                User.role == "DOCTOR",
                User.status == "ACTIVE",
            )
            active_doctors = (await self.db.scalar(doc_stmt)) or 0

        # 4. Salas Activas
        rooms_stmt = select(func.count(ClinicRoom.id)).where(
            ClinicRoom.clinic_id == clinic_id,
            ClinicRoom.is_active == True,
        )
        active_rooms = (await self.db.scalar(rooms_stmt)) or 0

        kpis = ClinicKpis(
            total_appointments=total_appts,
            completed_appointments=completed_count,
            confirmed_appointments=confirmed_count,
            pending_appointments=pending_count,
            cancelled_appointments=cancelled_count,
            attendance_rate_pct=attendance_rate,
            total_revenue=total_revenue,
            total_paid_count=paid_count,
            unique_patients=unique_patients,
            active_doctors=active_doctors,
            active_rooms=active_rooms,
        )

        # 5. Tendencia Diaria de Citas
        trend_map: dict[str, dict[str, int]] = {}
        for a in sorted(all_appts, key=lambda x: x.start_time):
            day_str = a.start_time.strftime("%d/%m")
            if day_str not in trend_map:
                trend_map[day_str] = {"total": 0, "confirmed": 0, "completed": 0, "cancelled": 0}
            trend_map[day_str]["total"] += 1
            if a.status in ("CONFIRMED", "SCHEDULED"):
                trend_map[day_str]["confirmed"] += 1
            elif a.status == "COMPLETED":
                trend_map[day_str]["completed"] += 1
            elif "CANCELLED" in a.status or "REJECTED" in a.status or a.status == "NO_SHOW":
                trend_map[day_str]["cancelled"] += 1

        trends = [
            DailyTrendItem(
                date=day_str,
                total=vals["total"],
                confirmed=vals["confirmed"],
                completed=vals["completed"],
                cancelled=vals["cancelled"],
            )
            for day_str, vals in list(trend_map.items())[-20:]
        ]

        # 6. Distribución de Estados
        status_counts: dict[str, int] = {}
        for a in all_appts:
            status_counts[a.status] = status_counts.get(a.status, 0) + 1

        status_distribution = []
        for st_key, cnt in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
            pct = round((cnt / total_appts * 100), 1) if total_appts > 0 else 0.0
            status_distribution.append(
                StatusDistributionItem(
                    status=st_key,
                    label=STATUS_LABELS.get(st_key, st_key),
                    count=cnt,
                    percentage=pct,
                    color=STATUS_COLORS.get(st_key, "#64748b"),
                )
            )

        # 7. Métodos de Pago
        method_sums: dict[str, dict] = {}
        for p in paid_payments:
            m = p.payment_method or "CASH"
            if m not in method_sums:
                method_sums[m] = {"amount": Decimal("0.00"), "count": 0}
            method_sums[m]["amount"] += p.amount
            method_sums[m]["count"] += 1

        payment_methods = []
        for m_key, data in method_sums.items():
            payment_methods.append(
                PaymentMethodItem(
                    method=m_key,
                    label=PAYMENT_METHOD_LABELS.get(m_key, m_key),
                    amount=data["amount"],
                    count=data["count"],
                    color=PAYMENT_COLORS.get(m_key, "#0d9488"),
                )
            )

        # 8. Demanda por Especialidad Médica y Top Médicos
        doc_ids = list({a.doctor_id for a in all_appts if a.doctor_id})
        doc_map: dict[str, User] = {}
        if doc_ids:
            docs_res = await self.db.execute(select(User).where(User.id.in_(doc_ids)))
            for d in docs_res.scalars().all():
                doc_map[d.id] = d

        specialty_counts: dict[str, int] = {}
        doctor_appts: dict[str, dict] = {}

        for a in all_appts:
            doc = doc_map.get(a.doctor_id)
            spec = (doc.specialty if doc and doc.specialty else "Medicina General")
            specialty_counts[spec] = specialty_counts.get(spec, 0) + 1

            if a.doctor_id:
                if a.doctor_id not in doctor_appts:
                    doctor_appts[a.doctor_id] = {
                        "name": doc.full_name if doc and doc.full_name else (doc.email if doc else "Dr. Especialista"),
                        "specialty": spec,
                        "total": 0,
                        "completed": 0,
                    }
                doctor_appts[a.doctor_id]["total"] += 1
                if a.status == "COMPLETED":
                    doctor_appts[a.doctor_id]["completed"] += 1

        specialties = [
            SpecialtyItem(specialty=sp, count=c)
            for sp, c in sorted(specialty_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        ]

        top_doctors = [
            DoctorPerformanceItem(
                doctor_id=d_id,
                doctor_name=info["name"],
                specialty=info["specialty"],
                appointments_count=info["total"],
                completed_count=info["completed"],
            )
            for d_id, info in sorted(doctor_appts.items(), key=lambda x: x[1]["total"], reverse=True)[:6]
        ]

        # 9. Ocupación de Salas
        room_ids = list({a.room_id for a in all_appts if a.room_id})
        room_map: dict[str, ClinicRoom] = {}
        if room_ids:
            r_res = await self.db.execute(select(ClinicRoom).where(ClinicRoom.id.in_(room_ids)))
            for r in r_res.scalars().all():
                room_map[r.id] = r

        room_counts: dict[str, int] = {}
        for a in all_appts:
            if a.room_id:
                room_counts[a.room_id] = room_counts.get(a.room_id, 0) + 1

        room_utilization = [
            RoomUtilizationItem(
                room_id=r_id,
                room_name=room_map[r_id].name if r_id in room_map else f"Consultorio {r_id[:6]}",
                appointments_count=cnt,
            )
            for r_id, cnt in sorted(room_counts.items(), key=lambda x: x[1], reverse=True)[:6]
        ]

        # 10. Próximas Citas / Citas Recientes
        recent_stmt = (
            select(Appointment)
            .options(
                selectinload(Appointment.doctor),
                selectinload(Appointment.patient),
                selectinload(Appointment.room),
                selectinload(Appointment.payment_record),
            )
            .where(Appointment.clinic_id == clinic_id)
            .order_by(Appointment.start_time.desc())
            .limit(10)
        )
        recent_res = await self.db.execute(recent_stmt)
        recent_appts = recent_res.scalars().all()

        today_appointments = []
        for appt in recent_appts:
            pat_name = "Paciente"
            if appt.patient:
                pat_name = appt.patient.full_name or appt.patient.email or "Paciente"
            doc_name = "Dr. Asignado"
            if appt.doctor:
                doc_name = appt.doctor.full_name or appt.doctor.email or "Dr. Asignado"
            doc_spec = appt.doctor.specialty if appt.doctor else None
            r_name = appt.room.name if appt.room else "Por asignar"
            pay_st = appt.payment_record.status if appt.payment_record else "UNPAID"
            pay_amt = appt.payment_record.amount if appt.payment_record else None

            today_appointments.append(
                TodayAppointmentItem(
                    id=appt.id,
                    start_time=appt.start_time.strftime("%d/%m/%Y %H:%M"),
                    patient_name=pat_name,
                    doctor_name=doc_name,
                    specialty=doc_spec,
                    room_name=r_name,
                    status=appt.status,
                    payment_status=pay_st,
                    amount=pay_amt,
                )
            )

        return ClinicAnalyticsResponse(
            clinic_id=clinic.id,
            clinic_name=clinic.name,
            period_days=days,
            kpis=kpis,
            trends=trends,
            status_distribution=status_distribution,
            payment_methods=payment_methods,
            specialties=specialties,
            top_doctors=top_doctors,
            room_utilization=room_utilization,
            today_appointments=today_appointments,
        )
