from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.affiliation import DoctorClinicAffiliation
from app.models.user import User
from app.schemas.analytics import ClinicAnalyticsResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/clinics/{clinic_id}/analytics", response_model=ClinicAnalyticsResponse)
async def get_clinic_analytics(
    clinic_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: Annotated[int, Query(ge=0, le=365, description="Filtro temporal en días (0 para histórico)")] = 30,
):
    """Obtiene KPIs, tendencias, distribución de estados, finanzas y demanda de una sede clínica.

    Aislamiento multi-tenant:
    - SUPERADMIN puede consultar las analíticas de cualquier sede.
    - CLINIC_ADMIN y RECEPTIONIST solo pueden consultar las analíticas de su propia clínica.
    - DOCTOR puede consultar analíticas de la sede donde trabaja o está afiliado.
    """
    # 1. Validación de Aislamiento de Tenant
    if current_user.role != "SUPERADMIN":
        allowed = False
        if current_user.clinic_id == clinic_id:
            allowed = True
        elif current_user.role == "DOCTOR":
            aff = await db.scalar(
                select(DoctorClinicAffiliation).where(
                    DoctorClinicAffiliation.doctor_id == current_user.id,
                    DoctorClinicAffiliation.clinic_id == clinic_id,
                    DoctorClinicAffiliation.status == "ACTIVE",
                )
            )
            if aff:
                allowed = True

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes autorización para consultar las métricas de esta sede clínica.",
            )

    # 2. Ejecución del servicio
    service = AnalyticsService(db)
    try:
        return await service.get_clinic_analytics(clinic_id=clinic_id, days=days)
    except ValueError as err:
        if str(err) == "Clínica no encontrada":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(err),
            )
        raise
