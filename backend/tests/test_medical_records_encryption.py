import datetime
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from httpx import AsyncClient
from sqlalchemy import select

from app.core.crypto import (
    _decrypt_dek_with_kek,
    decrypt_field,
    get_or_create_clinic_dek,
    get_or_create_kek,
    rewrap_deks_with_new_kek,
    rotate_kek_master,
)
from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.models.appointment import Appointment
from app.models.clinic_encryption_key import ClinicEncryptionKey
from app.models.medical_record import MedicalRecord


@pytest.mark.asyncio
async def test_envelope_encryption_aes_gcm_and_kek_rotation(client: AsyncClient):
    """Criterio de Aceptacion (DoD): Cifrado AES-256-GCM en reposo y rotacion de KEK sin perdida de acceso."""
    doctor_token = create_access_token(
        subject="u2222222-2222-2222-2222-222222222222",
        clinic_id="c1111111-1111-1111-1111-111111111111",
        role="DOCTOR",
        email="doctor@intimasalud.com",
    )

    appointment_id = "a6666666-6666-6666-6666-666666666666"
    clinic_id = "c1111111-1111-1111-1111-111111111111"
    secret_text = "SECRET_PHI_CONFIDENCIAL_HALLAZGO_GINECOLOGICO_999"

    async with AsyncSessionLocal() as db:
        # Limpiar
        existing_rec = (await db.execute(select(MedicalRecord).where(MedicalRecord.appointment_id == appointment_id))).scalar_one_or_none()
        if existing_rec:
            await db.delete(existing_rec)
        existing_app = (await db.execute(select(Appointment).where(Appointment.id == appointment_id))).scalar_one_or_none()
        if existing_app:
            await db.delete(existing_app)
        existing_keys = (await db.execute(select(ClinicEncryptionKey).where(ClinicEncryptionKey.clinic_id == clinic_id))).scalars().all()
        for k in existing_keys:
            await db.delete(k)
        await db.commit()

        app = Appointment(
            id=appointment_id,
            clinic_id=clinic_id,
            doctor_id="u2222222-2222-2222-2222-222222222222",
            patient_id="u4444444-4444-4444-4444-444444444444",
            start_time=datetime.datetime(2026, 10, 11, 10, 0),
            end_time=datetime.datetime(2026, 10, 11, 10, 30),
            status="CONFIRMED",
            reason="Prueba de cifrado en reposo",
        )
        db.add(app)
        await db.commit()

    # 1. Crear historia medica a traves de la API
    resp = await client.post(
        "/api/v1/medical-records",
        json={
            "appointment_id": appointment_id,
            "anamnesis": secret_text,
            "physical_exam": "Examen normal",
            "diagnosis": "Diagnostico clinico cifrado",
            "plan": "Plan confidencial",
            "icd10_code": "N94.6",
            "icd10_description": "Dismenorrea no especificada",
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert resp.status_code == 201
    record_id = resp.json()["id"]

    # 2. Verificar directamente en la base de datos MySQL que el campo este CIFRADO
    async with AsyncSessionLocal() as db:
        rec = (await db.execute(select(MedicalRecord).where(MedicalRecord.id == record_id))).scalar_one()
        # En la base de datos NUNCA debe estar el texto plano
        assert secret_text not in rec.encrypted_anamnesis
        assert rec.encrypted_anamnesis != secret_text
        assert len(rec.encrypted_anamnesis) > len(secret_text)

        # Verificar que la version de llave exista
        assert rec.encryption_key_version >= 1

        # Descifrar manualmente con la DEK
        dek, _ = await get_or_create_clinic_dek(db, clinic_id, version=rec.encryption_key_version)
        decrypted = decrypt_field(rec.encrypted_anamnesis, dek)
        assert decrypted == secret_text

    # 3. Prueba de Rotacion de KEK (Rewrapping de DEKs y actualizacion en Vault):
    async with AsyncSessionLocal() as db:
        new_kek = await rotate_kek_master(db)
        await db.commit()

        # Verificar que la DEK se descifra correctamente con la NUEVA KEK
        key_row = (await db.execute(select(ClinicEncryptionKey).where(ClinicEncryptionKey.clinic_id == clinic_id, ClinicEncryptionKey.is_active == True))).scalar_one()
        raw_dek_after_rotation = _decrypt_dek_with_kek(key_row.encrypted_dek, new_kek)

        # Y que los historiales existentes siguen siendo descifrables sin perdida
        decrypted_after = decrypt_field(rec.encrypted_anamnesis, raw_dek_after_rotation)
        assert decrypted_after == secret_text

