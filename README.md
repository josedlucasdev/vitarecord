# VitaRecord (anteriormente appcitas) — Plataforma Médica Integral

Estado actual de implementación: **Módulos 0 al 6 COMPLETADOS** con suite integral de 108 tests pasando al 100%:
- **Módulo 0 & 1:** Infraestructura contenerizada, modelos SQLAlchemy, autenticación JWT con Argon2id, TOTP MFA, control de acceso RBAC por clínica y health/readiness checks.
- **Módulo 1.5 & 2:** Directorio médico público, perfiles profesionales, agendamiento de citas con cerrojos distribuidos mutex en Redis (prevención de sobreventa), disponibilidad física de consultorios y reglas de fair-use / ciclo de vida (`CHECKED_IN`, `IN_CONSULTATION`, `NO_SHOW`, `RESCHEDULED`).
- **Módulo 3:** Dependientes y núcleo familiar, transición legal de minoridad a mayoría de edad (emancipación a los 18 años con suspensión de acceso del titular a nuevas notas clínicas), consentimientos inter-clínica (`patient_consent_grants`) y registro manual de pagos/cuadre de caja.
- **Módulo 4:** Urgencia médica remota, botón SOS con descargo legal, escalamiento multicanal con SLAs en cascada y WebSockets en tiempo real hacia la Torre de Control.
- **Módulo 5:** Historias clínicas con Envelope Encryption (AES-256-GCM + DEK por clínica y rotación de KEK en Vault), recetas médicas criptográficas con verificación por código QR, optimización de anexos a WebP con descarte de metadatos EXIF y pistas de auditoría inmutable de toda lectura (`action=READ`).
- **Módulo 6:** Notificaciones multicanal (WhatsApp Business Cloud API, Twilio SMS/Voz, FCM Push y Email) con fallback automático y reintentos, webhooks bidireccionales y worker dedicado en segundo plano (`appcitas_worker`).

## Cómo levantar el entorno

```bash
cp .env.example .env   # completar si se quiere sobreescribir algún valor de desarrollo
npm run dev             # docker compose up --build
```

Servicios expuestos en el host:

- Landing (Astro): http://localhost:4321
- Frontend (Quasar): http://localhost:9000
- Backend (FastAPI + Swagger): http://localhost:8000/docs
- Health / readiness: http://localhost:8000/health , http://localhost:8000/readiness
- MySQL: localhost:3306
- Redis: localhost:6379
- Almacenamiento S3-compatible (S3Proxy): API en localhost:9002. No tiene
  consola web — los archivos subidos quedan visibles directamente en
  `appcitas/_data/storage/` (bind mount al host). Se usa S3Proxy en vez de
  MinIO porque MinIO dejó de distribuir imágenes Docker gratuitas en
  octubre de 2025 (`docker pull minio/minio` responde `pull access denied`).
- Mailpit (correo local): http://localhost:8025
- Vault (modo dev): http://localhost:8200
- Worker de fondo (`appcitas_worker`): ejecuta schedulers periódicos de recordatorios, escalamiento de urgencias y emancipación de dependientes con cerrojos distribuidos Redis.

Observabilidad opcional (Prometheus/Grafana, no se levanta por defecto):

```bash
npm run dev:observability
```

## Migraciones de base de datos

Este proyecto usa Alembic con un motor **síncrono** (PyMySQL) exclusivamente
para generar/aplicar migraciones; el runtime de la aplicación sigue usando el
driver asíncrono `asyncmy` (ver `backend/alembic/env.py` y `plan/plan.md`
sección 2.A). La carpeta `alembic/versions` está vacía a propósito: la
primera migración se genera contra una base de datos real ya corriendo, para
que Alembic autogenere el esquema completo a partir de `app/models/`:

```bash
npm run dev                      # con el stack ya corriendo
npm run makemigration -- "initial schema"
npm run migrate
```

## Nota sobre presigned URLs (S3Proxy / S3)

`backend/app/core/config.py` define dos endpoints distintos a propósito:

- `S3_ENDPOINT_URL` (`http://storage:80`): el que usa el backend para hablar
  con el storage **dentro** de la red de Docker.
- `S3_PUBLIC_ENDPOINT_URL` (`http://localhost:9002`): el que debe poder
  resolver el **navegador** del usuario. Como la firma SigV4 incluye el host
  como parte de la firma, `storage_service.py` (Módulo 5, aún no
  implementado) debe generar las presigned URLs con un cliente `boto3`
  configurado con `S3_PUBLIC_ENDPOINT_URL`, nunca con `S3_ENDPOINT_URL` —
  de lo contrario el enlace que reciba el paciente/médico no será alcanzable
  desde su navegador.

## Qué falta (ver plan/plan.md, sección "ROADMAP")

- Módulo 1.5: panel y endpoints de verificación de matrícula profesional.
- Módulo 2: consultorios físicos, filas mutex `doctor_schedule_locks` /
  `room_schedule_locks` y motor de disponibilidad.
- Módulo 3: motor de citas, dependientes familiares, consentimientos, pagos.
- Módulo 4: urgencia médica remota con escalamiento multicanal.
- Módulo 5: expediente clínico cifrado (envelope encryption) y recetas QR.
- Módulo 6: servicio de notificaciones multicanal (WhatsApp/SMS/Voz/Push/Email).
- Módulo 7-8: pruebas de carga reales, compilación nativa Capacitor,
  observabilidad completa, gestión de secretos en producción y cumplimiento
  normativo por país.
