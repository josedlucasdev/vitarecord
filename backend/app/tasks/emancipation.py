"""Tarea programada y orquestador diario de emancipación de dependientes (plan/plan.md Módulo 3 y 2.B.5).

Revisa dependientes con estatus 'MINOR' cuya edad alcanza los 18 años, transicionándolos
automáticamente a 'EMANCIPATION_PENDING_CONSENT', suspendiendo el acceso del titular a nuevas
historias clínicas e invitando al nuevo adulto a crear su cuenta independiente de paciente.
"""

import asyncio
import datetime
import logging
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.broker import broker
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis
from app.core.timezones import today_in
from app.models.audit import AuditLog
from app.models.patient_dependent import PatientDependent
from app.models.user import User
from app.services.notification_service import NotificationService

logger = logging.getLogger("emancipation_task")
LOCK_KEY = "lock:emancipation_check_scan"


@broker.task
async def check_dependents_emancipation_task() -> dict[str, int]:
    """Tarea Taskiq ejecutable por el worker en background."""
    return await process_dependents_emancipation()


async def process_dependents_emancipation() -> dict[str, int]:
    """Escanea dependientes menores que cumplieron 18 años y ejecuta la transición legal."""
    now_utc = datetime.datetime.utcnow()
    today_caracas = today_in("America/Caracas")

    # Fecha límite de nacimiento para tener exactamente 18 o más años
    try:
        cutoff_birth_date = today_caracas.replace(year=today_caracas.year - 18)
    except ValueError:
        # 29 de febrero en año no bisiesto
        cutoff_birth_date = today_caracas.replace(year=today_caracas.year - 18, day=28)

    transitioned = 0
    invitations_sent = 0

    async with AsyncSessionLocal() as db:
        stmt = (
            select(PatientDependent)
            .options(selectinload(PatientDependent.guardian))
            .where(
                PatientDependent.emancipation_status == "MINOR",
                PatientDependent.birth_date <= cutoff_birth_date,
            )
        )
        res = await db.execute(stmt)
        dependents = list(res.scalars().all())

        for dep in dependents:
            dep.emancipation_status = "EMANCIPATION_PENDING_CONSENT"
            dep.emancipated_at = now_utc
            transitioned += 1

            # Registrar auditoría de conformidad legal
            audit = AuditLog(
                action="DEPENDENT_EMANCIPATED",
                entity_type="patient_dependent",
                entity_id=dep.id,
                user_id=dep.guardian_user_id,
                details={
                    "full_name": dep.full_name,
                    "birth_date": dep.birth_date.isoformat(),
                    "emancipation_status": "EMANCIPATION_PENDING_CONSENT",
                    "reason": "Alcanzó la mayoría de edad (18 años). Acceso de titular a nuevas historias suspendido.",
                },
            )
            db.add(audit)

            # Si tiene correo propio, enviar invitación formal a cuenta independiente
            if dep.email and dep.email.strip():
                try:
                    notif_service = NotificationService(db)
                    await notif_service.send_multichannel_notification(
                        recipient=None,
                        email=dep.email.strip(),
                        subject="Invitación a crear tu cuenta independiente en VitaRecord",
                        message=(
                            f"Estimado/a {dep.full_name}, has cumplido la mayoría de edad legal. "
                            f"Tu expediente clínico ahora requiere tu consentimiento autónomo. "
                            f"Crea tu cuenta en VitaRecord para administrar tu historial con total privacidad."
                        ),
                    )
                    invitations_sent += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning("No se pudo enviar notificación de emancipación a %s: %s", dep.email, exc)

        if transitioned > 0:
            await db.commit()
            logger.info("Transición de emancipación completada: %d dependientes actualizados.", transitioned)

    return {
        "scanned": len(dependents),
        "transitioned": transitioned,
        "invitations_sent": invitations_sent,
    }


async def start_emancipation_scheduler(interval_seconds: int = 86400) -> None:
    """Bucle periódico (por defecto diario) para ejecución en worker dedicado."""
    logger.info("Iniciando scheduler de emancipación de dependientes (intervalo: %ds)", interval_seconds)
    while True:
        try:
            acquired = True
            try:
                acquired = bool(await get_redis().set(LOCK_KEY, "1", nx=True, ex=max(1, interval_seconds - 60)))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Cerrojo de emancipación sin Redis, ejecutando: %s", exc)

            if acquired:
                stats = await process_dependents_emancipation()
                if stats["transitioned"] > 0:
                    logger.info("Ciclo diario de emancipación: %s", stats)
        except asyncio.CancelledError:
            logger.info("Scheduler de emancipación cancelado.")
            break
        except Exception as exc:  # noqa: BLE001
            logger.error("Error en ciclo de emancipación: %s", exc)

        await asyncio.sleep(interval_seconds)
