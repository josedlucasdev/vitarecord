"""agrega columna ai_consultation_assistant_enabled a clinics

Revision ID: 20260926_07
Revises: 20260926_06
Create Date: 2026-09-26 20:10:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260926_07"
down_revision = "20260926_06"
branch_labels = None
depends_on = None

COLUMNS = [
    ("clinics", "ai_consultation_assistant_enabled", "ai_consultation_assistant_enabled BOOLEAN NOT NULL DEFAULT FALSE"),
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
