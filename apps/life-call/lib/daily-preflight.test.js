"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  DEPENDENCY_NAMES,
  createDependencyChecks,
  runPreflight,
} = require("./daily-preflight.js");

const REQUIRED = [
  "health",
  "telegram",
  "calendar",
  "call",
  "location",
  "email",
  "discovery",
  "gemini",
  "maps",
];

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}

function productionLikeEnv() {
  return {
    RAILWAY_PUBLIC_DOMAIN: "life-call.example.test",
    LM_TELEGRAM_BOT_TOKEN: "telegram-secret-token",
    LM_TELEGRAM_WEBHOOK_SECRET: "telegram-webhook-secret",
    COMPOSIO_API_KEY: "composio-secret-key",
    SUPABASE_URL: "https://project.supabase.co",
    SUPABASE_SERVICE_ROLE_KEY: "supabase-secret-key",
    TELNYX_API_KEY: "telnyx-secret-key",
    TELNYX_PHONE_NUMBER: "+15551234567",
    TELNYX_CONNECTION_ID: "call-control-123",
    RESEND_API_KEY: "resend-secret-key",
    LM_MAIL_FROM: "Life Manager <hello@aniccaai.com>",
    GEMINI_API_KEY: "gemini-secret-key",
    LIFE_MAPS_KEY: "maps-secret-key",
  };
}

function successfulFetch(url, options = {}) {
  const target = String(url);
  if (target === "https://life-call.example.test/health") {
    return Promise.resolve(jsonResponse({ ok: true, service: "life-call", build: "build-123" }));
  }
  if (target.includes("api.telegram.org") && target.endsWith("/getWebhookInfo")) {
    return Promise.resolve(jsonResponse({
      ok: true,
      result: {
        url: "https://life-call.example.test/telegram",
        pending_update_count: 0,
        allowed_updates: ["callback_query", "edited_message", "message"],
      },
    }));
  }
  if (target.includes("/rest/v1/lm_users?paid=is.true")) {
    return Promise.resolve(jsonResponse([{ uid: "user-private-id" }]));
  }
  if (target.includes("backend.composio.dev/api/v3/tools/execute/GOOGLECALENDAR_EVENTS_LIST")) {
    return Promise.resolve(jsonResponse({ successful: true, data: { items: [] } }));
  }
  if (target.endsWith("/v2/balance")) {
    return Promise.resolve(jsonResponse({ data: { balance: "3.25", currency: "USD" } }));
  }
  if (target.includes("/v2/phone_numbers?")) {
    return Promise.resolve(jsonResponse({ data: [{ phone_number: "+15551234567", status: "active" }] }));
  }
  if (target.endsWith("/v2/call_control_applications/call-control-123")) {
    return Promise.resolve(jsonResponse({
      data: {
        id: "call-control-123",
        active: true,
        webhook_event_url: "https://life-call.example.test/telnyx-events",
        outbound: { outbound_voice_profile_id: "profile-private-id" },
      },
    }));
  }
  if (target.includes("/rest/v1/lm_user_locations?")) {
    return Promise.resolve(jsonResponse([{ observed_at: "2026-07-21T00:00:00Z", expires_at: "2026-07-22T00:00:00Z" }]));
  }
  if (target === "https://api.resend.com/domains") {
    return Promise.resolve(jsonResponse({ data: [{ name: "aniccaai.com", status: "verified" }] }));
  }
  if (target.includes("/rest/v1/lm_users?telegram_chat_id=not.is.null")) {
    return Promise.resolve(jsonResponse([{
      uid: "user-private-id",
      telegram_chat_id: "private-chat-id",
      last_discovery_at: "2026-07-14T00:00:00Z",
      last_discovery_gate: "location",
      payout_destination: null,
    }]));
  }
  if (target.includes("generativelanguage.googleapis.com/v1beta/models/")) {
    return Promise.resolve(jsonResponse({
      name: "models/gemini-2.5-flash-native-audio-preview-09-2025",
      supportedGenerationMethods: ["bidiGenerateContent"],
    }));
  }
  if (target === "https://routes.googleapis.com/directions/v2:computeRoutes") {
    assert.equal(options.method, "POST");
    return Promise.resolve(jsonResponse({ routes: [{ duration: "900s" }] }));
  }
  if (target.includes("maps.googleapis.com/maps/api/directions/json?")) {
    return Promise.resolve(jsonResponse({ status: "OK", routes: [{ legs: [{ duration: { value: 1200 } }] }] }));
  }
  throw new Error(`unexpected test URL: ${target}`);
}

test("manifest covers every required DAILY runtime dependency and real adapters pass with useful redacted evidence", async () => {
  assert.deepEqual(DEPENDENCY_NAMES, REQUIRED);
  const env = productionLikeEnv();
  const requests = [];
  const fetchImpl = (url, options = {}) => {
    requests.push({ url: String(url), method: options.method || "GET" });
    return successfulFetch(url, options);
  };
  const checks = createDependencyChecks({ env, fetchImpl, nowMs: Date.parse("2026-07-21T06:00:00Z") });

  const report = await runPreflight({ checks, timeoutMs: 100, now: () => Date.parse("2026-07-21T06:00:00Z") });

  assert.equal(report.overallStatus, "pass");
  assert.equal(report.exitCode, 0);
  assert.deepEqual(report.summary, { required: 9, passed: 9, failed: 0, timedOut: 0 });
  assert.deepEqual(report.dependencies.map((item) => item.dependency), REQUIRED);
  for (const item of report.dependencies) {
    assert.equal(item.status, "pass", item.dependency);
    assert.equal(item.failureClass, null, item.dependency);
    assert.equal(typeof item.latencyMs, "number", item.dependency);
    assert.ok(item.evidence && Object.keys(item.evidence).length > 0, item.dependency);
  }
  const serialized = JSON.stringify(report);
  for (const secret of Object.values(env).filter((value) => /secret|private|\+1555/.test(value))) {
    assert.equal(serialized.includes(secret), false, `must redact ${secret}`);
  }
  assert.equal(serialized.includes("hello@aniccaai.com"), false);
  assert.equal(serialized.includes("+15551234567"), false);
  assert.equal(requests.some(({ url }) => /\/emails$|\/v2\/calls$|sendMessage|CREATE_EVENT|PATCH_EVENT/.test(url)), false);
  assert.deepEqual(
    requests.filter(({ method }) => method === "POST").map(({ url }) => new URL(url).pathname).sort(),
    [
      "/api/v3/tools/execute/GOOGLECALENDAR_EVENTS_LIST",
      "/bottelegram-secret-token/getWebhookInfo",
      "/directions/v2:computeRoutes",
    ].sort(),
  );
});

test("explicit failure for every dependency is fail-closed and never becomes zero/empty success", async () => {
  const checks = REQUIRED.map((name) => ({
    name,
    run: async () => ({ ok: false, failureClass: "auth", evidence: { count: 0 } }),
  }));

  const report = await runPreflight({ checks, timeoutMs: 100 });

  assert.equal(report.overallStatus, "fail");
  assert.equal(report.exitCode, 1);
  assert.deepEqual(report.summary, { required: 9, passed: 0, failed: 9, timedOut: 0 });
  assert.ok(report.dependencies.every((item) => item.status === "fail"));
  assert.ok(report.dependencies.every((item) => item.failureClass === "auth"));
});

test("empty, false, and zero adapter results are invalid failures rather than success", async () => {
  const emptyValues = [undefined, null, false, 0, "", [], {}];
  const checks = REQUIRED.map((name, index) => ({ name, run: async () => emptyValues[index % emptyValues.length] }));

  const report = await runPreflight({ checks, timeoutMs: 100 });

  assert.equal(report.exitCode, 1);
  assert.equal(report.summary.passed, 0);
  assert.ok(report.dependencies.every((item) => item.status === "fail"));
  assert.ok(report.dependencies.every((item) => item.failureClass === "invalid_result"));
});

test("timeout for every dependency is classified and forces a nonzero exit", async () => {
  const checks = REQUIRED.map((name) => ({ name, run: () => new Promise(() => {}) }));

  const report = await runPreflight({ checks, timeoutMs: 5 });

  assert.equal(report.overallStatus, "fail");
  assert.equal(report.exitCode, 1);
  assert.deepEqual(report.summary, { required: 9, passed: 0, failed: 0, timedOut: 9 });
  assert.ok(report.dependencies.every((item) => item.status === "timeout"));
  assert.ok(report.dependencies.every((item) => item.failureClass === "timeout"));
});

test("thrown provider errors expose only a classification, never raw messages or secrets", async () => {
  const report = await runPreflight({
    checks: [{
      name: "health",
      run: async () => { throw new Error("Bearer super-secret hello@example.com +15551234567"); },
    }],
    timeoutMs: 100,
  });

  assert.equal(report.exitCode, 1);
  assert.equal(report.dependencies[0].failureClass, "dependency_error");
  assert.deepEqual(report.dependencies[0].evidence, { reason: "dependency_error" });
  assert.equal(JSON.stringify(report).includes("super-secret"), false);
  assert.equal(JSON.stringify(report).includes("hello@example.com"), false);
});
