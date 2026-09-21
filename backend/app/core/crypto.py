"""Primitivas criptograficas y Envelope Encryption (AES-256-GCM) para datos clinicos (plan/plan.md 2.B.8).

Gestiona:
1. KEK (Key Encryption Key): Almacenada exclusivamente en HashiCorp Vault.
2. DEK (Data Encryption Key): Generada por clinica y version, almacenada cifrada en la BD con la KEK.
3. Cifrado a nivel de campo (Field-Level Encryption) con AES-256-GCM, nonce aleatorio de 12 bytes y autenticacion.
4. Rotacion de KEK y rotacion progresiva de DEK.
"""

import base64
import logging
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.secrets import read_secret, write_secret
from app.models.clinic_encryption_key import ClinicEncryptionKey

logger = logging.getLogger("crypto")

# Ruta en Vault para la KEK maestra
VAULT_KEK_PATH = "kms/kek"
DEFAULT_FALLBACK_KEK = b"IntimaSalud_Master_KEK_32B_Key!!"  # exactly 32 bytes


def _get_all_historical_keks() -> list[bytes]:
    """Obtiene todas las versiones históricas de la KEK desde Vault y fallback."""
    keks = []
    try:
        from app.core.secrets import get_vault_client
        client = get_vault_client()
        meta = client.secrets.kv.v2.read_secret_metadata(path=VAULT_KEK_PATH)
        versions = list(meta.get("data", {}).get("versions", {}).keys())
        versions.sort(key=lambda x: int(x), reverse=True)
        for v in versions:
            try:
                sec = client.secrets.kv.v2.read_secret_version(
                    path=VAULT_KEK_PATH, version=int(v), raise_on_deleted_version=False
                )
                if sec and "data" in sec and "data" in sec["data"] and "kek_hex" in sec["data"]["data"]:
                    keks.append(bytes.fromhex(sec["data"]["data"]["kek_hex"]))
            except Exception:
                pass
    except Exception as exc:
        logger.debug("No se pudieron leer versiones históricas de Vault: %s", exc)
    keks.append(DEFAULT_FALLBACK_KEK)
    return keks


def get_or_create_kek() -> bytes:
    """Obtiene la KEK maestra desde HashiCorp Vault, o la genera e inicializa si no existe."""
    try:
        secret_data = read_secret(VAULT_KEK_PATH)
        if secret_data and "kek_hex" in secret_data:
            return bytes.fromhex(secret_data["kek_hex"])
    except Exception as exc:
        logger.warning("No se pudo leer KEK de Vault (%s). Verificando si podemos escribirla...", exc)

    # Si no existe en Vault o fallo la lectura, intentar generar y persistir en Vault
    try:
        new_kek = AESGCM.generate_key(bit_length=256)
        write_secret(VAULT_KEK_PATH, {"kek_hex": new_kek.hex()})
        logger.info("Nueva KEK maestra generada y persistida exitosamente en Vault.")
        return new_kek
    except Exception as exc:
        logger.warning("Vault no disponible para persistir KEK: %s. Utilizando fallback local controlado.", exc)
        return DEFAULT_FALLBACK_KEK


def _encrypt_dek_with_kek(raw_dek: bytes, kek: bytes) -> str:
    """Cifra una DEK de clinica con la KEK maestra usando AES-256-GCM."""
    aesgcm = AESGCM(kek)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, raw_dek, None)
    return base64.b64encode(nonce + ct).decode("utf-8")


def _decrypt_dek_with_kek(encrypted_dek_b64: str, kek: bytes) -> bytes:
    """Descifra una DEK de clinica con la KEK maestra."""
    raw = base64.b64decode(encrypted_dek_b64.encode("utf-8"))
    nonce = raw[:12]
    ct = raw[12:]
    aesgcm = AESGCM(kek)
    return aesgcm.decrypt(nonce, ct, None)


async def get_or_create_clinic_dek(db: AsyncSession, clinic_id: str, version: int | None = None) -> tuple[bytes, int]:
    """Obtiene la DEK activa de una clinica o la genera si es el primer acceso (Envelope Encryption)."""
    kek = get_or_create_kek()

    if version is not None:
        stmt = select(ClinicEncryptionKey).where(
            ClinicEncryptionKey.clinic_id == clinic_id,
            ClinicEncryptionKey.key_version == version,
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row:
            try:
                raw_dek = _decrypt_dek_with_kek(row.encrypted_dek, kek)
                return raw_dek, row.key_version
            except Exception:
                # Fallback a KEKs históricas si hubo rotación sin re-wrap
                for hist_kek in _get_all_historical_keks():
                    try:
                        raw_dek = _decrypt_dek_with_kek(row.encrypted_dek, hist_kek)
                        # Auto-sanación: re-wrap con la KEK activa
                        row.encrypted_dek = _encrypt_dek_with_kek(raw_dek, kek)
                        await db.flush()
                        logger.info("Auto-sanada DEK para clínica %s versión %s", clinic_id, row.key_version)
                        return raw_dek, row.key_version
                    except Exception:
                        pass
                raise

    # Buscar la llave activa mas reciente
    stmt = (
        select(ClinicEncryptionKey)
        .where(ClinicEncryptionKey.clinic_id == clinic_id, ClinicEncryptionKey.is_active == True)
        .order_by(ClinicEncryptionKey.key_version.desc())
    )
    row = (await db.execute(stmt)).scalars().first()

    if row:
        try:
            raw_dek = _decrypt_dek_with_kek(row.encrypted_dek, kek)
            return raw_dek, row.key_version
        except Exception:
            # Fallback a KEKs históricas si hubo rotación sin re-wrap
            for hist_kek in _get_all_historical_keks():
                try:
                    raw_dek = _decrypt_dek_with_kek(row.encrypted_dek, hist_kek)
                    # Auto-sanación: re-wrap con la KEK activa
                    row.encrypted_dek = _encrypt_dek_with_kek(raw_dek, kek)
                    await db.flush()
                    logger.info("Auto-sanada DEK activa para clínica %s", clinic_id)
                    return raw_dek, row.key_version
                except Exception:
                    pass

    # Generar nueva DEK para esta clinica (version subsiguiente o version 1)
    next_ver = (row.key_version + 1) if row else 1
    raw_dek = AESGCM.generate_key(bit_length=256)
    encrypted_dek = _encrypt_dek_with_kek(raw_dek, kek)

    if row:
        row.is_active = False

    new_key = ClinicEncryptionKey(
        clinic_id=clinic_id,
        key_version=next_ver,
        encrypted_dek=encrypted_dek,
        is_active=True,
    )
    db.add(new_key)
    await db.flush()

    return raw_dek, next_ver


def encrypt_field(plaintext: str | None, dek: bytes) -> str | None:
    """Cifra un campo con AES-256-GCM y devuelve payload Base64 (nonce + ciphertext + tag)."""
    if plaintext is None:
        return None
    aesgcm = AESGCM(dek)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("utf-8")


def decrypt_field(ciphertext_b64: str | None, dek: bytes) -> str | None:
    """Descifra un campo en Base64 con AES-256-GCM."""
    if ciphertext_b64 is None:
        return None
    try:
        raw = base64.b64decode(ciphertext_b64.encode("utf-8"))
        nonce = raw[:12]
        ct = raw[12:]
        aesgcm = AESGCM(dek)
        pt = aesgcm.decrypt(nonce, ct, None)
        return pt.decode("utf-8")
    except Exception as exc:
        logger.error("Error al descifrar campo: %s", exc)
        return "[ERROR_DECRYPTION]"


async def rotate_clinic_dek(db: AsyncSession, clinic_id: str) -> int:
    """Genera una nueva version de DEK para la clinica, permitiendo rotacion progresiva."""
    kek = get_or_create_kek()
    stmt = (
        select(ClinicEncryptionKey)
        .where(ClinicEncryptionKey.clinic_id == clinic_id)
        .order_by(ClinicEncryptionKey.key_version.desc())
    )
    latest = (await db.execute(stmt)).scalars().first()
    new_version = (latest.key_version + 1) if latest else 1

    # Desactivar llaves anteriores
    if latest:
        latest.is_active = False

    raw_dek = AESGCM.generate_key(bit_length=256)
    encrypted_dek = _encrypt_dek_with_kek(raw_dek, kek)

    new_key = ClinicEncryptionKey(
        clinic_id=clinic_id,
        key_version=new_version,
        encrypted_dek=encrypted_dek,
        is_active=True,
    )
    db.add(new_key)
    await db.flush()
    return new_version


async def rewrap_deks_with_new_kek(db: AsyncSession, old_kek: bytes, new_kek: bytes) -> int:
    """Re-cifra todas las DEKs en base de datos con una nueva KEK (Rotacion de KEK sin alterar los historiales)."""
    stmt = select(ClinicEncryptionKey)
    keys = list((await db.execute(stmt)).scalars().all())
    count = 0
    hist_keks = None
    for k in keys:
        raw_dek = None
        try:
            raw_dek = _decrypt_dek_with_kek(k.encrypted_dek, old_kek)
        except Exception:
            if hist_keks is None:
                hist_keks = _get_all_historical_keks()
            for hk in hist_keks:
                try:
                    raw_dek = _decrypt_dek_with_kek(k.encrypted_dek, hk)
                    break
                except Exception:
                    pass

        if raw_dek:
            k.encrypted_dek = _encrypt_dek_with_kek(raw_dek, new_kek)
            count += 1
    await db.flush()
    return count


async def rotate_kek_master(db: AsyncSession, new_kek: bytes | None = None) -> bytes:
    """Rota la KEK maestra en Vault y re-cifra todas las DEKs en base de datos."""
    old_kek = get_or_create_kek()
    if new_kek is None:
        new_kek = AESGCM.generate_key(bit_length=256)

    await rewrap_deks_with_new_kek(db, old_kek, new_kek)
    try:
        write_secret(VAULT_KEK_PATH, {"kek_hex": new_kek.hex()})
        logger.info("KEK maestra rotada y persistida exitosamente en Vault.")
    except Exception as exc:
        logger.warning("No se pudo escribir nueva KEK en Vault: %s", exc)
    return new_kek

