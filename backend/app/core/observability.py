"""Logging estructurado y Sentry (plan/plan.md seccion 2.B.10).

Las trazas OpenTelemetry y los dashboards de Prometheus/Grafana completos
se instrumentan en el Modulo 8; este modulo deja el punto de extension
(setup_observability) ya cableado desde app.main.
"""

import logging
import sys

from app.core.config import settings


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
