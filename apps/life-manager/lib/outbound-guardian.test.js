"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const {
  OUTBOUND_CAPABILITY,
  classifyOutboundWorkerHealth,
  guardianExitCode,
  parseOpenClawMessageId,
  recoverDockerWorker,
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

test("OpenClaw receiptはpositive message IDだけを配信成功にする", () => {
  assert.equal(parseOpenClawMessageId('{"messageId":"4312"}'), "4312");
  for (const value of ["{}", '{"messageId":0}', '{"messageId":"no"}', "not-json"]) {
    assert.throws(() => parseOpenClawMessageId(value), /message ID/);
  }
});

function memoryIncident(initial = null) {
  let value = initial;
  return {
    async load() { return value; },
    async save(next) { value = { ...next }; },
    async clear() { value = null; },
    value() { return value; },
  };
}

test("停止を一度だけ警告し、自動再起動後に復旧通知してincidentをclearする", async () => {
  const incidentStore = memoryIncident();
  const messages = [];
  const health = [
    { error: new Error("connect ECONNREFUSED") },
    { httpStatus: 200, body: healthyBody() },
  ];
  const selfFixCalls = [];
  const result = await runOutboundGuardian({
    healthUrl: "http://127.0.0.1:18790/health",
    nowMs: NOW,
    fetchHealth: async () => health.shift(),
    incidentStore,
    notify: async (message) => {
      messages.push(message);
      return { messageId: String(7000 + messages.length) };
    },
    recover: async () => true,
    selfFix: async (...args) => selfFixCalls.push(args),
  });
  assert.equal(result.code, "UNREACHABLE");
  assert.equal(result.recovered, true);
  assert.deepEqual(result.telegram, { alertMessageId: "7001", recoveryMessageId: "7002" });
  assert.equal(messages.length, 2);
  assert.match(messages[0], /Connectorの応募処理が停止/);
  assert.match(messages[0], /自動復旧/);
  assert.match(messages[0], /応募済みとは報告しません/);
  assert.match(messages[1], /Connectorの応募処理が復旧/);
  assert.equal(incidentStore.value(), null);
  assert.deepEqual(selfFixCalls, []);
});

test("同じ未復旧incidentでは警告を重複送信せずself-fixへ昇格する", async () => {
  const incidentStore = memoryIncident({
    code: "UNREACHABLE",
    alert_message_id: "6001",
    opened_at: "2026-08-01T02:58:00.000Z",
  });
  const messages = [];
  const selfFixCalls = [];
  const result = await runOutboundGuardian({
    healthUrl: "http://127.0.0.1:18790/health",
    nowMs: NOW,
    fetchHealth: async () => ({ error: new Error("still down") }),
    incidentStore,
    notify: async (message) => { messages.push(message); return { messageId: "7001" }; },
    recover: async () => false,
    selfFix: async (...args) => selfFixCalls.push(args),
  });
  assert.equal(result.recovered, false);
  assert.deepEqual(messages, []);
  assert.equal(selfFixCalls.length, 1);
  assert.equal(incidentStore.value().alert_message_id, "6001");
});

test("Telegramがmessage IDを返さなければincidentを保存せず成功扱いしない", async () => {
  const incidentStore = memoryIncident();
  await assert.rejects(() => runOutboundGuardian({
    healthUrl: "http://127.0.0.1:18790/health",
    nowMs: NOW,
    fetchHealth: async () => ({ error: new Error("down") }),
    incidentStore,
    notify: async () => ({}),
    recover: async () => true,
    selfFix: async () => {},
  }), /message ID/);
  assert.equal(incidentStore.value(), null);
});

test("launchd installerは宛先必須で、renderへhealth・宛先・workerを固定する", () => {
  const repoRoot = path.resolve(__dirname, "../../..");
  const installer = path.join(repoRoot, "skills/self/install-outbound-runtime-healthcheck-launchd.sh");
  const missing = spawnSync(installer, ["--render"], { encoding: "utf8" });
  assert.notEqual(missing.status, 0);
  assert.match(String(missing.stderr), /telegram-target/);

  const rendered = spawnSync(installer, [
    "--render",
    "--telegram-target", "123456789",
    "--worker-container", "life-manager-local-worker-1",
  ], { encoding: "utf8" });
  assert.equal(rendered.status, 0, rendered.stderr);
  assert.match(rendered.stdout, /LM_OUTBOUND_TELEGRAM_TARGET/);
  assert.match(rendered.stdout, /123456789/);
  assert.match(rendered.stdout, /LM_OUTBOUND_WORKER_CONTAINER/);
  assert.match(rendered.stdout, /life-manager-local-worker-1/);
  assert.match(rendered.stdout, /http:\/\/127\.0\.0\.1:18790\/health/);
});

test("Connector compose overlayはworkerへoutbound capabilityを追加できる", () => {
  const repoRoot = path.resolve(__dirname, "../../..");
  const overlay = fs.readFileSync(
    path.join(repoRoot, "deploy/local/compose.connector.yaml"),
    "utf8",
  );
  assert.match(overlay, /^services:/m);
  assert.match(overlay, /^  worker:/m);
  assert.match(overlay, /LM_CONNECTOR_WORKER_CAPABILITIES/);
  assert.match(overlay, /outbound\.event\.apply/);
  assert.match(overlay, /LM_LUMA_GOOGLE_ACCOUNT/);
});

test("Docker recoveryは指定workerだけをrestartしhealth復帰までboundedに待つ", async () => {
  const spawns = [];
  const health = [
    { error: new Error("starting") },
    { httpStatus: 200, body: healthyBody() },
  ];
  const sleeps = [];
  const recovered = await recoverDockerWorker({
    workerContainer: "life-manager-local-worker-1",
    healthUrl: "http://127.0.0.1:18790/health",
    nowMs: NOW,
    maxPollAgeMs: 120_000,
    attempts: 3,
    spawnSync: (command, args) => {
      spawns.push([command, args]);
      return { status: 0, stdout: "life-manager-local-worker-1\n", stderr: "" };
    },
    fetchHealth: async () => health.shift(),
    sleep: async (ms) => sleeps.push(ms),
  });
  assert.equal(recovered, true);
  assert.deepEqual(spawns, [["docker", ["restart", "life-manager-local-worker-1"]]]);
  assert.deepEqual(sleeps, [1000]);
});

test("Guardian processはhealthyまたは復旧済みならexit 0、未復旧だけexit 1", () => {
  assert.equal(guardianExitCode({ ok: true, code: "HEALTHY" }), 0);
  assert.equal(guardianExitCode({ ok: false, code: "UNREACHABLE", recovered: true }), 0);
  assert.equal(guardianExitCode({ ok: false, code: "UNREACHABLE", recovered: false }), 1);
});
