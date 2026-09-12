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

    CORS_ORIGINS: list[str] = ["http://localhost:9000"]
    FRONTEND_URL: str = "http://localhost:9000"

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

    SENTRY_DSN: str | None = None


settings = Settings()
