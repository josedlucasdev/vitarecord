"""agrega columnas de metodos de recuperacion y preferencias de notificacion a users

Revision ID: 20260926_03
Revises: 20260926_02
Create Date: 2026-09-26 17:15:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260926_03"
down_revision = "20260926_02"
branch_labels = None
depends_on = None

COLUMNS = [
    ("users", "recovery_email", "recovery_email VARCHAR(255) NULL"),
    ("users", "recovery_phone", "recovery_phone VARCHAR(32) NULL"),
    ("users", "notification_preferences", "notification_preferences JSON NULL"),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        return

    present = {c["name"] for c in inspector.get_columns("users")}
    for table, column, ddl in COLUMNS:
        if column not in present:
            op.execute(sa.text(f"ALTER TABLE `{table}` ADD COLUMN {ddl}"))

    op.execute(sa.text("ALTER TABLE `users` MODIFY COLUMN `mfa_recovery_codes_hash` TEXT NULL"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        return

    present = {c["name"] for c in inspector.get_columns("users")}
    for table, column, _ in COLUMNS:
        if column in present:
            op.execute(sa.text(f"ALTER TABLE `{table}` DROP COLUMN `{column}`"))
