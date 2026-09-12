"""Aislamiento multi-tenant a nivel de ORM (plan/plan.md seccion 2.B.1,
Principio Operativo 3).

Los modelos que heredan de `TenantScopedMixin` quedan sujetos a un filtro
automatico `WHERE clinic_id = :current_clinic_id` inyectado por el listener
`do_orm_execute`, salvo para roles globales (SUPERADMIN, MODERATOR,
COMPLIANCE_REVIEWER), que no operan sobre una sola clinica.

El contexto (clinic_id, role) se establece por cada peticion HTTP en el
middleware `TenantContextMiddleware` (ver app/main.py) a partir del JWT
y/o la cabecera X-Clinic-ID.
"""

from contextvars import ContextVar

from sqlalchemy import ForeignKey, String, event
from sqlalchemy.orm import Mapped, Session, mapped_column, with_loader_criteria
from sqlalchemy.orm.session import ORMExecuteState

GLOBAL_ROLES = ("SUPERADMIN", "MODERATOR", "COMPLIANCE_REVIEWER")

current_clinic_id: ContextVar[str | None] = ContextVar("current_clinic_id", default=None)
current_user_role: ContextVar[str | None] = ContextVar("current_user_role", default=None)


def set_tenant_context(clinic_id: str | None, role: str | None) -> None:
    current_clinic_id.set(clinic_id)
    current_user_role.set(role)


def reset_tenant_context() -> None:
    current_clinic_id.set(None)
    current_user_role.set(None)


class TenantScopedMixin:
    """Mixin para toda tabla transaccional/clinica que debe aislarse por
    clinic_id (medical_records, prescriptions, payment_records, clinic_rooms,
    appointments, etc. — plan/plan.md seccion 2.B.1)."""

    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), nullable=False, index=True)


def _tenant_filter(execute_state: ORMExecuteState) -> None:
    if not execute_state.is_select:
        return
    role = current_user_role.get()
    if role in GLOBAL_ROLES:
        return
    clinic_id = current_clinic_id.get()
    if clinic_id is None:
        return
    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            TenantScopedMixin,
            lambda cls: cls.clinic_id == clinic_id,
            include_aliases=True,
        )
    )


# Se registra una unica vez, al importar este modulo (desde app.main).
event.listen(Session, "do_orm_execute", _tenant_filter)
