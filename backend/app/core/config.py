from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "IntimaSalud"
    ENVIRONMENT: str = "development"

    # Runtime asincrono (asyncmy) para la aplicacion.
    DATABASE_URL: str = "mysql+asyncmy://appcitas:appcitas_dev_only@mysql:3306/appcitas"
    # Motor sincrono (PyMySQL) exclusivo para Alembic (ver alembic/env.py).
    DATABASE_SYNC_URL: str = "mysql+pymysql://appcitas:appcitas_dev_only@mysql:3306/appcitas"

    REDIS_URL: str = "redis://redis:6379/0"

    JWT_SECRET_KEY: str = "dev-only-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    CORS_ORIGINS: str | list[str] = [
        "http://localhost:9000",
        "https://app.vitarecord.com",
        "https://vitarecord.com",
    ]

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    FRONTEND_URL: str = "https://app.vitarecord.com"

    VAULT_ADDR: str = "http://vault:8200"
    VAULT_TOKEN: str = "devroot_dev_only"

    # Endpoint INTERNO: el que usa el backend para hablar con el storage
    # dentro de la red de Docker (S3Proxy en desarrollo; AWS S3/R2 en
    # produccion). MinIO se descarto como dependencia de desarrollo porque
    # dejo de distribuir imagenes Docker gratuitas (oct-2025) - ver
    # plan/plan.md seccion 0.
    S3_ENDPOINT_URL: str = "http://storage:80"
    # Endpoint PUBLICO: el que debe resolver el NAVEGADOR del usuario para
    # usar una presigned URL. Con S3-compatible + SigV4, el host forma parte
    # de la firma, asi que storage_service.py (Modulo 5) debe generar las
    # presigned URLs con un cliente boto3 configurado con ESTE endpoint,
    # nunca con S3_ENDPOINT_URL (que solo es alcanzable desde dentro de la
    # red de Docker, no desde el navegador).
    S3_PUBLIC_ENDPOINT_URL: str = "http://localhost:9002"
    S3_ACCESS_KEY: str = "devaccesskey"
    S3_SECRET_KEY: str = "devsecretkey_dev_only"
    S3_BUCKET_NAME: str = "appcitas-attachments"

    SMTP_HOST: str = "mailtrap"
    SMTP_PORT: int = 1025

    # Meta WhatsApp Cloud API
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v20.0"
    WHATSAPP_PHONE_NUMBER_ID: str = "101526655923922"
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = "110504608346732"
    WHATSAPP_ACCESS_TOKEN: str = "EAATmvZCRxNm8BSRvVzjhRsLQuMBM7uf8mcMFGW1zuEDlbNLaIZBgT6QTIYuSae4YpuYlo6NEs9NB4z7rYtF8AnfAJJL7ppZC5zBDv2o4qhs9FJe6PbnKZBicGNfK1yV0zhXARQJCorgStSaUsy92S5fqRqN3NTgvVc01tWycOyaWguKQbKAYaRTQhxhXoBP5lSuly0e6CtBRr1ZChvgtyePOSJ1ZAWDhhRGMAlXRVxI2wUZAiS8phohZBkRrZBGT5bW0ThlTgoZB7ZAc3P5T2VXF8EgrojPTlfjYqJD4ygWmwZDZD"
    WHATSAPP_VERIFY_TOKEN: str = "intimasalud_dev_webhook_verify_token"

    # Twilio SMS & Voice
    TWILIO_ACCOUNT_SID: str = "dev_twilio_sid"
    TWILIO_AUTH_TOKEN: str = "dev_twilio_token"
    TWILIO_FROM_NUMBER: str = "+15005550006"

    # Push FCM (Firebase Cloud Messaging HTTP v1 API)
    FIREBASE_CREDENTIALS_FILE: str | None = "/app/firebase-credentials.json"
    FCM_SERVER_KEY: str | None = "dev_fcm_server_key"
    FCM_PROJECT_ID: str = "vita-record"
    FCM_API_URL: str = "https://fcm.googleapis.com/fcm/send"

    # Facebook Login
    FACEBOOK_APP_ID: str = "1150121370684613"
    FACEBOOK_APP_SECRET: str = "d4797ebcd90c781fc0b5c4cc7bec3dc4"

    # Google Sign-In
    GOOGLE_CLIENT_ID: str = "398180197268-bqtm2q48fp00vra1p5ar9uop02ed0p4u.apps.googleusercontent.com"

    # Recordatorios automáticos
    REMINDER_CHECK_INTERVAL_SECONDS: int = 60

    SENTRY_DSN: str | None = None


settings = Settings()

