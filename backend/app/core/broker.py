"""Configuración del broker de tareas asíncronas con Taskiq y Redis (plan/plan.md Módulo 6)."""

import logging
from taskiq_redis import ListQueueBroker

from app.core.config import settings

logger = logging.getLogger("broker")

# Broker central conectado a la instancia de Redis de la infraestructura
broker = ListQueueBroker(
    url=settings.REDIS_URL,
    queue_name="appcitas_tasks",
)
