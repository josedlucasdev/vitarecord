/**
 * VitaRecord Cloudflare Worker - Edge API Gateway & Reverse Proxy
 *
 * Enruta las peticiones de app.vitarecord.com hacia el backend en contenedor Docker
 * inyectando cabeceras de seguridad, gestionando CORS y protegiendo el origen.
 */

export interface Env {
  BACKEND_ORIGIN_URL: string;
  ENVIRONMENT: string;
}

const ALLOWED_ORIGIN_RE =
  /^(https:\/\/([a-z0-9-]+\.)*vitarecord\.com|https:\/\/([a-z0-9-]+\.)?vitarecord-(app|web)\.pages\.dev|http:\/\/localhost(:\d+)?)$/;

function allowedOrigin(origin: string | null): string {
  return origin && ALLOWED_ORIGIN_RE.test(origin) ? origin : "https://app.vitarecord.com";
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    // 1. Healthcheck rápido en el Edge sin tocar el backend
    if (url.pathname === "/edge-health") {
      return new Response(
        JSON.stringify({
          status: "healthy",
          edge: "cloudflare-workers",
          timestamp: new Date().toISOString(),
          region: request.cf?.colo || "global",
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // 2. Preflight OPTIONS (CORS rápido en Edge)
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          // Solo se refleja el origen si esta en la lista permitida (mismo
          // criterio que CORS_ORIGIN_REGEX del backend); nunca "*" con credenciales.
          "Access-Control-Allow-Origin": allowedOrigin(request.headers.get("Origin")),
          "Vary": "Origin",
          "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Clinic-ID, X-Requested-With",
          "Access-Control-Allow-Credentials": "true",
          "Access-Control-Max-Age": "86400",
        },
      });
    }

    // 3. Reenviar petición hacia el origen backend configurado en Cloudflare DNS (VPS)
    try {
      const response = await fetch(request);

      // Añadir cabeceras de seguridad a la respuesta
      const responseHeaders = new Headers(response.headers);
      responseHeaders.set("X-Content-Type-Options", "nosniff");
      responseHeaders.set("X-Frame-Options", "DENY");
      responseHeaders.set("Referrer-Policy", "strict-origin-when-cross-origin");

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });
    } catch (err: any) {
      return new Response(
        JSON.stringify({
          error: "BackendUnavailable",
          message: "No se pudo establecer conexión con el backend en el VPS.",
          detail: err?.message || String(err),
        }),
        {
          status: 502,
          headers: { "Content-Type": "application/json" },
        }
      );
    }
  },
};
