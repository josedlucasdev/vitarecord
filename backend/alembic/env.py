"""Entorno de Alembic.

Nota de arquitectura (ver plan/plan.md, seccion 2.A): `asyncmy` (el driver
que usa la aplicacion en runtime) no es compatible de forma directa con el
modo --autogenerate de Alembic. Por eso este archivo crea un motor
SINCRONO con PyMySQL (DATABASE_SYNC_URL) exclusivamente para generar y
aplicar migraciones. El runtime de FastAPI nunca importa este modulo.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.models.base import Base

# Importar TODOS los modelos (app/models/__init__.py) para que Base.metadata
# este completo: si falta uno, --autogenerate propondria borrar su tabla.
import app.models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_SYNC_URL)

# Cuando las migraciones se lanzan desde la app (app/db/seed.py) no se toca la
# configuracion de logging estructurado de la aplicacion.
if config.config_file_name is not None and not config.attributes.get("skip_logging_config"):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Cerrojo de MySQL: si arrancan varias replicas a la vez, solo una
        # aplica migraciones; las demas esperan y luego no encuentran nada.
        connection.exec_driver_sql("SELECT GET_LOCK('appcitas_alembic_upgrade', 120)")
        # El cerrojo es de sesion; se cierra la transaccion implicita para que
        # Alembic gestione (y confirme) la suya propia.
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
