"""Sistema de Control de Acceso (ACL) y Permisos Atómicos (plan/plan.md seccion 2.B.0)."""

from enum import StrEnum


class Permission(StrEnum):
    TENANTS_MANAGE = "tenants:manage"
    TENANTS_READ = "tenants:read"
    COMPLIANCE_VERIFY_DOCTOR = "compliance:verify_doctor"
    COMPLIANCE_AUDIT_READ = "compliance:audit_read"
    ROOMS_MANAGE = "rooms:manage"
    ROOMS_READ = "rooms:read"
    DOCTORS_INVITE = "doctors:invite"
    DOCTORS_SCHEDULE_MANAGE = "doctors:schedule_manage"
    STAFF_MANAGE = "staff:manage"
    APPOINTMENTS_BOOK = "appointments:book"
    APPOINTMENTS_MANAGE = "appointments:manage"
    PAYMENTS_RECORD = "payments:record"
    PAYMENTS_VIEW_CASHIER = "payments:view_cashier"
    CLINICAL_RECORDS_READ = "clinical_records:read"
    CLINICAL_RECORDS_WRITE = "clinical_records:write"
    EMERGENCY_TRIGGER = "emergency:trigger"
    EMERGENCY_MONITOR = "emergency:monitor"
    EMERGENCY_RESPOND = "emergency:respond"


# Matriz determinista y configurable de Roles a Permisos
DEFAULT_ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "SUPERADMIN": {
        Permission.TENANTS_MANAGE,
        Permission.TENANTS_READ,
        Permission.COMPLIANCE_VERIFY_DOCTOR,
        Permission.COMPLIANCE_AUDIT_READ,
        Permission.ROOMS_MANAGE,
        Permission.ROOMS_READ,
        Permission.DOCTORS_INVITE,
        Permission.DOCTORS_SCHEDULE_MANAGE,
        Permission.STAFF_MANAGE,
        Permission.APPOINTMENTS_BOOK,
        Permission.APPOINTMENTS_MANAGE,
        Permission.PAYMENTS_RECORD,
        Permission.PAYMENTS_VIEW_CASHIER,
        Permission.EMERGENCY_TRIGGER,
        Permission.EMERGENCY_MONITOR,
        Permission.EMERGENCY_RESPOND,
    },
    "MODERATOR": {
        Permission.TENANTS_READ,
        Permission.COMPLIANCE_VERIFY_DOCTOR,
        Permission.COMPLIANCE_AUDIT_READ,
        Permission.ROOMS_READ,
        Permission.EMERGENCY_MONITOR,
        Permission.EMERGENCY_RESPOND,
    },
    "COMPLIANCE_REVIEWER": {
        Permission.TENANTS_READ,
        Permission.COMPLIANCE_VERIFY_DOCTOR,
        Permission.COMPLIANCE_AUDIT_READ,
        Permission.ROOMS_READ,
        Permission.EMERGENCY_MONITOR,
    },
    "CLINIC_ADMIN": {
        Permission.TENANTS_READ,
        Permission.ROOMS_MANAGE,
        Permission.ROOMS_READ,
        Permission.DOCTORS_INVITE,
        Permission.DOCTORS_SCHEDULE_MANAGE,
        Permission.STAFF_MANAGE,
        Permission.APPOINTMENTS_BOOK,
        Permission.APPOINTMENTS_MANAGE,
        Permission.PAYMENTS_RECORD,
        Permission.PAYMENTS_VIEW_CASHIER,
        Permission.EMERGENCY_MONITOR,
    },
    "RECEPTIONIST": {
        Permission.TENANTS_READ,
        Permission.ROOMS_READ,
        Permission.DOCTORS_INVITE,
        Permission.APPOINTMENTS_BOOK,
        Permission.APPOINTMENTS_MANAGE,
        Permission.PAYMENTS_RECORD,
        Permission.PAYMENTS_VIEW_CASHIER,
    },
    "DOCTOR": {
        Permission.TENANTS_READ,
        Permission.ROOMS_READ,
        Permission.DOCTORS_SCHEDULE_MANAGE,
        Permission.APPOINTMENTS_MANAGE,
        Permission.CLINICAL_RECORDS_READ,
        Permission.CLINICAL_RECORDS_WRITE,
        Permission.EMERGENCY_RESPOND,
    },
    "PATIENT": {
        Permission.TENANTS_READ,
        Permission.APPOINTMENTS_BOOK,
        Permission.APPOINTMENTS_MANAGE,
        Permission.CLINICAL_RECORDS_READ,
        Permission.EMERGENCY_TRIGGER,
    },
}


def has_permission(role: str, permission: Permission) -> bool:
    """Valida si un rol cuenta con un permiso especifico segun la matriz ACL."""
    perms = DEFAULT_ROLE_PERMISSIONS.get(role, set())
    return permission in perms
