"""Servicio de almacenamiento compatible con S3 (S3Proxy / AWS S3 / Cloudflare R2).

Maneja almacenamiento de avatares, anexos médicos y documentos mediante
subida directa y URLs prefirmadas seguras.
"""

import logging
import uuid
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger("storage")


class StorageService:
    def __init__(self):
        self.endpoint_url = settings.active_s3_endpoint_url
        self.public_endpoint_url = settings.active_s3_public_endpoint_url
        self.access_key = settings.active_s3_access_key
        self.secret_key = settings.active_s3_secret_key
        self.bucket_name = settings.active_s3_bucket

        # Cliente para llamadas directas internas desde backend a storage (Docker / R2 API)
        self.internal_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version="s3v4"),
            region_name="auto" if settings.R2_ACCOUNT_ID else "us-east-1",
        )

        # Cliente para generar Presigned URLs firmadas para el host publico del navegador
        self.public_signer = boto3.client(
            "s3",
            endpoint_url=self.public_endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version="s3v4"),
            region_name="auto" if settings.R2_ACCOUNT_ID else "us-east-1",
        )

    def ensure_bucket(self) -> None:
        """Crea el bucket si no existe aun en el almacenamiento (usado en dev/S3Proxy)."""
        try:
            self.internal_client.head_bucket(Bucket=self.bucket_name)
        except Exception:
            try:
                self.internal_client.create_bucket(Bucket=self.bucket_name)
                logger.info("Bucket S3 '%s' creado exitosamente.", self.bucket_name)
            except Exception as exc:
                logger.warning("No se pudo asegurar bucket S3 '%s': %s", self.bucket_name, exc)

    def upload_file(
        self,
        content: bytes,
        s3_key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Sube un archivo directamente a Cloudflare R2 / S3 y retorna su s3_key."""
        self.ensure_bucket()
        try:
            self.internal_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                ContentType=content_type,
            )
            return s3_key
        except Exception as exc:
            logger.error("Error al subir archivo a S3/R2 con clave '%s': %s", s3_key, exc)
            raise

    def get_file(self, s3_key: str) -> tuple[bytes, str] | None:
        """Obtiene el contenido binario y Content-Type de un archivo desde S3/R2."""
        try:
            resp = self.internal_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = resp["Body"].read()
            content_type = resp.get("ContentType", "application/octet-stream")
            return content, content_type
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404", "NotFound"):
                return None
            logger.error("Error al obtener archivo S3/R2 '%s': %s", s3_key, e)
            raise
        except Exception as exc:
            logger.error("Error general al obtener archivo S3/R2 '%s': %s", s3_key, exc)
            return None

    def delete_file(self, s3_key: str) -> bool:
        """Elimina un objeto de S3/R2."""
        try:
            self.internal_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except Exception as exc:
            logger.error("Error al eliminar archivo S3/R2 '%s': %s", s3_key, exc)
            return False

    def generate_presigned_upload_url(
        self, s3_key: str, content_type: str, expires_in: int = 900
    ) -> dict:
        """Genera una URL prefirmada PUT para que el frontend suba el archivo directamente."""
        self.ensure_bucket()
        try:
            url = self.public_signer.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": s3_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
                HttpMethod="PUT",
            )
            return {"upload_url": url, "s3_key": s3_key, "expires_in": expires_in}
        except Exception as exc:
            logger.error("Error al generar presigned upload URL: %s", exc)
            raise

    def generate_presigned_download_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Genera una URL prefirmada GET para visualización/descarga segura."""
        try:
            return self.public_signer.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expires_in,
            )
        except Exception as exc:
            logger.error("Error al generar presigned download URL: %s", exc)
            raise

    def get_file_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Retorna la URL pública directa (si existe R2_PUBLIC_URL) o una presigned URL."""
        if settings.R2_PUBLIC_URL:
            return f"{settings.R2_PUBLIC_URL.rstrip('/')}/{s3_key}"
        return self.generate_presigned_download_url(s3_key, expires_in=expires_in)

    # -------------------------------------------------------------
    # Taxonomía y Generadores de Claves Organizadas
    # -------------------------------------------------------------
    @staticmethod
    def build_avatar_key(entity_type: str, entity_id: str, ext: str) -> str:
        """Estructura: avatars/{patients|doctors|dependents}/{entity_id}.{ext}"""
        clean_ext = ext.lstrip(".")
        return f"avatars/{entity_type}/{entity_id}.{clean_ext}"

    @staticmethod
    def build_medical_record_attachment_key(clinic_id: str, record_id: str, filename: str) -> str:
        """Estructura: medical_records/{clinic_id}/{record_id}/{uuid}_{filename}"""
        file_ext = filename.split(".")[-1] if "." in filename else "dat"
        safe_uuid = uuid.uuid4().hex
        return f"medical_records/{clinic_id}/{record_id}/{safe_uuid}.{file_ext}"

    @staticmethod
    def build_prescription_pdf_key(clinic_id: str, prescription_code: str) -> str:
        """Estructura: prescriptions/{clinic_id}/{prescription_code}.pdf"""
        return f"prescriptions/{clinic_id}/{prescription_code}.pdf"


storage_service = StorageService()
