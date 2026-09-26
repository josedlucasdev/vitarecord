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
    # Ventana en la que se cuentan intentos fallidos (plan 2.B.9: 5 en 15 min).
    LOGIN_ATTEMPT_WINDOW_MINUTES: int = 15
    # Intentos por IP (todas las cuentas) antes de responder 429.
    LOGIN_MAX_ATTEMPTS_PER_IP: int = 50
    # Numero de bloqueos consecutivos a partir del cual se exige CAPTCHA.
    LOGIN_CAPTCHA_AFTER_LOCKOUTS: int = 2
    # Cloudflare Turnstile (CAPTCHA). Si no se configura, el paso de CAPTCHA
    # se omite y solo aplica el bloqueo temporal.
    TURNSTILE_SECRET_KEY: str | None = None

    # MFA obligatorio (plan 2.B.9). Los roles listados no pueden operar sin
    # MFA activo: solo pueden usar los endpoints de configuracion de MFA.
    # Por defecto activo; puede desactivarse SOLO en desarrollo/tests.
    MFA_ENFORCEMENT_ENABLED: bool = True
    MFA_REQUIRED_ROLES: list[str] = ["SUPERADMIN", "MODERATOR", "COMPLIANCE_REVIEWER", "CLINIC_ADMIN", "DOCTOR"]

    # Rate limiting por tenant (proteccion "noisy neighbor", plan 2.B.1).
    TENANT_RATE_LIMIT_PER_SECOND: int = 50

    # Emulacion de login social con tokens "dev_fb_*" / "dev_google_*".
    # SOLO para desarrollo local y tests; nunca debe activarse en produccion.
    ALLOW_DEV_SOCIAL_LOGIN: bool = False

    CORS_ORIGINS: str | list[str] = [
        "http://localhost:9000",
        "http://localhost:4321",
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

    # Origenes adicionales permitidos por expresion regular (anclada: debe
    # coincidir con el origen COMPLETO). Cubre subdominios de vitarecord.com,
    # los despliegues de vista previa de Cloudflare Pages de los proyectos
    # vitarecord-app / vitarecord-web y localhost en desarrollo.
    CORS_ORIGIN_REGEX: str = (
        r"https://([a-z0-9-]+\.)*vitarecord\.com"
        r"|https://([a-z0-9-]+\.)?vitarecord-(app|web)\.pages\.dev"
        r"|http://localhost(:\d+)?"
    )

    FRONTEND_URL: str = "https://app.vitarecord.com"

    VAULT_ADDR: str = "http://vault:8200"
    VAULT_TOKEN: str = "devroot_dev_only"

    # Configuración de Almacenamiento Compatible con S3 / Cloudflare R2
    R2_ACCOUNT_ID: str | None = None
    R2_ACCESS_KEY_ID: str | None = None
    R2_SECRET_ACCESS_KEY: str | None = None
    R2_BUCKET_NAME: str | None = None
    R2_PUBLIC_URL: str | None = None  # Ej: https://media.vitarecord.com o https://pub-xxx.r2.dev

    # Endpoint INTERNO: el que usa el backend para hablar con el storage
    # dentro de la red de Docker (S3Proxy en desarrollo; AWS S3/R2 en produccion).
    S3_ENDPOINT_URL: str = "http://storage:80"
    # Endpoint PUBLICO: el que debe resolver el NAVEGADOR del usuario para
    # usar una presigned URL.
    S3_PUBLIC_ENDPOINT_URL: str = "http://localhost:9002"
    S3_ACCESS_KEY: str = "devaccesskey"
    S3_SECRET_KEY: str = "devsecretkey_dev_only"
    S3_BUCKET_NAME: str = "appcitas-attachments"

    @property
    def active_s3_endpoint_url(self) -> str:
        if self.R2_ACCOUNT_ID:
            return f"https://{self.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        return self.S3_ENDPOINT_URL

    @property
    def active_s3_public_endpoint_url(self) -> str:
        if self.R2_PUBLIC_URL:
            return self.R2_PUBLIC_URL.rstrip("/")
        if self.R2_ACCOUNT_ID:
            return f"https://{self.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        return self.S3_PUBLIC_ENDPOINT_URL

    @property
    def active_s3_access_key(self) -> str:
        return self.R2_ACCESS_KEY_ID or self.S3_ACCESS_KEY

    @property
    def active_s3_secret_key(self) -> str:
        return self.R2_SECRET_ACCESS_KEY or self.S3_SECRET_KEY

    @property
    def active_s3_bucket(self) -> str:
        return self.R2_BUCKET_NAME or self.S3_BUCKET_NAME

    SMTP_HOST: str = "mailtrap"
    SMTP_PORT: int = 1025

    # Meta WhatsApp Cloud API
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v20.0"
    WHATSAPP_PHONE_NUMBER_ID: str = "101526655923922"
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = "110504608346732"
    # Secretos: NUNCA con valores reales en el codigo (plan 2.B.10). Se leen de
    # variables de entorno / Vault. Los valores "dev_*" activan el modo emulado.
    WHATSAPP_ACCESS_TOKEN: str = "dev_whatsapp_token"
    WHATSAPP_VERIFY_TOKEN: str = "dev_webhook_verify_token"
    # "App secret" de la app de Meta: firma X-Hub-Signature-256 de cada webhook.
    WHATSAPP_APP_SECRET: str = ""

    # Twilio SMS & Voice
    TWILIO_ACCOUNT_SID: str = "dev_twilio_sid"
    TWILIO_AUTH_TOKEN: str = "dev_twilio_token"
    TWILIO_FROM_NUMBER: str = "+15005550006"
    # URL publica exacta del webhook de Twilio (la firma X-Twilio-Signature se
    # calcula sobre ella). Si no se define se usa la URL de la peticion.
    TWILIO_WEBHOOK_URL: str | None = None

    # Push FCM (Firebase Cloud Messaging HTTP v1 API)
    FIREBASE_CREDENTIALS_FILE: str | None = "/app/firebase-credentials.json"
    FCM_SERVICE_ACCOUNT_JSON: str | None = None
    FCM_SERVER_KEY: str | None = "dev_fcm_server_key"
    FCM_PROJECT_ID: str = "vita-record"
    FCM_API_URL: str = "https://fcm.googleapis.com/fcm/send"

    # Facebook Login
    FACEBOOK_APP_ID: str = "1150121370684613"
    FACEBOOK_APP_SECRET: str = ""

    # Google Sign-In
    GOOGLE_CLIENT_ID: str = "398180197268-bqtm2q48fp00vra1p5ar9uop02ed0p4u.apps.googleusercontent.com"

    # Orquestador de escalamiento de urgencias (plan 2.B.7)
    EMERGENCY_DELIVERY_CONFIRM_SECONDS: int = 15
    EMERGENCY_DOCTOR_ACCEPT_TIMEOUT_SECONDS: int = 60
    EMERGENCY_MODERATOR_SLA_SECONDS: int = 120
    EMERGENCY_CHECK_INTERVAL_SECONDS: int = 5
    # Linea de respaldo global si la clinica no configuro la suya.
    EMERGENCY_BACKUP_PHONE: str | None = None
    # Reintentos de llamada a la linea de respaldo antes de dejar solo la alarma.
    EMERGENCY_BACKUP_MAX_CALLS: int = 3

    # Recordatorios automáticos
    REMINDER_CHECK_INTERVAL_SECONDS: int = 60

    # Telegram Support Bot
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ADMIN_CHAT_ID: str = ""

    # Firebase Realtime Database (Chat de soporte en tiempo real)
    FIREBASE_DATABASE_URL: str = "https://vita-record-default-rtdb.firebaseio.com"

    SENTRY_DSN: str | None = None

    def production_config_errors(self) -> list[str]:
        """Errores de configuracion que impiden arrancar en produccion."""
        if self.ENVIRONMENT != "production":
            return []
        errors = []
        if self.JWT_SECRET_KEY == "dev-only-change-me" or len(self.JWT_SECRET_KEY) < 32:
            errors.append("JWT_SECRET_KEY debe ser un secreto propio de al menos 32 caracteres")
        if self.ALLOW_DEV_SOCIAL_LOGIN:
            errors.append("ALLOW_DEV_SOCIAL_LOGIN no puede estar activo en produccion")
        if not self.MFA_ENFORCEMENT_ENABLED:
            errors.append("MFA_ENFORCEMENT_ENABLED no puede desactivarse en produccion")
        if self.WHATSAPP_VERIFY_TOKEN.startswith("dev_"):
            errors.append("WHATSAPP_VERIFY_TOKEN debe configurarse con un valor propio")
        if not self.WHATSAPP_APP_SECRET:
            errors.append("WHATSAPP_APP_SECRET es obligatorio para validar la firma de los webhooks de Meta")
        if self.VAULT_TOKEN == "devroot_dev_only":
            errors.append("VAULT_TOKEN no puede ser el token de desarrollo")
        return errors


settings = Settings()

