"""Endpoints de consulta de pistas de auditoria inmutable (plan/plan.md 2.B.8 y 2.B.11).

Permite a los roles de cumplimiento (COMPLIANCE_REVIEWER, SUPERADMIN) consultar
y auditar el rastro de accesos a PHI, cambios de configuración y acciones sensibles.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.acl import Permission
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogPaginationResponse, AuditLogPublic

router = APIRouter()


@router.get(
    "/logs",
    response_model=AuditLogPaginationResponse,
    summary="Consultar pistas de auditoría inmutables (Compliance / SuperAdmin)",
)
async def list_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.COMPLIANCE_AUDIT_READ))],
    clinic_id: str | None = Query(None, description="Filtrar por sede clínica"),
    user_id: str | None = Query(None, description="Filtrar por usuario autor"),
    action: str | None = Query(None, description="Filtrar por acción (READ, CREATE, UPDATE, etc.)"),
    entity_type: str | None = Query(None, description="Filtrar por tipo de entidad (medical_record, etc.)"),
    entity_id: str | None = Query(None, description="Filtrar por ID de entidad"),
    from_date: datetime | None = Query(None, description="Fecha de inicio (UTC)"),
    to_date: datetime | None = Query(None, description="Fecha de fin (UTC)"),
    limit: int = Query(50, ge=1, le=200, description="Cantidad de registros"),
    offset: int = Query(0, ge=0, description="Desplazamiento inicial"),
):
    stmt = select(AuditLog)
    count_stmt = select(func.count(AuditLog.id))

    filters = []
    if clinic_id:
        filters.append(AuditLog.clinic_id == clinic_id)
    if user_id:
        filters.append(AuditLog.user_id == user_id)
    if action:
        filters.append(AuditLog.action == action)
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)
    if entity_id:
        filters.append(AuditLog.entity_id == entity_id)
    if from_date:
        filters.append(AuditLog.created_at >= from_date)
    if to_date:
        filters.append(AuditLog.created_at <= to_date)

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    res = await db.execute(stmt)
    items = list(res.scalars().all())

    return AuditLogPaginationResponse(
        items=[AuditLogPublic.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )
