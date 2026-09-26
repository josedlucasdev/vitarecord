"""agrega columnas de configuracion de IA a clinics

Revision ID: 20260926_04
Revises: 20260926_03
Create Date: 2026-09-26 18:22:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260926_04"
down_revision = "20260926_03"
branch_labels = None
depends_on = None

COLUMNS = [
    ("clinics", "ai_enabled", "ai_enabled BOOLEAN NOT NULL DEFAULT 0"),
    ("clinics", "ai_api_url", "ai_api_url VARCHAR(500) NULL"),
    ("clinics", "ai_api_key", "ai_api_key VARCHAR(500) NULL"),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("clinics"):
        return

    present = {c["name"] for c in inspector.get_columns("clinics")}
    for table, column, ddl in COLUMNS:
        if column not in present:
            op.execute(sa.text(f"ALTER TABLE `{table}` ADD COLUMN {ddl}"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("clinics"):
        return

    present = {c["name"] for c in inspector.get_columns("clinics")}
    for table, column, _ in COLUMNS:
        if column in present:
            op.execute(sa.text(f"ALTER TABLE `{table}` DROP COLUMN `{column}`"))
