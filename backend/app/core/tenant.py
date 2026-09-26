"""Aislamiento multi-tenant a nivel de ORM (plan/plan.md seccion 2.B.1,
Principio Operativo 3).

Los modelos que heredan de `TenantScoped` (directamente o via
`TenantScopedMixin`) quedan sujetos a un filtro automatico
`WHERE clinic_id = :current_clinic_id` inyectado por el listener
`do_orm_execute`, salvo para roles globales (SUPERADMIN, MODERATOR,
COMPLIANCE_REVIEWER), que no operan sobre una sola clinica.

El contexto (clinic_id, role) se establece por cada peticion HTTP en
`app.api.deps.get_current_user`, que VALIDA la cabecera X-Clinic-ID contra
la clinica del usuario (personal de sede) o contra sus afiliaciones activas
(medicos). Nunca se confia en la cabecera enviada por el cliente sin validar.

Consultas que por diseno deben cruzar clinicas (p. ej. comprobar que un
medico no tenga una cita solapada en OTRA clinica, plan 2.B.4 Regla 1) deben
marcarse explicitamente con `.execution_options(tenant_bypass=True)` o con
el helper `cross_tenant(stmt)`. Toda marca de bypass debe estar justificada
en un comentario junto a la consulta.
"""

from contextvars import ContextVar

from sqlalchemy import ForeignKey, String, event
from sqlalchemy.orm import Mapped, Session, mapped_column, with_loader_criteria
from sqlalchemy.orm.session import ORMExecuteState

GLOBAL_ROLES = ("SUPERADMIN", "MODERATOR", "COMPLIANCE_REVIEWER")

# Roles cuyo tenant es SIEMPRE su propia clinica (user.clinic_id); el filtro
# se aplica aunque el cliente no envie la cabecera X-Clinic-ID.
CLINIC_BOUND_ROLES = ("CLINIC_ADMIN", "RECEPTIONIST")

TENANT_BYPASS_OPTION = "tenant_bypass"

current_clinic_id: ContextVar[str | None] = ContextVar("current_clinic_id", default=None)
current_user_role: ContextVar[str | None] = ContextVar("current_user_role", default=None)


def set_tenant_context(clinic_id: str | None, role: str | None) -> None:
    current_clinic_id.set(clinic_id)
    current_user_role.set(role)


def reset_tenant_context() -> None:
    current_clinic_id.set(None)
    current_user_role.set(None)


def cross_tenant(stmt):
    """Marca una consulta como inter-clinica a proposito (ver docstring del modulo)."""
    return stmt.execution_options(**{TENANT_BYPASS_OPTION: True})


class TenantScoped:
    """Marcador (sin columnas) para modelos cuyo `clinic_id` ya esta declarado
    en el propio modelo pero que deben aislarse por tenant."""


class TenantScopedMixin(TenantScoped):
    """Mixin para toda tabla transaccional/clinica que debe aislarse por
    clinic_id (medical_records, prescriptions, payment_records, clinic_rooms,
    appointments, etc. — plan/plan.md seccion 2.B.1)."""

    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), nullable=False, index=True)


def _tenant_filter(execute_state: ORMExecuteState) -> None:
    if not execute_state.is_select:
        return
    if execute_state.execution_options.get(TENANT_BYPASS_OPTION):
        return
    role = current_user_role.get()
    if role in GLOBAL_ROLES:
        return
    clinic_id = current_clinic_id.get()
    if clinic_id is None:
        return
    mapper = execute_state.bind_mapper
    registry = mapper.registry if mapper is not None else None
    if registry is None:
        return
    execute_state.statement = execute_state.statement.options(
        *(
            with_loader_criteria(
                cls,
                lambda cls: cls.clinic_id == clinic_id,
                include_aliases=True,
            )
            for cls in _tenant_scoped_classes(registry)
        )
    )


_scoped_cache: dict[int, tuple[type, ...]] = {}


def _tenant_scoped_classes(registry) -> tuple[type, ...]:
    """Clases mapeadas concretas que heredan de TenantScoped.

    `with_loader_criteria` necesita clases con el atributo `clinic_id` real
    (un marcador sin columnas no sirve), asi que se registra un criterio por
    cada modelo aislado.
    """
    key = id(registry)
    cached = _scoped_cache.get(key)
    if cached is None or len(cached) == 0:
        cached = tuple(
            m.class_ for m in registry.mappers if issubclass(m.class_, TenantScoped)
        )
        _scoped_cache[key] = cached
    return cached


# Se registra una unica vez, al importar este modulo (desde app.main).
event.listen(Session, "do_orm_execute", _tenant_filter)
