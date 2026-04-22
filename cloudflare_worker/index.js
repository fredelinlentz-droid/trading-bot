/**
 * Cloudflare Worker — Proxy sécurisé pour le Trading Bot API
 *
 * Déploiement :
 *   npm install -g wrangler
 *   wrangler login
 *   wrangler secret put API_SECRET
 *   wrangler secret put BACKEND_URL
 *   wrangler deploy
 */

export default {
  async fetch(request, env) {
    const url    = new URL(request.url);
    const method = request.method;

    // ── CORS Preflight ──────────────────────────────────
    if (method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin":  "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Authorization, Content-Type",
          "Access-Control-Max-Age":       "86400",
        },
      });
    }

    // ── Route publique : health check ────────────────────
    if (url.pathname === "/health") {
      return jsonResponse({ status: "ok", worker: "trading-bot", ts: Date.now() });
    }

    // ── Authentification ────────────────────────────────
    const auth = request.headers.get("Authorization");
    if (!auth || auth !== `Bearer ${env.API_SECRET}`) {
      return jsonResponse({ error: "Non autorisé" }, 401);
    }

    // ── Rate limiting simple (KV Store) ─────────────────
    const clientIP  = request.headers.get("CF-Connecting-IP") || "unknown";
    const rateLimitKey = `rate:${clientIP}`;

    if (env.KV) {
      const count = parseInt(await env.KV.get(rateLimitKey) || "0");
      if (count >= 60) {
        return jsonResponse({ error: "Trop de requêtes (max 60/min)" }, 429);
      }
      await env.KV.put(rateLimitKey, String(count + 1), { expirationTtl: 60 });
    }

    // ── Proxy vers le backend Python ─────────────────────
    const backendURL = env.BACKEND_URL || "http://localhost:8000";
    const targetURL  = backendURL + url.pathname + url.search;

    try {
      const backendResp = await fetch(targetURL, {
        method:  method,
        headers: {
          "Content-Type":  "application/json",
          "Authorization": `Bearer ${env.INTERNAL_SECRET || env.API_SECRET}`,
          "X-Forwarded-For": clientIP,
        },
        body: method !== "GET" ? request.body : undefined,
        // Timeout via signal (Cloudflare supporte)
        signal: AbortSignal.timeout(10000),
      });

      const data = await backendResp.text();

      return new Response(data, {
        status: backendResp.status,
        headers: {
          "Content-Type":                "application/json",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control":               url.pathname === "/signals" ? "max-age=60" : "no-cache",
        },
      });
    } catch (err) {
      return jsonResponse({ error: "Backend indisponible", detail: err.message }, 503);
    }
  },
};

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type":                "application/json",
      "Access-Control-Allow-Origin": "*",
    },
  });
}
