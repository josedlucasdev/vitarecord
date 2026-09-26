"""sincroniza columnas agregadas fuera de migraciones

Revision ID: 20260926_01
Revises: 20260921_01
Create Date: 2026-09-26 00:00:00

Hasta ahora las columnas nuevas se agregaban con ALTER TABLE dentro de
app/db/seed.py en cada arranque. Esta revision recoge TODAS esas columnas
(mas las de la politica de MFA por clinica, el orquestador de urgencias y la
revocacion de consentimientos) y las agrega solo si faltan, de modo que
cualquier base existente quede igual a la linea base 0001_baseline.
A partir de aqui, todo cambio de esquema va en una revision nueva.
"""

from alembic import op
import sqlalchemy as sa

revision = "20260926_01"
down_revision = "20260921_01"
branch_labels = None
depends_on = None

# (tabla, columna, definicion DDL de MySQL)
COLUMNS = [
    ("clinics", "phone", "phone VARCHAR(32) NULL"),
    ("clinics", "address", "address VARCHAR(255) NULL"),
    ("clinics", "is_active", "is_active BOOLEAN NOT NULL DEFAULT TRUE"),
    ("clinics", "require_mfa_for_receptionists", "require_mfa_for_receptionists BOOLEAN NOT NULL DEFAULT FALSE"),
    ("clinics", "emergency_doctor_attempts", "emergency_doctor_attempts INT NOT NULL DEFAULT 2"),
    ("clinics", "emergency_backup_phone", "emergency_backup_phone VARCHAR(32) NULL"),
    ("users", "specialty", "specialty VARCHAR(500) NULL"),
    ("users", "specialties", "specialties JSON NULL"),
    ("users", "license_number", "license_number VARCHAR(100) NULL"),
    ("users", "biography", "biography VARCHAR(1000) NULL"),
    ("users", "academic_degrees", "academic_degrees JSON NULL"),
    ("users", "work_experience", "work_experience JSON NULL"),
    ("users", "is_public_profile_enabled", "is_public_profile_enabled BOOLEAN NOT NULL DEFAULT TRUE"),
    ("users", "license_verification_status", "license_verification_status VARCHAR(32) NOT NULL DEFAULT 'NOT_APPLICABLE'"),
    ("users", "license_document_url", "license_document_url VARCHAR(500) NULL"),
    ("users", "verified_by_user_id", "verified_by_user_id VARCHAR(36) NULL"),
    ("users", "verified_at", "verified_at DATETIME NULL"),
    ("users", "preferred_notification_channels", "preferred_notification_channels JSON NULL"),
    ("users", "no_show_strikes", "no_show_strikes INT NOT NULL DEFAULT 0"),
    ("users", "is_restricted_booking", "is_restricted_booking BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "mfa_enabled", "mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "mfa_secret", "mfa_secret VARCHAR(64) NULL"),
    ("users", "mfa_recovery_codes_hash", "mfa_recovery_codes_hash VARCHAR(255) NULL"),
    ("users", "is_available_for_emergencies", "is_available_for_emergencies BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "profile_picture_url", "profile_picture_url VARCHAR(500) NULL"),
    ("users", "identification_number", "identification_number VARCHAR(32) NULL"),
    ("users", "birth_date", "birth_date DATETIME NULL"),
    ("users", "gender", "gender VARCHAR(16) NULL"),
    ("users", "address", "address VARCHAR(255) NULL"),
    ("users", "city", "city VARCHAR(100) NULL"),
    ("users", "country", "country VARCHAR(100) NULL DEFAULT 'Venezuela'"),
    ("users", "blood_type", "blood_type VARCHAR(10) NULL"),
    ("users", "height_cm", "height_cm FLOAT NULL"),
    ("users", "allergies", "allergies VARCHAR(500) NULL"),
    ("users", "chronic_conditions", "chronic_conditions VARCHAR(500) NULL"),
    ("users", "emergency_contact_name", "emergency_contact_name VARCHAR(255) NULL"),
    ("users", "emergency_contact_phone", "emergency_contact_phone VARCHAR(32) NULL"),
    ("users", "emergency_contact_relationship", "emergency_contact_relationship VARCHAR(100) NULL"),
    ("clinic_rooms", "specialty", "specialty VARCHAR(100) NULL"),
    ("clinic_rooms", "status", "status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'"),
    ("clinic_rooms", "operating_hours", "operating_hours JSON NULL"),
    ("appointments", "intake_data", "intake_data JSON NULL"),
    ("appointments", "dependent_id", "dependent_id VARCHAR(36) NULL"),
    ("appointments", "room_id", "room_id VARCHAR(36) NULL"),
    ("appointments", "cancellation_reason", "cancellation_reason VARCHAR(255) NULL"),
    ("patient_dependents", "blood_type", "blood_type VARCHAR(10) NULL"),
    ("patient_dependents", "height_cm", "height_cm FLOAT NULL"),
    ("patient_dependents", "allergies", "allergies VARCHAR(500) NULL"),
    ("patient_dependents", "chronic_conditions", "chronic_conditions VARCHAR(500) NULL"),
    ("patient_dependents", "phone", "phone VARCHAR(32) NULL"),
    ("patient_dependents", "notes", "notes VARCHAR(1000) NULL"),
    ("patient_dependents", "profile_picture_url", "profile_picture_url VARCHAR(500) NULL"),
    ("notification_logs", "appointment_id", "appointment_id VARCHAR(36) NULL"),
    ("notification_logs", "external_message_id", "external_message_id VARCHAR(500) NULL"),
    ("notification_logs", "metadata_payload", "metadata_payload JSON NULL"),
    ("notification_logs", "is_read", "is_read BOOLEAN NOT NULL DEFAULT FALSE"),
    ("notification_logs", "read_at", "read_at DATETIME NULL"),
    ("emergency_incidents", "last_escalated_at", "last_escalated_at DATETIME NULL"),
    ("emergency_incidents", "acknowledged_at", "acknowledged_at DATETIME NULL"),
    ("emergency_incidents", "acknowledged_by_id", "acknowledged_by_id VARCHAR(36) NULL"),
    ("doctor_clinic_affiliations", "contract_type", "contract_type VARCHAR(32) NOT NULL DEFAULT 'INDEPENDENT'"),
    ("doctor_clinic_affiliations", "consultation_fee", "consultation_fee DECIMAL(10,2) NOT NULL DEFAULT 30.00"),
    ("doctor_clinic_affiliations", "currency", "currency VARCHAR(8) NOT NULL DEFAULT 'USD'"),
    ("patient_consent_grants", "revoked_at", "revoked_at DATETIME NULL"),
]

# Indices de columnas agregadas tarde (declarados con index=True en los modelos).
INDEXES = [
    ("ix_notification_logs_appointment_id", "notification_logs", ["appointment_id"]),
    ("ix_notification_logs_external_message_id", "notification_logs", ["external_message_id"]),
]


# Claves foraneas de columnas agregadas tarde: (tabla, columnas, tabla_ref, cols_ref, ondelete)
FOREIGN_KEYS = [
    ("emergency_incidents", ["acknowledged_by_id"], "users", ["id"], "SET NULL"),
]


def upgrade() -> None:
    bind = op.get_bind()
    for table, column, ddl in COLUMNS:
        inspector = sa.inspect(bind)
        if not inspector.has_table(table):
            continue
        present = {c["name"] for c in inspector.get_columns(table)}
        if column not in present:
            op.execute(sa.text(f"ALTER TABLE `{table}` ADD COLUMN {ddl}"))

    for name, table, columns in INDEXES:
        inspector = sa.inspect(bind)
        if not inspector.has_table(table):
            continue
        if name not in {ix["name"] for ix in inspector.get_indexes(table)}:
            op.create_index(name, table, columns, unique=False)


    for table, columns, ref_table, ref_columns, ondelete in FOREIGN_KEYS:
        inspector = sa.inspect(bind)
        if not inspector.has_table(table):
            continue
        existing = {tuple(fk["constrained_columns"]) for fk in inspector.get_foreign_keys(table)}
        if tuple(columns) not in existing:
            op.create_foreign_key(
                f"fk_{table}_{'_'.join(columns)}_{ref_table}", table, ref_table, columns, ref_columns, ondelete=ondelete
            )


def downgrade() -> None:
    # Columnas con datos de produccion: no se eliminan automaticamente.
    pass
