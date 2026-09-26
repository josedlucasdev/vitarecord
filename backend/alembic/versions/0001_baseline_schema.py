"""baseline schema

Esquema completo de la base de datos a partir de los modelos (plan/plan.md
seccion 2.A: Alembic es la fuente de verdad del esquema).

Es IDEMPOTENTE a proposito: las bases de datos existentes se crearon con
`Base.metadata.create_all` + ALTER TABLE en app/db/seed.py, antes de que
existieran migraciones. En ellas esta revision solo crea las tablas o
indices que falten; en una base vacia crea todo. Las columnas agregadas
despues de que una tabla ya existia se completan en revisiones posteriores.

Revision ID: 0001_baseline
Revises: 
Create Date: 2026-09-25 20:46:55.866800

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001_baseline'
down_revision = None
branch_labels = None
depends_on = None


def _create_table(name, *columns, **kw):
    if sa.inspect(op.get_bind()).has_table(name):
        return
    op.create_table(name, *columns, **kw)


def _create_index(index_name, table_name, columns, **kw):
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table(table_name):
        existing = {ix["name"] for ix in inspector.get_indexes(table_name)}
        existing |= {uc["name"] for uc in inspector.get_unique_constraints(table_name)}
        if str(index_name) in existing:
            return
        # Tabla legada sin la columna todavia: el indice lo crea la revision
        # que agrega la columna (20260926_01).
        present = {c["name"] for c in inspector.get_columns(table_name)}
        if not set(columns) <= present:
            return
    op.create_index(index_name, table_name, columns, **kw)


def upgrade() -> None:
    _create_table('clinics',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('slug', sa.String(length=100), nullable=False),
    sa.Column('timezone', sa.String(length=64), nullable=False),
    sa.Column('country_code', sa.String(length=2), nullable=False),
    sa.Column('phone', sa.String(length=32), nullable=True),
    sa.Column('address', sa.String(length=255), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('require_mfa_for_receptionists', sa.Boolean(), nullable=False),
    sa.Column('emergency_doctor_attempts', sa.Integer(), nullable=False),
    sa.Column('emergency_backup_phone', sa.String(length=32), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_clinics_slug'), 'clinics', ['slug'], unique=True)
    _create_table('support_chat_sessions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('session_token', sa.String(length=64), nullable=False),
    sa.Column('id_card', sa.String(length=32), nullable=False),
    sa.Column('phone', sa.String(length=32), nullable=False),
    sa.Column('full_name', sa.String(length=128), nullable=False),
    sa.Column('status', sa.String(length=16), server_default='active', nullable=False),
    sa.Column('rating', sa.Integer(), nullable=True),
    sa.Column('rating_comment', sa.Text(), nullable=True),
    sa.Column('closed_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_support_chat_sessions_id_card'), 'support_chat_sessions', ['id_card'], unique=False)
    _create_index(op.f('ix_support_chat_sessions_phone'), 'support_chat_sessions', ['phone'], unique=False)
    _create_index(op.f('ix_support_chat_sessions_session_token'), 'support_chat_sessions', ['session_token'], unique=True)
    _create_table('clinic_encryption_keys',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('clinic_id', sa.String(length=36), nullable=False),
    sa.Column('key_version', sa.Integer(), nullable=False),
    sa.Column('encrypted_dek', sa.String(length=512), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_clinic_encryption_keys_clinic_id'), 'clinic_encryption_keys', ['clinic_id'], unique=False)
    _create_index(op.f('ix_clinic_encryption_keys_key_version'), 'clinic_encryption_keys', ['key_version'], unique=False)
    _create_table('clinic_rooms',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('room_number', sa.String(length=50), nullable=True),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.Column('specialty', sa.String(length=100), nullable=True),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('operating_hours', sa.JSON(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('clinic_id', sa.String(length=36), nullable=False),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_clinic_rooms_clinic_id'), 'clinic_rooms', ['clinic_id'], unique=False)
    _create_table('support_chat_messages',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('session_id', sa.Integer(), nullable=False),
    sa.Column('sender_type', sa.String(length=16), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('telegram_message_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['support_chat_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_support_chat_messages_session_id'), 'support_chat_messages', ['session_id'], unique=False)
    _create_index(op.f('ix_support_chat_messages_telegram_message_id'), 'support_chat_messages', ['telegram_message_id'], unique=False)
    _create_table('users',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=255), nullable=True),
    sa.Column('phone', sa.String(length=32), nullable=True),
    sa.Column('hashed_password', sa.String(length=255), nullable=True),
    sa.Column('role', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('clinic_id', sa.String(length=36), nullable=True),
    sa.Column('specialty', sa.String(length=500), nullable=True),
    sa.Column('specialties', sa.JSON(), nullable=True),
    sa.Column('license_number', sa.String(length=100), nullable=True),
    sa.Column('biography', sa.String(length=1000), nullable=True),
    sa.Column('profile_picture_url', sa.String(length=500), nullable=True),
    sa.Column('academic_degrees', sa.JSON(), nullable=True),
    sa.Column('work_experience', sa.JSON(), nullable=True),
    sa.Column('is_public_profile_enabled', sa.Boolean(), nullable=False),
    sa.Column('license_verification_status', sa.String(length=32), nullable=False),
    sa.Column('license_document_url', sa.String(length=500), nullable=True),
    sa.Column('verified_by_user_id', sa.String(length=36), nullable=True),
    sa.Column('verified_at', sa.DateTime(), nullable=True),
    sa.Column('preferred_notification_channels', sa.JSON(), nullable=True),
    sa.Column('no_show_strikes', sa.Integer(), nullable=False),
    sa.Column('is_restricted_booking', sa.Boolean(), nullable=False),
    sa.Column('mfa_enabled', sa.Boolean(), nullable=False),
    sa.Column('mfa_secret', sa.String(length=64), nullable=True),
    sa.Column('mfa_recovery_codes_hash', sa.String(length=255), nullable=True),
    sa.Column('is_available_for_emergencies', sa.Boolean(), nullable=False),
    sa.Column('identification_number', sa.String(length=32), nullable=True),
    sa.Column('birth_date', sa.DateTime(), nullable=True),
    sa.Column('gender', sa.String(length=16), nullable=True),
    sa.Column('address', sa.String(length=255), nullable=True),
    sa.Column('city', sa.String(length=100), nullable=True),
    sa.Column('country', sa.String(length=100), nullable=True),
    sa.Column('blood_type', sa.String(length=10), nullable=True),
    sa.Column('height_cm', sa.Float(), nullable=True),
    sa.Column('allergies', sa.String(length=500), nullable=True),
    sa.Column('chronic_conditions', sa.String(length=500), nullable=True),
    sa.Column('emergency_contact_name', sa.String(length=255), nullable=True),
    sa.Column('emergency_contact_phone', sa.String(length=32), nullable=True),
    sa.Column('emergency_contact_relationship', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ),
    sa.ForeignKeyConstraint(['verified_by_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_users_clinic_id'), 'users', ['clinic_id'], unique=False)
    _create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    _create_table('audit_logs',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('clinic_id', sa.String(length=36), nullable=True),
    sa.Column('user_id', sa.String(length=36), nullable=True),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('entity_type', sa.String(length=64), nullable=False),
    sa.Column('entity_id', sa.String(length=36), nullable=False),
    sa.Column('details', sa.JSON(), nullable=True),
    sa.Column('ip_address', sa.String(length=64), nullable=True),
    sa.Column('user_agent', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    _create_index(op.f('ix_audit_logs_clinic_id'), 'audit_logs', ['clinic_id'], unique=False)
    _create_index(op.f('ix_audit_logs_entity_id'), 'audit_logs', ['entity_id'], unique=False)
    _create_index(op.f('ix_audit_logs_entity_type'), 'audit_logs', ['entity_type'], unique=False)
    _create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    _create_table('doctor_clinic_affiliations',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('doctor_id', sa.String(length=36), nullable=False),
    sa.Column('clinic_id', sa.String(length=36), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('invitation_token', sa.String(length=500), nullable=True),
    sa.Column('invitation_expires_at', sa.DateTime(), nullable=True),
    sa.Column('responded_at', sa.DateTime(), nullable=True),
    sa.Column('contract_type', sa.String(length=32), nullable=False),
    sa.Column('consultation_fee', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=8), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ),
    sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_doctor_clinic_affiliations_clinic_id'), 'doctor_clinic_affiliations', ['clinic_id'], unique=False)
    _create_index(op.f('ix_doctor_clinic_affiliations_doctor_id'), 'doctor_clinic_affiliations', ['doctor_id'], unique=False)
    _create_table('doctor_schedule_locks',
    sa.Column('doctor_id', sa.String(length=36), nullable=False),
    sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('doctor_id')
    )
    _create_table('doctor_weekly_schedules',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('doctor_id', sa.String(length=36), nullable=False),
    sa.Column('day_of_week', sa.Integer(), nullable=False),
    sa.Column('start_time', sa.Time(), nullable=False),
    sa.Column('end_time', sa.Time(), nullable=False),
    sa.Column('slot_duration_minutes', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('clinic_id', sa.String(length=36), nullable=False),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ),
    sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_doctor_weekly_schedules_clinic_id'), 'doctor_weekly_schedules', ['clinic_id'], unique=False)
    _create_index(op.f('ix_doctor_weekly_schedules_doctor_id'), 'doctor_weekly_schedules', ['doctor_id'], unique=False)
    _create_table('medical_procedures',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('clinic_id', sa.String(length=36), nullable=False),
    sa.Column('doctor_id', sa.String(length=36), nullable=True),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=8), nullable=False),
    sa.Column('duration_minutes', sa.Integer(), nullable=False),
    sa.Column('category', sa.String(length=64), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_medical_procedures_clinic_id'), 'medical_procedures', ['clinic_id'], unique=False)
    _create_index(op.f('ix_medical_procedures_doctor_id'), 'medical_procedures', ['doctor_id'], unique=False)
    _create_table('patient_clinic_affiliations',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('patient_id', sa.String(length=36), nullable=False),
    sa.Column('clinic_id', sa.String(length=36), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_patient_clinic_affiliations_clinic_id'), 'patient_clinic_affiliations', ['clinic_id'], unique=False)
    _create_index(op.f('ix_patient_clinic_affiliations_patient_id'), 'patient_clinic_affiliations', ['patient_id'], unique=False)
    _create_table('patient_consent_grants',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('patient_id', sa.String(length=36), nullable=False),
    sa.Column('granted_to_clinic_id', sa.String(length=36), nullable=False),
    sa.Column('granted_by_user_id', sa.String(length=36), nullable=False),
    sa.Column('scope', sa.String(length=64), nullable=False),
    sa.Column('granted_at', sa.DateTime(), nullable=False),
    sa.Column('granted_until', sa.DateTime(), nullable=False),
    sa.Column('is_revoked', sa.Boolean(), nullable=False),
    sa.Column('revoked_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['granted_by_user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['granted_to_clinic_id'], ['clinics.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['patient_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_patient_consent_grants_granted_to_clinic_id'), 'patient_consent_grants', ['granted_to_clinic_id'], unique=False)
    _create_index(op.f('ix_patient_consent_grants_patient_id'), 'patient_consent_grants', ['patient_id'], unique=False)
    _create_table('patient_dependents',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('guardian_user_id', sa.String(length=36), nullable=False),
    sa.Column('full_name', sa.String(length=128), nullable=False),
    sa.Column('relationship', sa.String(length=32), nullable=False),
    sa.Column('birth_date', sa.Date(), nullable=False),
    sa.Column('id_document', sa.String(length=32), nullable=True),
    sa.Column('gender', sa.String(length=16), nullable=True),
    sa.Column('emancipation_status', sa.String(length=32), nullable=False),
    sa.Column('blood_type', sa.String(length=10), nullable=True),
    sa.Column('height_cm', sa.Float(), nullable=True),
    sa.Column('allergies', sa.String(length=500), nullable=True),
    sa.Column('chronic_conditions', sa.String(length=500), nullable=True),
    sa.Column('phone', sa.String(length=32), nullable=True),
    sa.Column('notes', sa.String(length=1000), nullable=True),
    sa.Column('profile_picture_url', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['guardian_user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_patient_dependents_guardian_user_id'), 'patient_dependents', ['guardian_user_id'], unique=False)
    _create_table('refresh_tokens',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('token_hash', sa.String(length=255), nullable=False),
    sa.Column('device_info', sa.String(length=255), nullable=True),
    sa.Column('ip_address', sa.String(length=64), nullable=True),
    sa.Column('issued_at', sa.DateTime(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('revoked_at', sa.DateTime(), nullable=True),
    sa.Column('replaced_by_token_id', sa.String(length=36), nullable=True),
    sa.ForeignKeyConstraint(['replaced_by_token_id'], ['refresh_tokens.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    _create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)
    _create_table('room_schedule_locks',
    sa.Column('room_id', sa.String(length=36), nullable=False),
    sa.ForeignKeyConstraint(['room_id'], ['clinic_rooms.id'], ),
    sa.PrimaryKeyConstraint('room_id')
    )
    _create_table('user_device_tokens',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('fcm_token', sa.String(length=512), nullable=False),
    sa.Column('platform', sa.String(length=32), nullable=False),
    sa.Column('device_name', sa.String(length=128), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('last_used_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_user_device_tokens_fcm_token'), 'user_device_tokens', ['fcm_token'], unique=True)
    _create_index(op.f('ix_user_device_tokens_user_id'), 'user_device_tokens', ['user_id'], unique=False)
    _create_table('appointments',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('clinic_id', sa.String(length=36), nullable=False),
    sa.Column('doctor_id', sa.String(length=36), nullable=False),
    sa.Column('patient_id', sa.String(length=36), nullable=False),
    sa.Column('dependent_id', sa.String(length=36), nullable=True),
    sa.Column('room_id', sa.String(length=36), nullable=True),
    sa.Column('start_time', sa.DateTime(), nullable=False),
    sa.Column('end_time', sa.DateTime(), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('reason', sa.String(length=255), nullable=True),
    sa.Column('cancellation_reason', sa.String(length=255), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('intake_data', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['dependent_id'], ['patient_dependents.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['patient_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['room_id'], ['clinic_rooms.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_appointments_clinic_id'), 'appointments', ['clinic_id'], unique=False)
    _create_index(op.f('ix_appointments_dependent_id'), 'appointments', ['dependent_id'], unique=False)
    _create_index(op.f('ix_appointments_doctor_id'), 'appointments', ['doctor_id'], unique=False)
    _create_index(op.f('ix_appointments_end_time'), 'appointments', ['end_time'], unique=False)
    _create_index(op.f('ix_appointments_patient_id'), 'appointments', ['patient_id'], unique=False)
    _create_index(op.f('ix_appointments_room_id'), 'appointments', ['room_id'], unique=False)
    _create_index(op.f('ix_appointments_start_time'), 'appointments', ['start_time'], unique=False)
    _create_index(op.f('ix_appointments_status'), 'appointments', ['status'], unique=False)
    _create_table('emergency_incidents',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('clinic_id', sa.String(length=36), nullable=False),
    sa.Column('patient_id', sa.String(length=36), nullable=False),
    sa.Column('dependent_id', sa.String(length=36), nullable=True),
    sa.Column('assigned_doctor_id', sa.String(length=36), nullable=True),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('escalation_level', sa.Integer(), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('chief_complaint', sa.String(length=255), nullable=False),
    sa.Column('triage_notes', sa.Text(), nullable=True),
    sa.Column('disclaimer_acknowledged_at', sa.DateTime(), nullable=False),
    sa.Column('triggered_at', sa.DateTime(), nullable=False),
    sa.Column('accepted_at', sa.DateTime(), nullable=True),
    sa.Column('resolved_at', sa.DateTime(), nullable=True),
    sa.Column('last_escalated_at', sa.DateTime(), nullable=True),
    sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
    sa.Column('acknowledged_by_id', sa.String(length=36), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['acknowledged_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['assigned_doctor_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['dependent_id'], ['patient_dependents.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['patient_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_emergency_incidents_assigned_doctor_id'), 'emergency_incidents', ['assigned_doctor_id'], unique=False)
    _create_index(op.f('ix_emergency_incidents_clinic_id'), 'emergency_incidents', ['clinic_id'], unique=False)
    _create_index(op.f('ix_emergency_incidents_patient_id'), 'emergency_incidents', ['patient_id'], unique=False)
    _create_index(op.f('ix_emergency_incidents_status'), 'emergency_incidents', ['status'], unique=False)
    _create_table('appointment_procedures',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('appointment_id', sa.String(length=36), nullable=False),
    sa.Column('procedure_id', sa.String(length=36), nullable=True),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=8), nullable=False),
    sa.Column('notes', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['procedure_id'], ['medical_procedures.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_appointment_procedures_appointment_id'), 'appointment_procedures', ['appointment_id'], unique=False)
    _create_index(op.f('ix_appointment_procedures_procedure_id'), 'appointment_procedures', ['procedure_id'], unique=False)
    _create_table('medical_records',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('appointment_id', sa.String(length=36), nullable=False),
    sa.Column('clinic_id', sa.String(length=36), nullable=False),
    sa.Column('doctor_id', sa.String(length=36), nullable=False),
    sa.Column('patient_id', sa.String(length=36), nullable=False),
    sa.Column('dependent_id', sa.String(length=36), nullable=True),
    sa.Column('encrypted_anamnesis', sa.Text(), nullable=False),
    sa.Column('encrypted_physical_exam', sa.Text(), nullable=True),
    sa.Column('encrypted_diagnosis', sa.Text(), nullable=False),
    sa.Column('encrypted_plan', sa.Text(), nullable=False),
    sa.Column('icd10_code', sa.String(length=16), nullable=True),
    sa.Column('icd10_description', sa.String(length=255), nullable=True),
    sa.Column('encryption_key_version', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['dependent_id'], ['patient_dependents.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['patient_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_medical_records_appointment_id'), 'medical_records', ['appointment_id'], unique=True)
    _create_index(op.f('ix_medical_records_clinic_id'), 'medical_records', ['clinic_id'], unique=False)
    _create_index(op.f('ix_medical_records_dependent_id'), 'medical_records', ['dependent_id'], unique=False)
    _create_index(op.f('ix_medical_records_doctor_id'), 'medical_records', ['doctor_id'], unique=False)
    _create_index(op.f('ix_medical_records_encryption_key_version'), 'medical_records', ['encryption_key_version'], unique=False)
    _create_index(op.f('ix_medical_records_icd10_code'), 'medical_records', ['icd10_code'], unique=False)
    _create_index(op.f('ix_medical_records_patient_id'), 'medical_records', ['patient_id'], unique=False)
    _create_index(op.f('ix_medical_records_status'), 'medical_records', ['status'], unique=False)
    _create_table('notification_logs',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('incident_id', sa.String(length=36), nullable=True),
    sa.Column('appointment_id', sa.String(length=36), nullable=True),
    sa.Column('recipient_id', sa.String(length=36), nullable=True),
    sa.Column('channel', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('attempt_number', sa.Integer(), nullable=False),
    sa.Column('sent_at', sa.DateTime(), nullable=False),
    sa.Column('delivered_at', sa.DateTime(), nullable=True),
    sa.Column('response_time_seconds', sa.Float(), nullable=True),
    sa.Column('error_message', sa.String(length=255), nullable=True),
    sa.Column('external_message_id', sa.String(length=500), nullable=True),
    sa.Column('metadata_payload', sa.JSON(), nullable=True),
    sa.Column('is_read', sa.Boolean(), nullable=False),
    sa.Column('read_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['incident_id'], ['emergency_incidents.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_notification_logs_appointment_id'), 'notification_logs', ['appointment_id'], unique=False)
    _create_index(op.f('ix_notification_logs_external_message_id'), 'notification_logs', ['external_message_id'], unique=False)
    _create_index(op.f('ix_notification_logs_incident_id'), 'notification_logs', ['incident_id'], unique=False)
    _create_index(op.f('ix_notification_logs_recipient_id'), 'notification_logs', ['recipient_id'], unique=False)
    _create_table('payment_records',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('appointment_id', sa.String(length=36), nullable=False),
    sa.Column('clinic_id', sa.String(length=36), nullable=False),
    sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=8), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('payment_method', sa.String(length=32), nullable=True),
    sa.Column('reference', sa.String(length=64), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('recorded_by_user_id', sa.String(length=36), nullable=True),
    sa.Column('paid_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['recorded_by_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_payment_records_appointment_id'), 'payment_records', ['appointment_id'], unique=True)
    _create_index(op.f('ix_payment_records_clinic_id'), 'payment_records', ['clinic_id'], unique=False)
    _create_index(op.f('ix_payment_records_status'), 'payment_records', ['status'], unique=False)
    _create_table('medical_attachments',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('medical_record_id', sa.String(length=36), nullable=False),
    sa.Column('clinic_id', sa.String(length=36), nullable=False),
    sa.Column('file_name', sa.String(length=255), nullable=False),
    sa.Column('content_type', sa.String(length=100), nullable=False),
    sa.Column('file_size', sa.Integer(), nullable=False),
    sa.Column('s3_key', sa.String(length=512), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['medical_record_id'], ['medical_records.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('s3_key')
    )
    _create_index(op.f('ix_medical_attachments_clinic_id'), 'medical_attachments', ['clinic_id'], unique=False)
    _create_index(op.f('ix_medical_attachments_medical_record_id'), 'medical_attachments', ['medical_record_id'], unique=False)
    _create_table('prescriptions',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('medical_record_id', sa.String(length=36), nullable=False),
    sa.Column('appointment_id', sa.String(length=36), nullable=False),
    sa.Column('clinic_id', sa.String(length=36), nullable=False),
    sa.Column('doctor_id', sa.String(length=36), nullable=False),
    sa.Column('patient_id', sa.String(length=36), nullable=False),
    sa.Column('dependent_id', sa.String(length=36), nullable=True),
    sa.Column('verification_hash', sa.String(length=64), nullable=False),
    sa.Column('prescription_code', sa.String(length=32), nullable=False),
    sa.Column('items', sa.JSON(), nullable=False),
    sa.Column('diagnosis_summary', sa.String(length=255), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('issued_at', sa.DateTime(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['dependent_id'], ['patient_dependents.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['medical_record_id'], ['medical_records.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['patient_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_prescriptions_appointment_id'), 'prescriptions', ['appointment_id'], unique=False)
    _create_index(op.f('ix_prescriptions_clinic_id'), 'prescriptions', ['clinic_id'], unique=False)
    _create_index(op.f('ix_prescriptions_dependent_id'), 'prescriptions', ['dependent_id'], unique=False)
    _create_index(op.f('ix_prescriptions_doctor_id'), 'prescriptions', ['doctor_id'], unique=False)
    _create_index(op.f('ix_prescriptions_medical_record_id'), 'prescriptions', ['medical_record_id'], unique=False)
    _create_index(op.f('ix_prescriptions_patient_id'), 'prescriptions', ['patient_id'], unique=False)
    _create_index(op.f('ix_prescriptions_prescription_code'), 'prescriptions', ['prescription_code'], unique=True)
    _create_index(op.f('ix_prescriptions_status'), 'prescriptions', ['status'], unique=False)
    _create_index(op.f('ix_prescriptions_verification_hash'), 'prescriptions', ['verification_hash'], unique=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # La linea base no se revierte: borraria todas las tablas con datos clinicos.
    raise NotImplementedError("La revision base del esquema no admite downgrade.")
