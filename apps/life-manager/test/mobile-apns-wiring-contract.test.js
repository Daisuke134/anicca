"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { Readable } = require("node:stream");

const { appendMobileMessage, encodeCursor } = require("../lib/mobile-outbox.js");
const { createMemoryMobileStore, createSupabaseMobileStore } = require("../lib/mobile-store.js");
const { createMobilePushOrchestrator } = require("../lib/mobile-push.js");
const { handleMobileV1Request } = require("../lib/mobile-v1-router.js");
const { createMobilePushRuntime } = require("../server.js");

const TOKEN_A = "aa".repeat(32);
const TOKEN_B = "bb".repeat(32);
const CURSOR = encodeCursor(1);

function semanticInput(id = "message:v1:push-1") {
  return {
    id,
    type: "system",
    key: "chat.welcome",
    args: {},
    userContent: { eventTitle: null, eventLocation: null },
  };
}

function request(method, url, body, headers = {}) {
  const req = Readable.from(body === undefined ? [] : [JSON.stringify(body)]);
  req.method = method;
  req.url = url;
  req.headers = { ...(body === undefined ? {} : { "content-type": "application/json" }), ...headers };
  return req;
}

function response() {
  return {
    statusCode: 200, headers: {}, body: "",
    writeHead(status, headers = {}) { this.statusCode = status; Object.assign(this.headers, headers); },
    end(value = "") { this.body += value; this.ended = true; },
  };
}

function parsed(res) {
  return JSON.parse(res.body || "{}");
}

test("an outbox row without a committed sequence never invokes the APNs notifier", async () => {
  let sends = 0;
  const store = {
    async appendOutbox(_scope, row) { return { ...row, sequence: null }; },
  };
  await assert.rejects(
    () => appendMobileMessage({ uid: "user-a" }, semanticInput(), {
      store,
      notifyMobilePush: async () => { sends += 1; },
    }),
    (error) => error.code === "outbox_sequence_missing",
  );
  assert.equal(sends, 0);
});

test("a newly committed semantic insert sends one notification after persistence", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }] });
  const calls = [];
  const result = await appendMobileMessage({ uid: "user-a", productLocale: "en" }, semanticInput(), {
    store,
    notifyMobilePush: async (scope, row) => calls.push({ scope, row }),
  });
  assert.equal(result.id, "message:v1:push-1");
  assert.equal(calls.length, 1);
  assert.equal(calls[0].scope.uid, "user-a");
  assert.equal(calls[0].row.sequence, 1);
  assert.equal(calls[0].row.cursor, encodeCursor(1));
  assert.equal(store._outbox.get("user-a").length, 1);
});

test("a duplicate append conflict returns the original message and sends zero additional notifications", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }] });
  let sends = 0;
  const deps = { store, notifyMobilePush: async () => { sends += 1; } };
  const first = await appendMobileMessage({ uid: "user-a", productLocale: "en" }, semanticInput(), deps);
  const replay = await appendMobileMessage({ uid: "user-a", productLocale: "en" }, {
    ...semanticInput(), args: { replay: true },
  }, deps);
  assert.equal(sends, 1);
  assert.equal(replay.id, first.id);
  assert.equal(replay.cursor, first.cursor);
  assert.equal(store._outbox.get("user-a").length, 1);
});

test("a push failure records a durable failure and never removes the committed outbox row", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }] });
  const failures = [];
  const message = await appendMobileMessage({ uid: "user-a", productLocale: "en" }, semanticInput(), {
    store,
    notifyMobilePush: async () => { throw Object.assign(new Error("APNs unavailable"), { code: "apns_transport_error" }); },
    recordMobilePushFailure: async (scope, row, error) => failures.push({ scope, row, error }),
  });
  assert.equal(message.id, "message:v1:push-1");
  assert.equal(store._outbox.get("user-a").length, 1);
  assert.equal(failures.length, 1);
  assert.equal(failures[0].scope.uid, "user-a");
  assert.equal(failures[0].row.sequence, 1);
  assert.equal(failures[0].error.code, "apns_transport_error");
});

test("the orchestrator lists and sends only the authenticated tenant devices", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }, { uid: "user-b" }] });
  await store.upsertDevice({ uid: "user-a" }, { token: TOKEN_A, environment: "production", locale: "en", timezone: "UTC" });
  await store.upsertDevice({ uid: "user-b" }, { token: TOKEN_B, environment: "production", locale: "en", timezone: "UTC" });
  const sent = [];
  const orchestrator = createMobilePushOrchestrator({
    store,
    apnsClient: { async sendChatMessage(input) { sent.push(input); return { ok: true, status: 200, apnsId: "apns-a", reason: null }; } },
    recordApnsResult: (scope, receipt) => store.recordApnsResult(scope, receipt),
  });
  await orchestrator.notifyCommittedOutbox({ uid: "user-a" }, { id: "message:v1:push-1", sequence: 1, cursor: CURSOR, key: "chat.welcome" });
  assert.deepEqual(sent.map((item) => item.token), [TOKEN_A]);
  assert.equal(store._apnsResults.length, 1);
  assert.equal(store._apnsResults[0].uid, "user-a");
  assert.equal(store._apnsResults[0].messageId, "message:v1:push-1");
});

test("APNs result logging stores provider facts but never token or notification body", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }] });
  await store.recordApnsResult({ uid: "user-a" }, {
    deviceId: "device-a", apnsId: "apns-1", status: 410, reason: "Unregistered",
    environment: "production", messageId: "message:v1:push-1", token: TOKEN_A,
    payload: { aps: { alert: "secret body" }, messageId: "message:v1:push-1" },
  });
  const logged = store._apnsResults[0];
  assert.deepEqual(logged, {
    uid: "user-a", deviceId: "device-a", apnsId: "apns-1", status: 410,
    reason: "Unregistered", environment: "production", messageId: "message:v1:push-1",
  });
  assert.equal(JSON.stringify(logged).includes(TOKEN_A), false);
  assert.equal(JSON.stringify(logged).includes("secret body"), false);
});

test("Supabase APNs result, list, and removal operations are tenant-scoped", async () => {
  const calls = [];
  const store = createSupabaseMobileStore({
    supaUrl: "https://supa.example", supaKey: "service-key",
    fetchImpl: async (input, init = {}) => {
      const url = new URL(String(input));
      calls.push({ url, init });
      if (url.pathname.endsWith("/lm_mobile_devices") && init.method === "GET") {
        return { ok: true, status: 200, json: async () => [{ token: TOKEN_A, environment: "production", locale: "en", timezone: "UTC" }] };
      }
      if (url.pathname.endsWith("/lm_mobile_apns_results")) {
        return { ok: true, status: 201, json: async () => [{ id: 1 }] };
      }
      return { ok: true, status: 204, json: async () => ({}) };
    },
  });
  const devices = await store.listDevices({ uid: "user-a" });
  await store.recordApnsResult({ uid: "user-a" }, {
    deviceId: "device-a", apnsId: "apns-1", status: 200, reason: null,
    environment: "production", messageId: "message:v1:push-1", token: TOKEN_A,
    payload: { messageId: "message:v1:push-1" },
  });
  await store.removeDevice({ uid: "user-a" }, TOKEN_A);
  assert.equal(devices[0].token, TOKEN_A);
  const resultWrite = calls.find((call) => call.url.pathname.endsWith("/lm_mobile_apns_results"));
  const resultBody = JSON.parse(resultWrite.init.body);
  assert.equal(resultBody.uid, "user-a");
  assert.equal(resultBody.message_id, "message:v1:push-1");
  assert.equal(Object.hasOwn(resultBody, "token"), false);
  assert.equal(Object.hasOwn(resultBody, "payload"), false);
  for (const call of calls) {
    if (call.url.pathname.endsWith("/lm_mobile_devices") || call.url.pathname.endsWith("/lm_mobile_apns_results")) {
      if (call.init.method === "POST") assert.equal(JSON.parse(call.init.body).uid, "user-a");
      else assert.equal(call.url.searchParams.get("uid"), "eq.user-a");
    }
  }
});

test("router passes the mobile push notifier through the authenticated runtime", async () => {
  let seen;
  const res = response();
  await handleMobileV1Request(request("POST", "/api/mobile/v1/analysis", { analysisId: "analysis:router-push" }, {
    authorization: "Bearer access", "idempotency-key": "analysis-router-push",
  }), res, {
    authenticateMobileRequest: async () => ({ uid: "user-a", sessionId: "session-a", productLocale: "en", timezone: "UTC" }),
    idempotencyStore: new Map(),
    notifyMobilePush: async () => {},
    analyzeNextEvent: async (_scope, _body, runtime) => { seen = runtime.notifyMobilePush; return { status: "no_upcoming_event" }; },
  });
  assert.equal(res.statusCode, 200);
  assert.equal(typeof seen, "function");
});

test("missing APNs credentials disable push without failing message creation", async () => {
  const runtime = createMobilePushRuntime({});
  assert.equal(runtime.enabled, false);
  const result = await runtime.notifyMobilePush({ uid: "user-a" }, {
    id: "message:v1:push-1", sequence: 1, cursor: CURSOR, key: "chat.welcome",
  }, { store: createMemoryMobileStore({ users: [{ uid: "user-a" }] }) });
  assert.deepEqual(result, { enabled: false, reason: "credentials_missing" });
});

test("APNs migration stores no device token or payload columns in the result log", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-09-lm-mobile-apns.sql"), "utf8");
  assert.match(sql, /CREATE TABLE IF NOT EXISTS public\.lm_mobile_apns_results\b/u);
  assert.match(sql, /message_id text NOT NULL/u);
  assert.match(sql, /apns_id text/u);
  assert.match(sql, /status integer/u);
  assert.match(sql, /reason text/u);
  assert.match(sql, /environment text/u);
  assert.match(sql, /GRANT USAGE, SELECT ON SEQUENCE public\.lm_mobile_apns_results_id_seq TO service_role;/u);
  assert.doesNotMatch(sql, /token text/u);
  assert.doesNotMatch(sql, /payload jsonb/u);
});
