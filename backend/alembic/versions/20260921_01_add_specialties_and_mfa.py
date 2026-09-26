"""add specialties and mfa columns to users

Revision ID: 20260921_01
Revises: 
Create Date: 2026-09-21 11:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260921_01'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    columns_to_add = [
        ("users", "specialty", "VARCHAR(500) NULL"),
        ("users", "specialties", "JSON NULL"),
        ("users", "license_number", "VARCHAR(100) NULL"),
        ("users", "biography", "VARCHAR(1000) NULL"),
        ("users", "mfa_enabled", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("users", "mfa_secret", "VARCHAR(64) NULL"),
        ("users", "mfa_recovery_codes_hash", "VARCHAR(255) NULL"),
        ("users", "is_available_for_emergencies", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("users", "license_verification_status", "VARCHAR(32) NOT NULL DEFAULT 'NOT_APPLICABLE'"),
        ("users", "license_document_url", "VARCHAR(500) NULL"),
        ("users", "verified_by_user_id", "VARCHAR(36) NULL"),
        ("users", "verified_at", "DATETIME NULL"),
        ("users", "preferred_notification_channels", "JSON NULL"),
        ("users", "no_show_strikes", "INT NOT NULL DEFAULT 0"),
        ("users", "is_restricted_booking", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("appointments", "intake_data", "JSON NULL"),
        ("appointments", "dependent_id", "VARCHAR(36) NULL"),
        ("appointments", "room_id", "VARCHAR(36) NULL"),
        ("appointments", "cancellation_reason", "VARCHAR(255) NULL"),
    ]
    for table, col_name, col_type in columns_to_add:
        try:
            conn.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))
        except Exception:
            pass

    try:
        conn.execute(sa.text(
            "UPDATE users SET specialties = JSON_ARRAY(specialty) WHERE specialty IS NOT NULL AND (specialties IS NULL OR JSON_LENGTH(specialties) = 0)"
        ))
    except Exception:
        pass


def downgrade() -> None:
    pass
