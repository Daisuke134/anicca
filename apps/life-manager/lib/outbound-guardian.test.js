"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const {
  OUTBOUND_CAPABILITY,
  classifyOutboundWorkerHealth,
  guardianExitCode,
  parseOpenClawMessageId,
  notifyOpenClaw,
  notifyOpenClawGateway,
  notifyOpenClawPhoto,
  recoverDockerWorker,
  runOutboundGuardian,
} = require("./outbound-guardian.js");

const NOW = Date.parse("2026-08-01T03:00:00.000Z");

test("legacy OpenClaw text delivery keeps message CLI and needs no idempotency key", async () => {
  const receipt = await notifyOpenClaw("wake report", {
    telegramTarget: "fixture-target",
    spawnSync(command, args) {
      assert.equal(command, "openclaw");
      assert.deepEqual(args, [
        "message", "send", "--channel", "telegram", "--target", "fixture-target",
        "--message", "wake report", "--json",
      ]);
      return { status: 0, stdout: JSON.stringify({ messageId: "321" }), stderr: "" };
    },
  });
  assert.deepEqual(receipt, { messageId: "321" });
});

test("report text delivery uses Gateway send with the caller wake id", async () => {
  const receipt = await notifyOpenClawGateway("wake report", {
    telegramTarget: "123456789",
    idempotencyKey: "wake-20260810-001",
    spawnSync(command, args, options) {
      assert.equal(command, "openclaw");
      assert.deepEqual(args.slice(0, 5), ["gateway", "call", "send", "--timeout", "60000"]);
      assert.equal(options.timeout, 65_000);
      assert.equal(args[5], "--params");
      assert.deepEqual(JSON.parse(args[6]), {
        channel: "telegram", to: "123456789", message: "wake report", idempotencyKey: "wake-20260810-001",
      });
      assert.equal(args[7], "--json");
      return { status: 0, stdout: JSON.stringify({ messageId: "322" }), stderr: "" };
    },
  });
  assert.deepEqual(receipt, { messageId: "322" });
});

test("report Gateway child-process timeout folds to the existing safe failure", async () => {
  const privateMessage = "private gateway timeout";
  const privateStderr = "private gateway stderr";
  await assert.rejects(() => notifyOpenClawGateway("wake report", {
    telegramTarget: "123456789",
    idempotencyKey: "wake-test-timeout",
    spawnSync() {
      const error = new Error(privateMessage);
      error.code = "ETIMEDOUT";
      return { status: null, stdout: "", stderr: privateStderr, error };
    },
  }), (error) => {
    assert.equal(error.message, "Telegram report delivery failed");
    assert.doesNotMatch(error.message, /private gateway timeout|private gateway stderr/);
    return true;
  });
});

test("report Gateway delivery rejects malformed target or wake ID before spawn", async () => {
  for (const telegramTarget of ["fixture-target", "1234", ""]) {
    let spawns = 0;
    await assert.rejects(() => notifyOpenClawGateway("wake report", {
      telegramTarget, idempotencyKey: "wake-20260810-001", spawnSync() { spawns += 1; },
    }), /Telegram report delivery failed/);
    assert.equal(spawns, 0);
  }
  for (const idempotencyKey of ["", "x", "bad key", null, 9]) {
    let spawns = 0;
    await assert.rejects(() => notifyOpenClawGateway("wake report", {
      telegramTarget: "123456789", idempotencyKey, spawnSync() { spawns += 1; },
    }), /Telegram report delivery failed/);
    assert.equal(spawns, 0);
  }
});

test("report Gateway delivery hides failure stderr and still requires a positive top-level message ID", async () => {
  const target = "123456789";
  const message = `private report ${target}`;
  await assert.rejects(() => notifyOpenClawGateway(message, {
    telegramTarget: target,
    idempotencyKey: "wake-test-stderr",
    spawnSync() { return { status: 1, stdout: "", stderr: `failure ${target} ${message}` }; },
  }), (error) => {
    assert.equal(error.message, "Telegram report delivery failed");
    assert.doesNotMatch(error.message, /private report|123456789|failure/);
    return true;
  });
  for (const stdout of ["{}", '{"messageId":0}', '{"messageId":"no"}']) {
    await assert.rejects(() => notifyOpenClawGateway("wake report", {
      telegramTarget: target, idempotencyKey: "wake-test-receipt",
      spawnSync() { return { status: 0, stdout, stderr: "" }; },
    }), /Telegram report delivery failed/);
  }
});

test("OpenClaw photo delivery uses Gateway send with a private temporary PNG and returns a positive message ID", async () => {
  const bytes = Buffer.alloc(5_000, 0x61);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(bytes);
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-outbound-photo-root-"));
  let mediaPath;
  const receipt = await notifyOpenClawPhoto(bytes, {
    env: { LM_DATA_DIR: dataDir },
    telegramTarget: "123456789",
    caption: "registered evidence",
    idempotencyKey: "connector-evidence:abc123",
    spawnSync(command, args) {
      assert.equal(command, "openclaw");
      assert.deepEqual(args.slice(0, 5), [
        "gateway", "call", "send", "--timeout", "60000",
      ]);
      assert.equal(args[5], "--params");
      const params = JSON.parse(args[6]);
      assert.equal(params.channel, "telegram");
      assert.equal(params.to, "123456789");
      assert.equal(params.message, "registered evidence");
      assert.equal(params.forceDocument, true);
      assert.equal(params.idempotencyKey, "connector-evidence:abc123");
      mediaPath = params.mediaUrl;
      assert.match(mediaPath, new RegExp(`${dataDir}/media/connector-telegram-photo-`));
      assert.equal(fs.statSync(path.dirname(mediaPath)).mode & 0o777, 0o700);
      assert.equal(fs.statSync(mediaPath).mode & 0o777, 0o600);
      assert.deepEqual(fs.readFileSync(mediaPath), bytes);
      assert.equal(args[7], "--json");
      return { status: 0, stdout: JSON.stringify({ messageId: "322" }), stderr: "" };
    },
  });
  assert.deepEqual(receipt, { messageId: "322" });
  assert.equal(fs.existsSync(mediaPath), false);
});

test("OpenClaw photo delivery rejects malformed target or idempotency key before spawn", async () => {
  const bytes = Buffer.alloc(5_000, 0x61);
  for (const telegramTarget of ["fixture-target", "1234", "", null, 123456789]) {
    let spawns = 0;
    await assert.rejects(() => notifyOpenClawPhoto(bytes, {
      telegramTarget,
      idempotencyKey: "connector-evidence:abc123",
      spawnSync() { spawns += 1; },
    }), /Telegram photo delivery invalid/);
    assert.equal(spawns, 0);
  }
  for (const idempotencyKey of ["", "x", "bad key", null, 9]) {
    let spawns = 0;
    await assert.rejects(() => notifyOpenClawPhoto(bytes, {
      telegramTarget: "123456789",
      idempotencyKey,
      spawnSync() { spawns += 1; },
    }), /Telegram photo delivery invalid/);
    assert.equal(spawns, 0);
  }
});

test("photo delivery refuses a legacy Life Manager data root before spawning", async () => {
  const bytes = Buffer.from("not-an-image");
  let spawns = 0;
  await assert.rejects(() => notifyOpenClawPhoto(bytes, {
    env: { LM_DATA_DIR: path.join(os.tmpdir(), ".openclaw") },
    telegramTarget: "123456789",
    idempotencyKey: "connector-evidence:legacy-root",
    spawnSync() { spawns += 1; },
  }), /Telegram photo delivery failed/);
  assert.equal(spawns, 0);
});

test("photo delivery refuses a Life Manager root symlinked into a legacy root", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-outbound-symlink-"));
  const legacy = path.join(root, ".openclaw");
  const linked = path.join(root, "data");
  fs.mkdirSync(legacy);
  fs.symlinkSync(legacy, linked, "dir");
  let spawns = 0;
  await assert.rejects(() => notifyOpenClawPhoto(Buffer.from("not-an-image"), {
    env: { LM_DATA_DIR: linked },
    telegramTarget: "123456789",
    idempotencyKey: "connector-evidence:symlink-root",
    spawnSync() { spawns += 1; },
  }), /Telegram photo delivery failed/);
  assert.equal(spawns, 0);
});

test("OpenClaw photo delivery sanitizes failures, requires a positive top-level message ID, and removes media", async () => {
  const bytes = Buffer.alloc(5_000, 0x61);
  const target = "123456789";
  const caption = `private caption ${target}`;
  const idempotencyKey = "connector-evidence:secret123";
  let mediaPath;
  await assert.rejects(() => notifyOpenClawPhoto(bytes, {
    telegramTarget: target,
    caption,
    idempotencyKey,
    spawnSync(command, args) {
      assert.equal(command, "openclaw");
      const paramsIndex = args.indexOf("--params");
      mediaPath = paramsIndex === -1
        ? args[args.indexOf("--media") + 1]
        : JSON.parse(args[paramsIndex + 1]).mediaUrl;
      return { status: 1, stdout: "", stderr: `private stderr ${target} ${caption} ${mediaPath}` };
    },
  }), (error) => {
    assert.equal(error.message, "Telegram photo delivery failed");
    assert.doesNotMatch(error.message, /private stderr|private caption|123456789|connector-evidence:secret123|registered-page\.png/);
    return true;
  });
  assert.equal(fs.existsSync(mediaPath), false);

  for (const stdout of ["{}", '{"messageId":0}', '{"messageId":"no"}']) {
    await assert.rejects(() => notifyOpenClawPhoto(bytes, {
      telegramTarget: target,
      caption,
      idempotencyKey: "connector-evidence:receipt123",
      spawnSync(command, args) {
        const paramsIndex = args.indexOf("--params");
        mediaPath = paramsIndex === -1
          ? args[args.indexOf("--media") + 1]
          : JSON.parse(args[paramsIndex + 1]).mediaUrl;
        return { status: 0, stdout, stderr: "" };
      },
    }), /Telegram photo delivery failed/);
    assert.equal(fs.existsSync(mediaPath), false);
  }
});

test("OpenClaw photo delivery does not return a receipt when temporary-directory cleanup fails", async () => {
  const bytes = Buffer.alloc(5_000, 0x61);
  let cleanupPath;
  let cleanupCalls = 0;
  await assert.rejects(() => notifyOpenClawPhoto(bytes, {
    telegramTarget: "123456789",
    caption: "cleanup failure evidence",
    idempotencyKey: "connector-evidence:cleanup123",
    spawnSync() {
      return { status: 0, stdout: JSON.stringify({ messageId: "323" }), stderr: "" };
    },
    rmSync(target, options) {
      cleanupPath = target;
      cleanupCalls += 1;
      fs.rmSync(target, options);
      throw new Error("injected cleanup failure");
    },
  }), (error) => {
    assert.equal(error.message, "Telegram photo delivery failed");
    assert.doesNotMatch(error.message, /cleanup failure evidence|injected cleanup failure|registered-page\.png/);
    return true;
  });
  assert.equal(cleanupCalls, 1);
  assert.equal(fs.existsSync(cleanupPath), false);
});

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

test("last_poll_atが壊れている、遠い未来、古い場合はhealthyにしない", () => {
  for (const [lastPollAt, code] of [
    ["not-a-date", "INVALID_LAST_POLL"],
    ["2026-08-01T03:00:11.001Z", "INVALID_LAST_POLL"],
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

test("worker VMの小さな時計ずれはfresh pollとして扱う", () => {
  assert.deepEqual(classifyOutboundWorkerHealth({
    httpStatus: 200,
    body: healthyBody({ last_poll_at: "2026-08-01T03:00:04.000Z" }),
    nowMs: NOW,
    maxPollAgeMs: 120_000,
  }), {
    ok: true,
    code: "HEALTHY",
    workerId: "local-runtime-worker",
    pollAgeMs: 0,
  });
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

test("Connectorはcontainer railを持たない", () => {
  const repoRoot = path.resolve(__dirname, "../../..");
  for (const removed of [
    "deploy/local/compose.connector.yaml",
    "apps/life-manager/scripts/deploy-connector-runtime.sh",
    "apps/life-manager/scripts/connector-host-bridge-server.js",
    "apps/life-manager/scripts/connector-host-bridge-boot.sh",
    "apps/life-manager/scripts/install-connector-host-bridge-launchd.sh",
  ]) {
    assert.equal(fs.existsSync(path.join(repoRoot, removed)), false, removed);
  }
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
