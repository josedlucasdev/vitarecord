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
          "Access-Control-Allow-Origin": request.headers.get("Origin") || "*",
          "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Clinic-ID, X-Requested-With",
          "Access-Control-Allow-Credentials": "true",
          "Access-Control-Max-Age": "86400",
        },
      });
    }

    // 3. Reenviar petición hacia el origen backend en Docker (Render o servidor propio)
    const backendOrigin = (env.BACKEND_ORIGIN_URL || "https://vitarecord-backend.onrender.com").replace(/\/$/, "");
    const targetUrl = new URL(url.pathname + url.search, backendOrigin);

    // Clonar cabeceras y añadir metadatos de Cloudflare para el backend
    const forwardHeaders = new Headers(request.headers);
    forwardHeaders.set("X-Forwarded-Host", url.host);
    forwardHeaders.set("X-Forwarded-Proto", url.protocol.replace(":", ""));
    forwardHeaders.set("X-Real-IP", request.headers.get("CF-Connecting-IP") || "");

    try {
      const response = await fetch(targetUrl.toString(), {
        method: request.method,
        headers: forwardHeaders,
        body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
        redirect: "follow",
      });

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
          message: "No se pudo establecer conexión con el backend en contenedor.",
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
