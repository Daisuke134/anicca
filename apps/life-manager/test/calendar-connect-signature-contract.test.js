"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { createRequire } = require("node:module");

const HANDLER_PATH = path.resolve(__dirname, "../../landing/netlify/functions/calendar-connect.js");
const SECRET = "fixture-existing-lm-uid-secret";

process.env.COMPOSIO_API_KEY = "fixture-composio";
process.env.COMPOSIO_GCAL_AUTH_CONFIG = "fixture-calendar";
process.env.SUPABASE_URL = "https://fixture.supabase.co";
process.env.SUPABASE_SERVICE_ROLE_KEY = "fixture-service-role";
process.env.LM_UID_SECRET = SECRET;

function loadHandler() {
  const source = fs.readFileSync(HANDLER_PATH, "utf8");
  const module = { exports: {} };
  new Function("exports", "require", "module", "__filename", "__dirname", source)(
    module.exports, createRequire(HANDLER_PATH), module, HANDLER_PATH, path.dirname(HANDLER_PATH));
  return module.exports.handler;
}

function signedQuery(uid, purpose, exp, nonce) {
  const canonical = `${uid}\ncalendar-connect:${purpose}\n${exp}\n${nonce}`;
  return {
    uid, purpose, exp: String(exp), nonce,
    sig: crypto.createHmac("sha256", SECRET).update(canonical).digest("base64url"),
  };
}

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

function providerFixture() {
  const counts = { status: 0, oauth: 0, providerMutation: 0, nonceClaims: 0 };
  const claimed = new Set();
  const fetchImpl = async (input, init = {}) => {
    const url = new URL(String(input));
    const method = String(init.method || "GET").toUpperCase();
    if (url.pathname === "/rest/v1/lm_calendar_connect_nonces" && method === "POST") {
      counts.nonceClaims++;
      const row = JSON.parse(init.body || "{}");
      const key = `${row.uid}:${row.purpose}:${row.nonce_hash}`;
      if (claimed.has(key)) return response(409, { code: "23505" });
      claimed.add(key);
      return response(201, null);
    }
    if (url.hostname === "backend.composio.dev" && method === "GET") {
      counts.status++;
      return response(200, { items: [] });
    }
    if (url.hostname === "backend.composio.dev" && method === "POST") {
      counts.oauth++;
      return response(200, { redirect_url: "https://provider.example/consent" });
    }
    if (url.pathname === "/rest/v1/lm_users" && method === "PATCH") {
      counts.providerMutation++;
      return response(204, null);
    }
    throw new Error(`unexpected fetch ${method} ${url}`);
  };
  return { counts, fetchImpl };
}

async function invoke(handler, query) {
  return handler({ httpMethod: "GET", queryStringParameters: query });
}

function sideEffects(counts) {
  return { status: counts.status, oauth: counts.oauth, providerMutation: counts.providerMutation };
}

test("calendar-connect rejects missing, invalid, expired, uid-mismatched, and purpose-mismatched signatures before side effects", async () => {
  const handler = loadHandler();
  const fixture = providerFixture();
  const originalFetch = global.fetch;
  global.fetch = fixture.fetchImpl;
  try {
    const now = Math.floor(Date.now() / 1000);
    const attempts = [
      { uid: "lm_a", purpose: "oauth", exp: String(now + 300), nonce: "n-missing" },
      { uid: "lm_a", purpose: "oauth", exp: String(now + 300), nonce: "n-invalid", sig: "invalid" },
      signedQuery("lm_a", "oauth", now - 1, "n-expired"),
      { ...signedQuery("lm_a", "oauth", now + 300, "n-uid"), uid: "lm_b" },
      { ...signedQuery("lm_a", "status", now + 300, "n-purpose"), purpose: "oauth" },
    ];
    for (const query of attempts) {
      const before = { ...fixture.counts };
      const result = await invoke(handler, query);
      assert.equal(result.statusCode, 403);
      assert.deepEqual(sideEffects(fixture.counts), sideEffects(before));
    }
  } finally {
    global.fetch = originalFetch;
  }
});

test("calendar-connect lets one exact uid/purpose/expiry signature proceed and replay performs zero provider side effects", async () => {
  const handler = loadHandler();
  const fixture = providerFixture();
  const originalFetch = global.fetch;
  global.fetch = fixture.fetchImpl;
  try {
    const query = signedQuery("lm_a", "oauth", Math.floor(Date.now() / 1000) + 300, "n-once");
    const first = await invoke(handler, query);
    assert.equal(first.statusCode, 200);
    assert.equal(fixture.counts.status, 1);
    assert.equal(fixture.counts.oauth, 1);
    assert.equal(fixture.counts.providerMutation, 0);

    const beforeReplay = { ...fixture.counts };
    const replay = await invoke(handler, query);
    assert.equal(replay.statusCode, 403);
    assert.deepEqual(sideEffects(fixture.counts), sideEffects(beforeReplay));
  } finally {
    global.fetch = originalFetch;
  }
});

