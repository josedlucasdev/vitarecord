"""agrega soporte de anexos de cita, grabacion de audio y tipos de anexo a medical_attachments

Revision ID: 20260926_06
Revises: 20260926_05
Create Date: 2026-09-26 19:50:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260926_06"
down_revision = "20260926_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("medical_attachments"):
        return

    cols = {c["name"] for c in inspector.get_columns("medical_attachments")}

    # 1. Modificar medical_record_id para que sea NULLABLE (permite adjuntar antes de firmar)
    op.execute(sa.text("ALTER TABLE `medical_attachments` MODIFY COLUMN `medical_record_id` VARCHAR(36) NULL"))

    # 2. Agregar appointment_id si no existe
    if "appointment_id" not in cols:
        op.execute(sa.text(
            "ALTER TABLE `medical_attachments` ADD COLUMN `appointment_id` VARCHAR(36) NULL"
        ))
        try:
            op.execute(sa.text(
                "ALTER TABLE `medical_attachments` ADD CONSTRAINT `fk_medical_attachments_appointment_id` "
                "FOREIGN KEY (`appointment_id`) REFERENCES `appointments` (`id`) ON DELETE CASCADE"
            ))
        except Exception:
            pass
        try:
            op.execute(sa.text(
                "CREATE INDEX `ix_medical_attachments_appointment_id` ON `medical_attachments` (`appointment_id`)"
            ))
        except Exception:
            pass

    # 3. Agregar attachment_type si no existe
    if "attachment_type" not in cols:
        op.execute(sa.text(
            "ALTER TABLE `medical_attachments` ADD COLUMN `attachment_type` VARCHAR(32) NOT NULL DEFAULT 'DOCUMENT'"
        ))
        try:
            op.execute(sa.text(
                "CREATE INDEX `ix_medical_attachments_attachment_type` ON `medical_attachments` (`attachment_type`)"
            ))
        except Exception:
            pass


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("medical_attachments"):
        return

    cols = {c["name"] for c in inspector.get_columns("medical_attachments")}
    if "attachment_type" in cols:
        op.execute(sa.text("ALTER TABLE `medical_attachments` DROP COLUMN `attachment_type`"))
    if "appointment_id" in cols:
        try:
            op.execute(sa.text("ALTER TABLE `medical_attachments` DROP FOREIGN KEY `fk_medical_attachments_appointment_id`"))
        except Exception:
            pass
        op.execute(sa.text("ALTER TABLE `medical_attachments` DROP COLUMN `appointment_id`"))
