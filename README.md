# appcitas — ÍntimaSalud

Implementación en curso según `plan/plan.md`. Estado actual: **Módulo 0 completo
(infraestructura contenerizada)** + **arranque de Módulo 1** (modelos base,
autenticación JWT/Argon2/TOTP, health checks). Los módulos 2 en adelante
(motor de citas con filas mutex, verificación de médicos, emergencias,
notificaciones multicanal, cifrado PHI, observabilidad completa) están
en el roadmap de `plan/plan.md` y se implementan de forma incremental.

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
