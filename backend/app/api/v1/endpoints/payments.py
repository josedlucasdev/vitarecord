import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.acl import Permission
from app.core.database import get_db
from app.models.user import User
from app.schemas.payment import CashierDailySummary, PaymentRecordPublic, RecordPaymentRequest
from app.services.payment_service import PaymentService

router = APIRouter()


@router.post(
    "/clinics/{clinic_id}/payments/{appointment_id}/record",
    response_model=PaymentRecordPublic,
)
async def record_payment(
    clinic_id: str,
    appointment_id: str,
    payload: RecordPaymentRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.PAYMENTS_RECORD))],
):
    """Registra el cobro manual efectuado en recepción (efectivo, tarjeta, transferencia, etc.)."""
    service = PaymentService(db)
    return await service.record_payment(clinic_id, appointment_id, payload, current_user)


@router.get(
    "/clinics/{clinic_id}/cashier/daily-summary",
    response_model=CashierDailySummary,
)
async def get_daily_cashier_summary(
    clinic_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.PAYMENTS_VIEW_CASHIER))],
    target_date: Annotated[datetime.date | None, Query(alias="date")] = None,
):
    """Calcula el cuadre diario de caja por sede, totalizando los cobros e ignorando citas canceladas/exentas."""
    service = PaymentService(db)
    date_to_query = target_date or datetime.date.today()
    return await service.get_daily_summary(clinic_id, date_to_query)
