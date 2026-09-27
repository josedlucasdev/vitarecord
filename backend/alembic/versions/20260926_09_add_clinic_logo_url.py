"""agrega columna logo_url a clinics

Revision ID: 20260926_09
Revises: 20260926_08
Create Date: 2026-09-26 20:25:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260926_09"
down_revision = "20260926_08"
branch_labels = None
depends_on = None

COLUMNS = [
    ("clinics", "logo_url", "logo_url VARCHAR(500) NULL"),
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
