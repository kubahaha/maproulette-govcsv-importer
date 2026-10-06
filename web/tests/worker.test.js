import test from "node:test";
import assert from "node:assert/strict";
import { handleOverpassProxy } from "../../worker/overpass-proxy.js";

const localOrigin = "http://localhost:4173";

test("Overpass proxy answers preflight for local development origin", async () => {
  const response = await handleOverpassProxy(new Request("https://worker.test/api/overpass", {
    method: "OPTIONS",
    headers: { Origin: localOrigin },
  }));
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("Access-Control-Allow-Origin"), localOrigin);
  assert.match(response.headers.get("Access-Control-Allow-Methods"), /POST/);
});

test("Overpass proxy rejects origins outside the allowlist", async () => {
  const response = await handleOverpassProxy(new Request("https://worker.test/api/overpass", {
    method: "POST",
    headers: { Origin: "https://untrusted.example", "Content-Type": "application/x-www-form-urlencoded" },
    body: "data=%5Bout%3Ajson%5D%3Bout%3B",
  }));
  assert.equal(response.status, 403);
});

test("Overpass proxy forwards form body and returns upstream response with CORS", async () => {
  let capturedUrl;
  let capturedBody;
  const response = await handleOverpassProxy(new Request("https://worker.test/api/overpass", {
    method: "POST",
    headers: { Origin: localOrigin, "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
    body: "data=%5Bout%3Ajson%5D%3Bout%3B",
  }), async (url, options) => {
    capturedUrl = url;
    capturedBody = new TextDecoder().decode(options.body);
    return new Response('{"elements":[]}', { status: 200, headers: { "Content-Type": "application/json" } });
  });
  assert.equal(capturedUrl, "https://overpass-api.de/api/interpreter");
  assert.equal(capturedBody, "data=%5Bout%3Ajson%5D%3Bout%3B");
  assert.equal(response.headers.get("Access-Control-Allow-Origin"), localOrigin);
  assert.deepEqual(await response.json(), { elements: [] });
});