# Guía de Despliegue en Cloudflare: Backend API y Almacenamiento R2

Esta guía contiene los pasos exactos para configurar tu subdominio `app.vitarecord.com`, desplegar el Worker de Cloudflare y conectar el almacenamiento de objetos **Cloudflare R2** para eliminar el almacenamiento local de archivos.

---

## 1. Configuración de Cloudflare R2 (Almacenamiento de Archivos)

Cloudflare R2 es un almacenamiento de objetos 100% compatible con la API de Amazon S3, sin costos de transferencia saliente (egress fees gratuitos).

### Paso 1: Crear el Bucket en Cloudflare
1. Entra a tu dashboard de [Cloudflare](https://dash.cloudflare.com/).
2. En el menú lateral izquierdo, haz clic en **R2** (o **R2 Storage**).
3. Haz clic en el botón azul **Create bucket**.
4. Nómbralo: `vitarecord-storage` (o el nombre que elijas) y selecciona ubicación automática (**Automatic**).
5. Haz clic en **Create Bucket**.

### Paso 2: Generar Credenciales de Acceso S3 (API Tokens)
1. En la página principal de **R2**, en el panel derecho haz clic en **Manage R2 API Tokens**.
2. Haz clic en **Create API Token**.
3. Configura:
   - **Token name:** `vitarecord-backend-token`
   - **Permissions:** Selecciona **Admin Read & Write** (o **Object Read & Write**).
   - **TTL:** Forever (o según tu política de rotación).
4. Haz clic en **Create API Token**.
5. **Copia y guarda inmediatamente**:
   - **Access Key ID**
   - **Secret Access Key**
   - **Account ID** (aparece en la URL de endpoint: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`)

### Paso 3: (Opcional pero recomendado) Habilitar Dominio Público R2
Si deseas que las imágenes de perfil y documentos públicos se sirvan directamente vía CDN ultra-rápido:
1. En la configuración de tu bucket `vitarecord-storage`, ve a la pestaña **Settings**.
2. En la sección **Public Access**:
   - Puedes conectar un dominio personalizado (ej. `media.vitarecord.com`), O
   - Habilitar **R2.dev subdomain** (ej. `https://pub-xxxxxx.r2.dev`).

### Paso 4: Configurar Variables de Entorno en tu Backend (Render / Docker)
En el panel de Render.com (o en tu archivo `.env` de producción), agrega las siguientes variables de entorno:

```env
R2_ACCOUNT_ID=tu_account_id_de_cloudflare
R2_ACCESS_KEY_ID=tu_access_key_id
R2_SECRET_ACCESS_KEY=tu_secret_access_key
R2_BUCKET_NAME=vitarecord-storage
# Opcional: si conectaste dominio público o habilitaste pub-xxx.r2.dev
R2_PUBLIC_URL=https://media.vitarecord.com
```

> **Estructura Organizada en R2 implementada:**
> - `avatars/patients/{patient_id}.{ext}`
> - `avatars/doctors/{doctor_id}.{ext}`
> - `avatars/dependents/{dependent_id}.{ext}`
> - `medical_records/{clinic_id}/{record_id}/{uuid}_{filename}`
> - `prescriptions/{clinic_id}/{prescription_code}.pdf`

---

## 2. Despliegue Automático con GitHub Actions (CI/CD)

Ya hemos configurado el flujo automatizado en:
[`.github/workflows/deploy-worker.yml`](file:///Volumes/M2STORAGE/WorkSpace/intimasalud/appcitas/.github/workflows/deploy-worker.yml)

Cada vez que hagas `git push origin main`, GitHub Actions compilará y desplegará tu Worker en Cloudflare automáticamente.

### Pasos para activar el despliegue automático:
1. En tu repositorio de GitHub, ve a **Settings** -> **Secrets and variables** -> **Actions**.
2. Agrega los siguientes **Repository secrets**:
   - `CLOUDFLARE_API_TOKEN`: Ve a tu panel de Cloudflare -> **My Profile** -> **API Tokens** -> **Create Token** -> Usa la plantilla **Edit Cloudflare Workers** -> copia el token.
   - `CLOUDFLARE_ACCOUNT_ID`: Tu Account ID de Cloudflare (aparece en la barra lateral derecha del dashboard de Workers o en R2).
3. ¡Listo! Cualquier cambio que envíes a `main` dentro de `cloudflare/` activará el despliegue sin que tengas que hacer nada manual.

---

## 3. Cómo Apuntar tu Subdominio al Worker en Cloudflare

Como tu dominio `vitarecord.com` ya fue comprado y gestionado dentro de Cloudflare, apuntar el subdominio es inmediato.

> [!NOTE]
> Tu frontend Quasar SPA continúa intacto en **`app.vitarecord.com`** (desplegado a cPanel).
> Tu API backend responderá exclusivamente a través de **`api.vitarecord.com`**.

### Método Recomendado: Cloudflare Custom Domains (Automático)
1. Ve a tu panel de Cloudflare -> **Workers & Pages**.
2. Haz clic en tu worker `vitarecord-api-gateway`.
3. Ve a la pestaña **Settings** -> **Domains & Routes** (o **Triggers**).
4. En la sección **Custom Domains**, haz clic en **Add Custom Domain**.
5. Escribe tu subdominio:
   - `api.vitarecord.com`
6. Haz clic en **Add Custom Domain**.
7. Cloudflare creará automáticamente el registro DNS, el certificado SSL y conectará el tráfico hacia tu Worker en segundos.

### Método Alternativo: Rutas de Zona (Routes)
Si prefieres usar la configuración definida en `wrangler.jsonc`:
1. En **Workers & Pages** -> `vitarecord-api-gateway` -> **Settings** -> **Routes** -> **Add route**.
2. Ruta: `api.vitarecord.com/*`, Zona: `vitarecord.com`.
3. En **DNS** -> **Records**, asegúrate de que el registro DNS para `api` tenga la **nube naranja (Proxied)** activada.

---

## 4. Resumen de Opciones para Contenedores Docker

1. **Backend en Render + Edge Worker en Cloudflare (Recomendada ahora mismo):**
   - Tu contenedor Docker corre estable en Render con su base de datos y Redis.
   - El Worker en `api.vitarecord.com` recibe el tráfico en el Edge de Cloudflare y lo enruta al contenedor.
   - Los archivos se guardan directamente en Cloudflare R2 sin tocar el disco local de Render.
2. **Backend en VPS Propio + Cloudflare Tunnel (`cloudflared`):**
   - Si más adelante decides migrar fuera de Render a un VPS (como Hetzner, AWS o DigitalOcean), puedes ejecutar `docker compose up -d` y levantar un contenedor `cloudflare/cloudflared`. El túnel conecta directamente a `api.vitarecord.com` sin abrir puertos de red.
