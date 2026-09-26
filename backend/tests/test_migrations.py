"""El esquema lo define Alembic (plan/plan.md 2.A y Modulo 0 DoD).

Falla si alguien cambia un modelo sin crear la migracion correspondiente, o si
el historial de migraciones queda con mas de una cabeza.
"""

from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

import app.models  # noqa: F401  (registra todos los modelos)
from app.core.config import settings
from app.models.base import Base

BACKEND = Path(__file__).resolve().parents[1]


def _script() -> ScriptDirectory:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    return ScriptDirectory.from_config(cfg)


def test_single_migration_head():
    assert len(_script().get_heads()) == 1


def test_database_is_at_head_and_matches_models():
    engine = create_engine(settings.DATABASE_SYNC_URL)
    try:
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn, opts={"compare_type": True})
            assert ctx.get_current_revision() == _script().get_current_head()
            diff = compare_metadata(ctx, Base.metadata)
    finally:
        engine.dispose()
    assert diff == [], f"Modelos sin migracion: {diff}"
