import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
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


@router.get(
    "/clinics/{clinic_id}/cashier/export-accounting-excel",
)
async def export_accounting_excel(
    clinic_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.PAYMENTS_VIEW_CASHIER))],
    start_date: Annotated[datetime.date | None, Query(alias="start_date")] = None,
    end_date: Annotated[datetime.date | None, Query(alias="end_date")] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    bcv_rate: Annotated[Decimal | None, Query(alias="bcv_rate")] = None,
):
    """Genera y descarga el Libro / Reporte Contable de Ingresos en formato Excel (.xlsx).

    Especialmente estructurado con columnas y normativas para contadores en Venezuela:
    - Base imponible, exenciones de IVA (Art. 18 Ley IVA servicios médicos).
    - Desglose por método de pago (Efectivo, Tarjeta, Transferencia, Pago Móvil, Zelle).
    - Conversión multimoneda con Tasa Oficial BCV a Bolívares (VES).
    - Identificación fiscal del paciente (Cédula/RIF) y médico tratante.
    """
    if current_user.role != "SUPERADMIN" and current_user.clinic_id and current_user.clinic_id != clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes autorización para exportar los libros contables de esta sede clínica.",
        )

    from app.services.accounting_export_service import AccountingExportService

    service = AccountingExportService(db)
    excel_bytes, filename = await service.generate_accounting_excel(
        clinic_id=clinic_id,
        start_date=start_date,
        end_date=end_date,
        status_filter=status_filter,
        bcv_rate=bcv_rate,
    )

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )

