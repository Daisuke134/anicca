"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { createRequire } = require("node:module");

const LANDING = path.resolve(__dirname, "../../landing");
const ONBOARD_HANDLER = path.join(LANDING, "netlify/functions/lm-onboard.js");
const LM_CLIENT = path.join(LANDING, "app/lm/LmClient.tsx");

process.env.COMPOSIO_API_KEY = "fixture-composio";
process.env.COMPOSIO_GCAL_AUTH_CONFIG = "fixture-calendar";
process.env.SUPABASE_URL = "https://fixture.supabase.co";
process.env.SUPABASE_SERVICE_ROLE_KEY = "fixture-service-role";
process.env.LM_UID_SECRET = "fixture-existing-lm-uid-secret";

function loadCommonJs(filename) {
  const source = fs.readFileSync(filename, "utf8");
  const module = { exports: {} };
  const localRequire = createRequire(filename);
  new Function("exports", "require", "module", "__filename", "__dirname", source)(
    module.exports, localRequire, module, filename, path.dirname(filename));
  return module.exports;
}

function response(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  };
}

function exchangeFixture(rowsByUid) {
  const calls = [];
  const handler = loadCommonJs(ONBOARD_HANDLER).handler;
  const fetchImpl = async (input, init = {}) => {
    const url = new URL(String(input));
    const method = String(init.method || "GET").toUpperCase();
    calls.push({ url, method, body: init.body && JSON.parse(init.body) });
    if (url.pathname === "/auth/v1/user") {
      const token = String((init.headers || {}).Authorization || "").replace(/^Bearer /, "");
      return response(200, { id: token === "token-b" ? "user-b" : "user-a" });
    }
    if (url.pathname === "/rest/v1/lm_users" && method === "GET") {
      const uid = String(url.searchParams.get("uid") || "").replace(/^eq\./, "");
      const row = rowsByUid[uid];
      return response(200, row ? [{ ...row }] : []);
    }
    if (url.pathname === "/rest/v1/lm_users" && method === "POST") return response(201, null);
    if (url.pathname === "/rest/v1/lm_calendar_connect_nonces" && method === "POST") return response(201, null);
    throw new Error(`unexpected fetch ${method} ${url}`);
  };
  return { handler, fetchImpl, calls };
}

async function exchange(handler, accessToken) {
  const result = await handler({
    httpMethod: "POST",
    queryStringParameters: { action: "exchange" },
    body: JSON.stringify({ access_token: accessToken }),
  });
  return { status: result.statusCode, body: JSON.parse(result.body) };
}

test("production onboarding exchange returns only the authenticated user's durable resume truth", async () => {
  const fixture = exchangeFixture({
    "lm_user-a": {
      uid: "lm_user-a", name: "Existing A", calendar_provider: "composio_gcal",
      phone: "+447700900123", paid: true, tg_onboard_stage: "done", call_language: "ja",
    },
  });
  const originalFetch = global.fetch;
  global.fetch = fixture.fetchImpl;
  try {
    const existing = await exchange(fixture.handler, "token-a");
    assert.equal(existing.status, 200);
    assert.deepEqual(existing.body.onboarding, {
      name: "Existing A", calendarConnected: true, contextComplete: true,
      phone: "+447700900123", paid: true, callLanguage: "ja", step: "dashboard",
    });

    const first = await exchange(fixture.handler, "token-b");
    assert.equal(first.status, 200);
    assert.deepEqual(first.body.onboarding, {
      name: null, calendarConnected: false, contextComplete: false,
      phone: null, paid: false, callLanguage: null, step: "name",
    });

    const reads = fixture.calls.filter((call) => call.method === "GET" && call.url.pathname === "/rest/v1/lm_users");
    assert.deepEqual(reads.map((call) => call.url.searchParams.get("uid")), ["eq.lm_user-a", "eq.lm_user-b"]);
    assert.ok(reads.every((call) => call.url.searchParams.get("limit") === "1"), "every resume read is tenant-scoped");
  } finally {
    global.fetch = originalFetch;
  }
});

function memoryStorage(entries = {}) {
  const values = new Map(Object.entries(entries));
  return {
    getItem: (key) => values.has(key) ? values.get(key) : null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
    entries: () => [...values.entries()],
  };
}

function transpileClientBehavior(fragment) {
  return fragment
    .replace(/^type .*$/gm, "")
    .replace(/const COUNTRIES:\s*\{[^=]+\}\[\]\s*=/, "const COUNTRIES =")
    .replace(/function splitPhone\(phone: unknown\)/, "function splitPhone(phone)")
    .replace(/function calendarGrantQuery\(uid: string, grant: CalendarGrant\)/,
      "function calendarGrantQuery(uid, grant)")
    .replace(/useState<[^>]+>/g, "useState")
    .replace(/useRef<[^>]+>/g, "useRef")
    .replace(/let d: any;/, "let d;")
    .replace(/durable\.step as Step/g, "durable.step")
    .replace(/\(fn: string, set: \(s: ConnState\) => void\)/, "(fn, set)");
}

function loadActualClient({ fetchImpl, getSession, storage, search = "", stateOverrides = {} }) {
  const source = fs.readFileSync(LM_CLIENT, "utf8");
  const constantsStart = source.indexOf("const EXCHANGE_URL");
  const constantsEnd = source.indexOf("function StepDots");
  const componentStart = source.indexOf("export default function LmClient()");
  const renderStart = source.indexOf("// ── render", componentStart);
  assert.ok(constantsStart >= 0 && constantsEnd > constantsStart && componentStart >= 0 && renderStart > componentStart,
    "LmClient behavior harness must locate the production component body");
  const constants = source.slice(constantsStart, constantsEnd);
  const component = source.slice(componentStart, renderStart)
    .replace("export default function LmClient()", "function LmClient()") +
    "return { saveName, savePhone, runConnect };\n}";
  const executable = transpileClientBehavior(`${constants}\n${component}`);

  const effects = [];
  const updates = [];
  let stateIndex = 0;
  const useState = (initial) => {
    const index = stateIndex++;
    const value = Object.prototype.hasOwnProperty.call(stateOverrides, index) ? stateOverrides[index] : initial;
    updates[index] = [];
    return [value, (next) => updates[index].push(typeof next === "function" ? next(value) : next)];
  };
  const useEffect = (effect) => effects.push(effect);
  const useCallback = (fn) => fn;
  const useRef = (value) => ({ current: value });
  const historyCalls = [];
  const fakeWindow = {
    localStorage: storage,
    location: { search, pathname: "/lm", origin: "https://aniccaai.com", href: "https://aniccaai.com/lm" + search },
    history: { replaceState: (...args) => historyCalls.push(args) },
    open: () => ({ close() {}, location: { href: "" } }),
  };
  const launchStrings = { en: { lm: {
    name: { error: "name required", saveError: "name save failed" },
    phone: { error: "phone invalid", saveError: "phone save failed" },
  } } };
  const factory = new Function(
    "useCallback", "useEffect", "useRef", "useState", "useLaunchLocale", "launchStrings",
    "signInWithGoogle", "getSession", "window", "fetch", "process",
    `${executable}\nreturn LmClient;`,
  );
  const componentFn = factory(
    useCallback, useEffect, useRef, useState, () => ({ locale: "en" }), launchStrings,
    async () => {}, getSession, fakeWindow, fetchImpl, process,
  );
  const callbacks = componentFn();
  return {
    callbacks, effects, updates, historyCalls, storage,
    latest(index, fallback) {
      const values = updates[index] || [];
      return values.length ? values[values.length - 1] : fallback;
    },
  };
}

async function flushAsyncWork() {
  for (let i = 0; i < 6; i++) await new Promise((resolve) => setImmediate(resolve));
}

function exchangeResponse(uid, onboarding) {
  return response(200, {
    uid, sig: `uid-sig-${uid}`, onboarding,
    calendarConnect: {
      oauth: { purpose: "oauth", exp: 1999999999, nonce: `nonce-${uid}`, sig: `oauth-sig-${uid}` },
      status: { purpose: "status", exp: 1999999999, nonce: "", sig: `status-sig-${uid}` },
    },
  });
}

test("actual LmClient resumes an existing user from server truth in a fresh browser", async () => {
  const storage = memoryStorage();
  const client = loadActualClient({
    storage, getSession: async () => ({ access_token: "token-a" }),
    fetchImpl: async () => exchangeResponse("lm_user-a", {
      name: "Existing A", calendarConnected: true, contextComplete: true,
      phone: "+447700900123", paid: true, callLanguage: "ja", step: "dashboard",
    }),
  });
  client.effects[1]();
  await flushAsyncWork();
  assert.equal(client.latest(0, "login"), "dashboard");
  assert.equal(client.latest(3, ""), "Existing A");
  assert.equal(client.latest(7, "idle"), "connected");
  assert.equal(client.latest(6, ""), "7700900123");
});

test("actual LmClient does not inherit another user's global browser state", async () => {
  const storage = memoryStorage({
    "anicca.lm.uid": "lm_user-a", "anicca.lm.sig": "sig-a",
    "anicca.lm.step": "dashboard", "anicca.lm.cal": "connected",
  });
  const client = loadActualClient({
    storage, getSession: async () => ({ access_token: "token-b" }),
    fetchImpl: async () => exchangeResponse("lm_user-b", {
      name: null, calendarConnected: false, contextComplete: false,
      phone: null, paid: false, callLanguage: null, step: "name",
    }),
  });
  client.effects[1]();
  await flushAsyncWork();
  assert.equal(client.latest(1, ""), "lm_user-b");
  assert.equal(client.latest(0, "login"), "name");
  assert.equal(client.latest(3, ""), "");
  assert.equal(client.latest(7, "idle"), "idle");
  assert.deepEqual(storage.entries().filter(([key]) => [
    "anicca.lm.uid", "anicca.lm.sig", "anicca.lm.step", "anicca.lm.cal",
  ].includes(key)), [], "unscoped onboarding cache must be removed");
});

test("actual LmClient does not advance after a non-2xx profile save", async () => {
  const saveClient = loadActualClient({
    storage: memoryStorage(), getSession: async () => null,
    stateOverrides: { 0: "name", 1: "lm_user-a", 2: "uid-sig", 3: "Alice" },
    fetchImpl: async () => response(502, { ok: false }),
  });
  await saveClient.callbacks.saveName();
  assert.equal(saveClient.latest(0, "name"), "name", "failed name save must not advance");
});

test("actual LmClient keeps a recoverable Telegram binding after a non-2xx link", async () => {
  const linkCalls = [];
  const linkClient = loadActualClient({
    storage: memoryStorage(), search: "?tg=100&name=Alice",
    getSession: async () => ({ access_token: "token-a" }),
    fetchImpl: async (input) => {
      linkCalls.push(String(input));
      if (String(input).includes("action=exchange")) return exchangeResponse("lm_user-a", {
        name: "Alice", calendarConnected: false, contextComplete: false,
        phone: null, paid: false, callLanguage: "en", step: "connect",
      });
      return response(502, { ok: false });
    },
  });
  linkClient.effects[1]();
  await flushAsyncWork();
  assert.equal(linkCalls.filter((url) => url.includes("action=telegram-link")).length, 1);
  assert.equal(linkClient.historyCalls.length, 0, "failed Telegram link must keep the binding URL recoverable");
  const pending = linkClient.storage.entries().filter(([key]) => key === "anicca.lm.user:lm_user-a:telegram-binding");
  assert.equal(pending.length, 1, "failed binding is cached only under the authenticated uid");
});
