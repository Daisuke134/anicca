"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  OUTBOUND_CAPABILITY,
  classifyOutboundWorkerHealth,
  runOutboundGuardian,
} = require("./outbound-guardian.js");

const NOW = Date.parse("2026-08-01T03:00:00.000Z");

function healthyBody(overrides = {}) {
  return {
    ok: true,
    role: "worker",
    worker_id: "local-runtime-worker",
    capabilities: ["runtime.noop", OUTBOUND_CAPABILITY],
    last_poll_at: "2026-08-01T02:59:30.000Z",
    ...overrides,
  };
}

test("workerが応募能力を持ち、直近pollがfreshならhealthy", () => {
  assert.deepEqual(classifyOutboundWorkerHealth({
    httpStatus: 200,
    body: healthyBody(),
    nowMs: NOW,
    maxPollAgeMs: 120_000,
  }), {
    ok: true,
    code: "HEALTHY",
    workerId: "local-runtime-worker",
    pollAgeMs: 30_000,
  });
});

test("到達不能はhealthyにしない", () => {
  assert.equal(classifyOutboundWorkerHealth({
    error: new Error("connect ECONNREFUSED"),
    nowMs: NOW,
  }).code, "UNREACHABLE");
});

test("HTTP 200でもJSONでなければhealthyにしない", () => {
  assert.equal(classifyOutboundWorkerHealth({
    httpStatus: 200,
    body: null,
    nowMs: NOW,
  }).code, "INVALID_PAYLOAD");
});

test("HTTPエラーはhealthyにしない", () => {
  assert.equal(classifyOutboundWorkerHealth({
    httpStatus: 503,
    body: healthyBody({ ok: false }),
    nowMs: NOW,
  }).code, "HTTP_UNHEALTHY");
});

test("worker以外のroleはhealthyにしない", () => {
  assert.equal(classifyOutboundWorkerHealth({
    httpStatus: 200,
    body: healthyBody({ role: "api" }),
    nowMs: NOW,
  }).code, "WRONG_ROLE");
});

test("outbound capabilityがないworkerはhealthyにしない", () => {
  assert.equal(classifyOutboundWorkerHealth({
    httpStatus: 200,
    body: healthyBody({ capabilities: ["runtime.noop"] }),
    nowMs: NOW,
  }).code, "MISSING_CAPABILITY");
});

test("last_poll_atが壊れている、未来、古い場合はhealthyにしない", () => {
  for (const [lastPollAt, code] of [
    ["not-a-date", "INVALID_LAST_POLL"],
    ["2026-08-01T03:00:01.000Z", "INVALID_LAST_POLL"],
    ["2026-08-01T02:57:59.999Z", "STALE_POLL"],
  ]) {
    assert.equal(classifyOutboundWorkerHealth({
      httpStatus: 200,
      body: healthyBody({ last_poll_at: lastPollAt }),
      nowMs: NOW,
      maxPollAgeMs: 120_000,
    }).code, code);
  }
});

test("Guardianはhealthyならself-fixを呼ばない", async () => {
  const calls = [];
  const result = await runOutboundGuardian({
    healthUrl: "http://127.0.0.1:18790/health",
    nowMs: NOW,
    fetchHealth: async () => ({ httpStatus: 200, body: healthyBody() }),
    selfFix: async (...args) => calls.push(args),
  });
  assert.equal(result.code, "HEALTHY");
  assert.deepEqual(calls, []);
});

test("Guardianは異常理由とURLを既存self-fixへ一度だけ渡す", async () => {
  const calls = [];
  const result = await runOutboundGuardian({
    healthUrl: "http://127.0.0.1:18790/health",
    nowMs: NOW,
    fetchHealth: async () => ({
      httpStatus: 200,
      body: healthyBody({ capabilities: ["runtime.noop"] }),
    }),
    selfFix: async (...args) => calls.push(args),
  });
  assert.equal(result.code, "MISSING_CAPABILITY");
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "connector-outbound");
  assert.match(calls[0][1], /MISSING_CAPABILITY/);
  assert.match(calls[0][1], /127\.0\.0\.1:18790/);
});

