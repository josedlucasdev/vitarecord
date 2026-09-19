import datetime
from decimal import Decimal
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.payment_record import PaymentRecord


class PaymentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, payment: PaymentRecord) -> PaymentRecord:
        self.db.add(payment)
        await self.db.flush()
        return payment

    async def get_by_appointment_id(self, appointment_id: str) -> PaymentRecord | None:
        stmt = select(PaymentRecord).where(PaymentRecord.appointment_id == appointment_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def update_status(
        self,
        payment_id: str,
        status: str,
        payment_method: str | None = None,
        reference: str | None = None,
        notes: str | None = None,
        recorded_by_user_id: str | None = None,
        amount: Decimal | None = None,
    ) -> PaymentRecord | None:
        stmt = select(PaymentRecord).where(PaymentRecord.id == payment_id)
        res = await self.db.execute(stmt)
        record = res.scalar_one_or_none()
        if record:
            record.status = status
            if amount is not None:
                record.amount = amount
            if payment_method:
                record.payment_method = payment_method
            if reference:
                record.reference = reference
            if notes:
                record.notes = notes
            if recorded_by_user_id:
                record.recorded_by_user_id = recorded_by_user_id
            if status == "PAID" and not record.paid_at:
                record.paid_at = datetime.datetime.now(datetime.timezone.utc)
            await self.db.flush()
        return record

    async def get_daily_summary(self, clinic_id: str, target_date: datetime.date) -> dict:
        """Cuadre de caja diario excluyendo pagos EXEMPT y VOID de los totales recaudados."""
        start_of_day = datetime.datetime.combine(target_date, datetime.time.min)
        end_of_day = datetime.datetime.combine(target_date, datetime.time.max)

        stmt = (
            select(PaymentRecord)
            .outerjoin(Appointment, PaymentRecord.appointment_id == Appointment.id)
            .where(
                PaymentRecord.clinic_id == clinic_id,
                or_(
                    and_(PaymentRecord.paid_at >= start_of_day, PaymentRecord.paid_at <= end_of_day),
                    and_(PaymentRecord.paid_at.is_(None), PaymentRecord.created_at >= start_of_day, PaymentRecord.created_at <= end_of_day),
                    and_(Appointment.start_time >= start_of_day, Appointment.start_time <= end_of_day),
                ),
            )
        )
        res = await self.db.execute(stmt)
        records = list(res.scalars().all())

        total_collected = Decimal("0.00")
        by_method: dict[str, Decimal] = {
            "CASH": Decimal("0.00"),
            "CARD": Decimal("0.00"),
            "TRANSFER": Decimal("0.00"),
            "PAGO_MOVIL": Decimal("0.00"),
            "ZELLE": Decimal("0.00"),
            "OTHER": Decimal("0.00"),
        }
        counts = {"PAID": 0, "EXEMPT": 0, "VOID": 0, "UNPAID": 0}

        for rec in records:
            if rec.status in counts:
                counts[rec.status] += 1

            # Solo suma al total recaudado si el estado es PAID
            if rec.status == "PAID":
                total_collected += rec.amount
                method = rec.payment_method or "OTHER"
                if method not in by_method:
                    by_method[method] = Decimal("0.00")
                by_method[method] += rec.amount

        return {
            "date": target_date,
            "clinic_id": clinic_id,
            "total_collected": total_collected,
            "currency": "USD",
            "by_method": by_method,
            "paid_count": counts["PAID"],
            "exempt_count": counts["EXEMPT"],
            "void_count": counts["VOID"],
            "unpaid_count": counts["UNPAID"],
        }
