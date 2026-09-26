"""Conversión entre la hora local de cada clínica y UTC (plan/plan.md 2.B.4).

Todo se almacena en UTC (DATETIME sin zona, interpretado como UTC). Las reglas
de negocio que dependen del "día" o de la "hora" (cuadre de caja diario,
horarios de consulta, apertura de consultorios) se evalúan en la zona IANA de
la clínica (`clinics.timezone`, p. ej. America/Caracas).
"""

import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TZ = "America/Caracas"
UTC = datetime.timezone.utc


def get_zone(tz_name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name or DEFAULT_TZ)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(DEFAULT_TZ)


def today_in(tz_name: str | None) -> datetime.date:
    return datetime.datetime.now(get_zone(tz_name)).date()


def local_day_bounds_utc(day: datetime.date, tz_name: str | None) -> tuple[datetime.datetime, datetime.datetime]:
    """[inicio, fin) del día local de la clínica, expresado en UTC naive (como se guarda en MySQL)."""
    zone = get_zone(tz_name)
    start_local = datetime.datetime.combine(day, datetime.time.min, tzinfo=zone)
    end_local = datetime.datetime.combine(day + datetime.timedelta(days=1), datetime.time.min, tzinfo=zone)
    return (
        start_local.astimezone(UTC).replace(tzinfo=None),
        end_local.astimezone(UTC).replace(tzinfo=None),
    )


def local_to_utc_naive(value: datetime.datetime, tz_name: str | None) -> datetime.datetime:
    """Hora local de pared (naive) de la clínica -> UTC naive."""
    aware = value.replace(tzinfo=get_zone(tz_name)) if value.tzinfo is None else value
    return aware.astimezone(UTC).replace(tzinfo=None)


def utc_to_local(value: datetime.datetime, tz_name: str | None) -> datetime.datetime:
    """UTC (naive o aware) -> hora local aware de la clínica."""
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value
    return aware.astimezone(get_zone(tz_name))
