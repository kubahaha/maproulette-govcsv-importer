const ALLOWED_ORIGINS = new Set([
  "https://kubahaha.github.io",
  "http://localhost:4173",
]);
const OVERPASS_URL = "https://overpass-api.de/api/interpreter";
const MAX_QUERY_BYTES = 1_000_000;

export async function handleOverpassProxy(request, upstreamFetch = fetch) {
  const origin = request.headers.get("Origin");
  if (!ALLOWED_ORIGINS.has(origin)) {
    return new Response("Origin not allowed", { status: 403 });
  }

  const corsHeaders = {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };

  if (request.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }
  if (request.method !== "POST") {
    return new Response("Method not allowed", { status: 405, headers: corsHeaders });
  }
  if (!request.headers.get("Content-Type")?.startsWith("application/x-www-form-urlencoded")) {
    return new Response("Expected form-encoded Overpass query", { status: 415, headers: corsHeaders });
  }

  const body = await request.arrayBuffer();
  if (body.byteLength > MAX_QUERY_BYTES) {
    return new Response("Query too large", { status: 413, headers: corsHeaders });
  }

  try {
    const upstream = await upstreamFetch(OVERPASS_URL, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
      body,
      signal: AbortSignal.timeout(25_000),
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        ...corsHeaders,
        "Content-Type": upstream.headers.get("Content-Type") ?? "application/json",
      },
    });
  } catch {
    return new Response("Overpass request failed or timed out", { status: 502, headers: corsHeaders });
  }
}

export default {
  fetch(request) {
    const url = new URL(request.url);
    if (url.pathname !== "/api/overpass") {
      return new Response("Not found", { status: 404 });
    }
    return handleOverpassProxy(request);
  },
};