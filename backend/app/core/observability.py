"""Logging estructurado, Sentry y Métricas Prometheus (plan/plan.md seccion 2.B.10 y Modulo 8).
"""

import logging
import sys
import time
from typing import Callable
from fastapi import Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from app.core.config import settings

# --- Métricas Prometheus Obligatorias del Sistema ---
# Latencia HTTP y Concurrencia (permite p95 y p99 de /appointments/book y demás rutas)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "Duración de peticiones HTTP en segundos",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total de peticiones HTTP atendidas",
    ["method", "endpoint", "status_code"],
)

# Tasa de error 409 (Race condition detection)
APPOINTMENT_CONFLICTS_TOTAL = Counter(
    "appointment_conflicts_total",
    "Total de colisiones de reserva (HTTP 409 Conflict) detectadas por cerrojos mutex",
    ["resource_type"],  # 'doctor' o 'room'
)

# Citas agendadas exitosamente
APPOINTMENTS_BOOKED_TOTAL = Counter(
    "appointments_booked_total",
    "Total de citas agendadas con éxito",
    ["clinic_id"],
)

# SLA de Emergencias Médicas Remotas
EMERGENCY_RESPONSE_TIME_SECONDS = Histogram(
    "emergency_response_time_seconds",
    "Tiempo en segundos desde la activación de la urgencia SOS hasta la toma por un médico",
    ["escalation_level"],
    buckets=[10, 30, 60, 90, 120, 180, 240, 300, 600],
)

# Omnicanalidad y Confirmaciones de Entrega
NOTIFICATION_DELIVERIES_TOTAL = Counter(
    "notification_deliveries_total",
    "Total de notificaciones despachadas por canal y su estado de confirmación",
    ["channel", "status"],  # channel: 'whatsapp', 'twilio_sms', 'fcm', 'email'
)

# Profundidad de colas de tareas
WORKER_QUEUE_DEPTH = Gauge(
    "worker_queue_depth",
    "Profundidad actual de las colas de procesamiento asíncrono",
    ["queue_name"],
)


def setup_observability() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=(
            '{"timestamp":"%(asctime)s","level":"%(levelname)s",'
            '"logger":"%(name)s","message":"%(message)s"}'
        ),
        stream=sys.stdout,
    )

    if settings.SENTRY_DSN:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.2,
            environment=settings.ENVIRONMENT,
        )


async def prometheus_metrics_middleware(request: Request, call_next: Callable) -> Response:
    """Middleware para instrumentar automáticamente latencia y conteo de respuestas HTTP."""
    if request.url.path == "/metrics" or request.url.path == "/health":
        return await call_next(request)

    start_time = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start_time

    # Normalizar ruta para no crear explosión de cardinalidad con IDs
    endpoint = request.url.path
    if endpoint.startswith("/api/v1/appointments/book"):
        endpoint = "/api/v1/appointments/book"
    elif endpoint.startswith("/api/v1/emergencies"):
        endpoint = "/api/v1/emergencies/*"
    elif endpoint.startswith("/api/v1/medical-records"):
        endpoint = "/api/v1/medical-records/*"

    status_code = str(response.status_code)
    HTTP_REQUEST_DURATION_SECONDS.labels(method=request.method, endpoint=endpoint).observe(duration)
    HTTP_REQUESTS_TOTAL.labels(method=request.method, endpoint=endpoint, status_code=status_code).inc()

    if response.status_code == 409:
        APPOINTMENT_CONFLICTS_TOTAL.labels(resource_type="schedule_lock").inc()

    return response


def get_metrics_response() -> Response:
    """Retorna las métricas en formato estándar de Prometheus."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
