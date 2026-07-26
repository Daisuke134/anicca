// steel-cdp-client.test.js — the self-hosted steel-browser rail (§10.0-12). Routes pinned against
// steel-dev/steel-browser api/src/modules/sessions/sessions.routes.ts + steel-browser-plugin.ts
// (prefix "/v1"): GET /v1/health, POST /v1/sessions, POST /v1/sessions/:id/release. There is NO
// DELETE /v1/sessions — a test that asserted one would be pinning a route that does not exist.
// Run: node --test lib/steel-cdp-client.test.js
"use strict";
const { test } = require("node:test");
const assert = require("node:assert");
const { makeSteelCdpClient, STEEL_BASE_URL } = require("./steel-cdp-client.js");

function fakeFetch(handler) {
  const calls = [];
  const impl = async (url, opts = {}) => {
    calls.push({ url, method: (opts.method || "GET").toUpperCase(), body: opts.body ? JSON.parse(opts.body) : null });
    return handler(url, opts);
  };
  impl.calls = calls;
  return impl;
}

const ok = (json) => ({ ok: true, status: 200, json: async () => json, text: async () => JSON.stringify(json) });

test("the private-networking base URL is the Railway internal service, never a public domain", () => {
  assert.equal(STEEL_BASE_URL, "http://steel-browser.railway.internal:3000");
});

test("createSession posts /v1/sessions and returns the CDP websocket url", async () => {
  const fetchImpl = fakeFetch(() => ok({ id: "abc", websocketUrl: "ws://steel-browser.railway.internal:3000/", status: "live" }));
  const client = makeSteelCdpClient({ fetchImpl, connectCdp: async () => ({}) });
  const session = await client.createSession();

  assert.deepEqual(session, { id: "abc", websocketUrl: "ws://steel-browser.railway.internal:3000/" });
  assert.equal(fetchImpl.calls[0].url, "http://steel-browser.railway.internal:3000/v1/sessions");
  assert.equal(fetchImpl.calls[0].method, "POST");
});

test("releaseSession posts the verified per-session release route", async () => {
  const fetchImpl = fakeFetch(() => ok({ success: true }));
  const client = makeSteelCdpClient({ fetchImpl, connectCdp: async () => ({}) });
  await client.releaseSession("abc");
  assert.equal(fetchImpl.calls[0].url, "http://steel-browser.railway.internal:3000/v1/sessions/abc/release");
  assert.equal(fetchImpl.calls[0].method, "POST");
});

test("a failed session launch throws rather than returning a phantom session", async () => {
  const fetchImpl = fakeFetch(() => ({ ok: false, status: 503, text: async () => "service_unavailable" }));
  const client = makeSteelCdpClient({ fetchImpl, connectCdp: async () => ({}) });
  await assert.rejects(() => client.createSession(), /503/);
});

test("health checks the verified /v1/health route", async () => {
  const fetchImpl = fakeFetch(() => ok({ status: "ok" }));
  const client = makeSteelCdpClient({ fetchImpl, connectCdp: async () => ({}) });
  assert.equal(await client.health(), true);
  assert.equal(fetchImpl.calls[0].url, "http://steel-browser.railway.internal:3000/v1/health");
});

test("page work runs over the session's CDP connection and reads real form fields", async () => {
  const evaluated = [];
  const connectCdp = async (websocketUrl) => ({
    websocketUrl,
    async evaluate(expression) { evaluated.push(expression); return FORM; },
    async close() { evaluated.push("close"); },
  });
  const FORM = {
    submitSelector: "form button[type=submit]",
    fields: [{ selector: "#name", label: "お名前", name: "name", type: "text", required: true }],
  };
  const fetchImpl = fakeFetch(() => ok({ id: "abc", websocketUrl: "ws://s/", status: "live" }));
  const client = makeSteelCdpClient({ fetchImpl, connectCdp });

  await client.createSession();
  const form = await client.readForm("abc");
  assert.deepEqual(form, FORM);
  assert.equal(evaluated.length, 1);
  assert.match(evaluated[0], /querySelectorAll/);
});

test("releaseSession also closes the CDP connection so the single OSS session is really free", async () => {
  let closed = 0;
  const connectCdp = async () => ({ async evaluate() { return null; }, async close() { closed += 1; } });
  const fetchImpl = fakeFetch(() => ok({ id: "abc", websocketUrl: "ws://s/", status: "live" }));
  const client = makeSteelCdpClient({ fetchImpl, connectCdp });
  await client.createSession();
  await client.readForm("abc");
  await client.releaseSession("abc");
  assert.equal(closed, 1);
});
