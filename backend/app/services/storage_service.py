"""Servicio de almacenamiento compatible con S3 (S3Proxy / AWS S3 / Cloudflare R2) (plan/plan.md 2.B.8).

Maneja carga de anexos medicos mediante Presigned URLs efimeras.
"""

import logging
import boto3
from botocore.config import Config

from app.core.config import settings

logger = logging.getLogger("storage")


class StorageService:
    def __init__(self):
        # Cliente para llamadas directas internas desde backend a storage dentro de red Docker
        self.internal_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

        # Cliente para generar Presigned URLs firmadas para el host publico del navegador (localhost:9002)
        self.public_signer = boto3.client(
            "s3",
            endpoint_url=settings.S3_PUBLIC_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

        self.bucket_name = settings.S3_BUCKET_NAME

    def ensure_bucket(self) -> None:
        """Crea el bucket si no existe aun en el almacenamiento."""
        try:
            self.internal_client.head_bucket(Bucket=self.bucket_name)
        except Exception:
            try:
                self.internal_client.create_bucket(Bucket=self.bucket_name)
                logger.info("Bucket S3 '%s' creado exitosamente.", self.bucket_name)
            except Exception as exc:
                logger.warning("No se pudo asegurar bucket S3 '%s': %s", self.bucket_name, exc)

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
        """Genera una URL prefirmada GET para visualizacion/descarga segura."""
        try:
            return self.public_signer.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expires_in,
            )
        except Exception as exc:
            logger.error("Error al generar presigned download URL: %s", exc)
            raise


storage_service = StorageService()
