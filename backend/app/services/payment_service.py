import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import CashierDailySummary, PaymentRecordPublic, RecordPaymentRequest


class PaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.payments = PaymentRepository(db)
        self.appointments = AppointmentRepository(db)

    async def record_payment(
        self,
        clinic_id: str,
        appointment_id: str,
        payload: RecordPaymentRequest,
        current_user: User,
    ) -> PaymentRecordPublic:
        app = await self.appointments.get_by_id(appointment_id)
        if not app or app.clinic_id != clinic_id:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "Cita no encontrada en esta clínica.",
            )

        pay_record = await self.payments.get_by_appointment_id(appointment_id)
        if not pay_record:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "Registro contable de la cita no encontrado.",
            )

        if pay_record.status == "PAID":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Esta cita ya se encuentra pagada.",
            )
        if pay_record.status in ("EXEMPT", "VOID"):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"No se puede cobrar una cita en estado {pay_record.status}.",
            )

        updated = await self.payments.update_status(
            payment_id=pay_record.id,
            status="PAID",
            payment_method=payload.payment_method,
            reference=payload.reference,
            notes=payload.notes,
            recorded_by_user_id=current_user.id,
        )
        await self.db.commit()

        return PaymentRecordPublic(
            id=updated.id,
            appointment_id=updated.appointment_id,
            clinic_id=updated.clinic_id,
            amount=updated.amount,
            currency=updated.currency,
            status=updated.status,
            payment_method=updated.payment_method,
            reference=updated.reference,
            notes=updated.notes,
            paid_at=updated.paid_at,
            created_at=updated.created_at,
            patient_name=app.patient.full_name if app.patient else None,
            doctor_name=app.doctor.full_name if app.doctor else None,
        )

    async def get_daily_summary(
        self, clinic_id: str, target_date: datetime.date
    ) -> CashierDailySummary:
        summary_dict = await self.payments.get_daily_summary(clinic_id, target_date)
        return CashierDailySummary(**summary_dict)
