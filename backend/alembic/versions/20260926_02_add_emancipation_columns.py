"""agrega columnas de emancipacion y cuenta vinculada a patient_dependents

Revision ID: 20260926_02
Revises: 20260926_01
Create Date: 2026-09-26 01:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260926_02"
down_revision = "20260926_01"
branch_labels = None
depends_on = None

COLUMNS = [
    ("patient_dependents", "email", "email VARCHAR(255) NULL"),
    ("patient_dependents", "linked_user_id", "linked_user_id VARCHAR(36) NULL"),
    ("patient_dependents", "emancipated_at", "emancipated_at DATETIME NULL"),
]

FOREIGN_KEYS = [
    ("patient_dependents", ["linked_user_id"], "users", ["id"], "SET NULL"),
]

INDEXES = [
    ("ix_patient_dependents_linked_user_id", "patient_dependents", ["linked_user_id"]),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("patient_dependents"):
        return

    present = {c["name"] for c in inspector.get_columns("patient_dependents")}
    for table, column, ddl in COLUMNS:
        if column not in present:
            op.execute(sa.text(f"ALTER TABLE `{table}` ADD COLUMN {ddl}"))

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("patient_dependents")}
    for name, table, columns in INDEXES:
        if name not in existing_indexes:
            op.create_index(name, table, columns, unique=False)

    existing_fks = {tuple(fk["constrained_columns"]) for fk in inspector.get_foreign_keys("patient_dependents")}
    for table, columns, ref_table, ref_columns, ondelete in FOREIGN_KEYS:
        if tuple(columns) not in existing_fks:
            op.create_foreign_key(
                f"fk_{table}_{'_'.join(columns)}_{ref_table}",
                table,
                ref_table,
                columns,
                ref_columns,
                ondelete=ondelete,
            )


def downgrade() -> None:
    pass
