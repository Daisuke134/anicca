"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { EventEmitter } = require("node:events");
const fs = require("node:fs");
const path = require("node:path");

const { createApnsClient } = require("../lib/apns-client.js");
const { createMobilePushOrchestrator, drainMobilePushJobs } = require("../lib/mobile-push.js");
const { appendMobileMessage, encodeCursor } = require("../lib/mobile-outbox.js");
const { createMemoryMobileStore } = require("../lib/mobile-store.js");
const { createMobilePushRuntime, startMobilePushDrain } = require("../server.js");

const TOKEN_A = "aa".repeat(32);
const TOKEN_B = "bb".repeat(32);
const MESSAGE_ID = "message:v1:durable-apns-1";
const CURSOR = encodeCursor(1);

function requestInput(token = TOKEN_A) {
  return { token, environment: "production", messageId: MESSAGE_ID, cursor: CURSOR };
}

function hangingHttp2(calls) {
  return {
    connect(authority) {
      const session = new EventEmitter();
      calls.push({ authority, session });
      session.request = () => {
        const stream = new EventEmitter();
        stream.setEncoding = () => {};
        stream.write = () => {};
        stream.end = () => {};
        stream.close = () => { stream.closed = true; };
        stream.destroy = () => { stream.destroyed = true; };
        calls.at(-1).stream = stream;
        return stream;
      };
      session.close = () => { calls.at(-1).closed = true; };
      session.destroy = () => { calls.at(-1).destroyed = true; };
      return session;
    },
  };
}

test("APNs stream timeout rejects and closes the session and stream", async () => {
  const calls = [];
  const client = createApnsClient({
    topic: "com.anicca.life-manager",
    tokenProvider: () => "jwt.fixture",
    requestIdFactory: () => "123e4567-e89b-12d3-a456-426614174000",
    http2: hangingHttp2(calls),
    connectTimeoutMs: 25,
    streamTimeoutMs: 5,
  });

  await assert.rejects(
    () => client.sendChatMessage(requestInput()),
    (error) => error.code === "apns_stream_timeout",
  );
  assert.equal(calls.length, 1);
  assert.equal(calls[0].closed || calls[0].destroyed, true);
  assert.equal(calls[0].stream.destroyed || calls[0].stream.closed, true);
});

test("APNs connect timeout rejects through the injected timeout boundary", async () => {
  const client = createApnsClient({
    topic: "com.anicca.life-manager",
    tokenProvider: () => "jwt.fixture",
    requestIdFactory: () => "123e4567-e89b-12d3-a456-426614174000",
    connect: () => new Promise(() => {}),
    connectTimeoutMs: 5,
  });
  await assert.rejects(
    () => client.sendChatMessage(requestInput()),
    (error) => error.code === "apns_connect_timeout",
  );
});

test("one provider device failure is recorded while later devices are still attempted", async () => {
  const records = [];
  const sender = createMobilePushOrchestrator({
    apnsClient: {
      async sendChatMessage(input) {
        if (input.token === TOKEN_A) throw Object.assign(new Error("temporary APNs failure"), { code: "apns_transport_error" });
        return { ok: true, status: 200, apnsId: "apns-b", environment: input.environment };
      },
    },
    listDevices: async () => [
      { deviceId: "device-a", token: TOKEN_A, environment: "production" },
      { deviceId: "device-b", token: TOKEN_B, environment: "production" },
    ],
    recordApnsResult: async (_scope, receipt) => records.push(receipt),
  });

  const result = await sender.notifyCommittedOutbox(
    { uid: "user-a" },
    { id: MESSAGE_ID, sequence: 1, cursor: CURSOR, key: "chat.welcome" },
  );

  assert.equal(result.attempted, 2);
  assert.equal(result.delivered, 1);
  assert.equal(records.length, 2);
  assert.equal(records[0].ok, false);
  assert.equal(records[0].reason, "apns_transport_error");
  assert.equal(records[1].ok, true);
});

test("outbox append atomically creates one pending dispatch job and duplicate append does not resend terminal work", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }], now: () => 1000 });
  const scope = { uid: "user-a", productLocale: "en" };
  const input = { id: MESSAGE_ID, key: "chat.welcome", args: {}, userContent: { eventTitle: null, eventLocation: null } };

  await appendMobileMessage(scope, input, { store });
  const firstJob = await store.readMobilePushJob(scope, MESSAGE_ID);
  assert.equal(firstJob.status, "pending");
  assert.equal(firstJob.attempts, 0);
  assert.equal(store._mobilePushJobs.size, 1);

  await store.markMobilePushJobSuccess(scope, MESSAGE_ID, { attempted: 1, delivered: 1 });
  await appendMobileMessage(scope, { ...input, args: { duplicate: true } }, { store });
  const terminal = await store.readMobilePushJob(scope, MESSAGE_ID);
  assert.equal(terminal.status, "completed");
  assert.equal(store._outbox.get("user-a").length, 1);
});

test("temporary delivery failure stays pending with backoff and the bounded drain retries it", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }], now: () => 1000 });
  const scope = { uid: "user-a", productLocale: "en" };
  await appendMobileMessage(scope, {
    id: MESSAGE_ID, key: "chat.welcome", args: {}, userContent: { eventTitle: null, eventLocation: null },
  }, { store });

  let sends = 0;
  const apnsClient = {
    async sendChatMessage(input) {
      sends += 1;
      if (sends === 1) throw Object.assign(new Error("temporary"), { code: "apns_transport_error" });
      return { ok: true, status: 200, apnsId: "apns-ok", environment: input.environment };
    },
  };
  await store.upsertDevice(scope, { token: TOKEN_A, environment: "production", locale: "en", timezone: "UTC" });
  const first = await drainMobilePushJobs({ store, apnsClient, now: () => 1000, maxJobs: 1 });
  assert.equal(first.processed, 1);
  const pending = await store.readMobilePushJob(scope, MESSAGE_ID);
  assert.equal(pending.status, "pending");
  assert.equal(pending.attempts, 1);
  assert.ok(pending.nextAttemptAt > 1000);

  const second = await drainMobilePushJobs({ store, apnsClient, now: () => pending.nextAttemptAt, maxJobs: 1 });
  assert.equal(second.processed, 1);
  const completed = await store.readMobilePushJob(scope, MESSAGE_ID);
  assert.equal(completed.status, "completed");
  assert.equal(completed.attempts, 2);
});

test("a crash after claiming before provider send is recovered after the lease expires", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }], now: () => 1000 });
  const scope = { uid: "user-a", productLocale: "en" };
  await appendMobileMessage(scope, {
    id: MESSAGE_ID, key: "chat.welcome", args: {}, userContent: { eventTitle: null, eventLocation: null },
  }, { store });
  await store.upsertDevice(scope, { token: TOKEN_A, environment: "production", locale: "en", timezone: "UTC" });
  const claimed = await store.claimMobilePushJob(scope, MESSAGE_ID, { now: 1000, leaseMs: 10 });
  assert.equal(claimed.status, "processing");
  assert.equal(claimed.attempts, 1);

  const sent = [];
  const drained = await drainMobilePushJobs({
    store,
    apnsClient: { async sendChatMessage(input) { sent.push(input); return { ok: true, status: 200, apnsId: "apns-recovered", environment: input.environment }; } },
    now: 11_001,
    maxJobs: 1,
  });
  assert.equal(drained.completed, 1);
  assert.equal(sent.length, 1);
  assert.equal((await store.readMobilePushJob(scope, MESSAGE_ID)).attempts, 2);
});

test("missing APNs credentials leaves the durable job pending and exposes owner health", async () => {
  const runtime = createMobilePushRuntime({});
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }], now: () => 1000 });
  const scope = { uid: "user-a", productLocale: "en" };
  await appendMobileMessage(scope, {
    id: MESSAGE_ID, key: "chat.welcome", args: {}, userContent: { eventTitle: null, eventLocation: null },
  }, { store });

  const result = await runtime.drainMobilePushJobs(store, { now: () => 1000, maxJobs: 1 });
  assert.equal(result.processed, 1);
  assert.equal(result.reason, "credentials_missing");
  assert.equal((await store.readMobilePushJob(scope, MESSAGE_ID)).status, "pending");
  assert.deepEqual(runtime.health(), { enabled: false, credentials: "missing", delivery: "pending" });
});

test("durable APNs migration defines the atomic outbox/job transaction and lease RPCs", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-09-lm-mobile-apns-delivery.sql"), "utf8");
  assert.match(sql, /CREATE TABLE IF NOT EXISTS public\.lm_mobile_push_jobs\b/u);
  assert.match(sql, /FOREIGN KEY \(uid, message_id\)[\s\S]*REFERENCES public\.lm_mobile_outbox\(uid, id\)/u);
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.append_lm_mobile_outbox_with_push_job\b/u);
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.claim_lm_mobile_push_job\b/u);
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.complete_lm_mobile_push_job\b/u);
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.retry_lm_mobile_push_job\b/u);
  assert.match(sql, /ON CONFLICT \(uid, id\) DO NOTHING[\s\S]*INSERT INTO public\.lm_mobile_push_jobs/u);
  assert.doesNotMatch(sql, /token text/u);
});

test("startup drain is bounded to one in-flight tick and can be stopped", async () => {
  const callbacks = [];
  const intervals = [];
  let ticks = 0;
  const timer = { unref() {} };
  let stopped = false;
  const loop = startMobilePushDrain({
    SUPABASE_URL: "https://supa.example",
    SUPABASE_SERVICE_ROLE_KEY: "service-key",
    LM_MOBILE_PUSH_DRAIN_INTERVAL_MS: "1000",
  }, {
    store: {},
    runtime: { drainMobilePushJobs: async () => { ticks += 1; return { processed: 0 }; } },
    setIntervalImpl: (callback, intervalMs) => { callbacks.push(callback); intervals.push(intervalMs); return timer; },
    clearIntervalImpl: (value) => { stopped = value === timer; },
  });
  assert.equal(loop.enabled, true);
  assert.deepEqual(intervals, [1000]);
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(ticks, 1);
  await loop.tick();
  assert.equal(ticks, 2);
  callbacks[0]();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(ticks, 3);
  loop.stop();
  assert.equal(stopped, true);
});
