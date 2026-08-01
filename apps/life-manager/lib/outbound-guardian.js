"use strict";

const path = require("node:path");
const fs = require("node:fs");
const { spawnSync } = require("node:child_process");

const OUTBOUND_CAPABILITY = "outbound.event.apply";
const DEFAULT_HEALTH_URL = "http://127.0.0.1:18790/health";
const DEFAULT_MAX_POLL_AGE_MS = 120_000;

function unhealthy(code, detail) {
  return { ok: false, code, detail };
}

function classifyOutboundWorkerHealth(input = {}) {
  if (input.error) return unhealthy("UNREACHABLE", String(input.error.message || input.error));
  if (input.httpStatus !== 200) return unhealthy("HTTP_UNHEALTHY", `health endpoint returned ${input.httpStatus || "no status"}`);
  const body = input.body;
  if (!body || typeof body !== "object" || Array.isArray(body)) return unhealthy("INVALID_PAYLOAD", "health endpoint did not return a JSON object");
  if (body.ok !== true) return unhealthy("HTTP_UNHEALTHY", "worker reported ok=false");
  if (body.role !== "worker") return unhealthy("WRONG_ROLE", `expected worker, got ${body.role || "missing"}`);
  if (!Array.isArray(body.capabilities) || !body.capabilities.includes(OUTBOUND_CAPABILITY)) {
    return unhealthy("MISSING_CAPABILITY", `${OUTBOUND_CAPABILITY} is not assigned to this worker`);
  }
  const nowMs = Number.isFinite(input.nowMs) ? input.nowMs : Date.now();
  const lastPollMs = Date.parse(String(body.last_poll_at || ""));
  const pollAgeMs = nowMs - lastPollMs;
  if (!Number.isFinite(lastPollMs) || pollAgeMs < 0) return unhealthy("INVALID_LAST_POLL", `invalid last_poll_at: ${body.last_poll_at || "missing"}`);
  const maxPollAgeMs = Number.isFinite(input.maxPollAgeMs) ? input.maxPollAgeMs : DEFAULT_MAX_POLL_AGE_MS;
  if (pollAgeMs > maxPollAgeMs) return unhealthy("STALE_POLL", `last worker poll was ${pollAgeMs}ms ago`);
  return { ok: true, code: "HEALTHY", workerId: String(body.worker_id || ""), pollAgeMs };
}

async function fetchWorkerHealth(healthUrl, options = {}) {
  const fetchImpl = options.fetchImpl || globalThis.fetch;
  try {
    const response = await fetchImpl(healthUrl, {
      signal: AbortSignal.timeout(Number(options.timeoutMs || 10_000)),
      redirect: "error",
    });
    let body = null;
    try { body = await response.json(); } catch { body = null; }
    return { httpStatus: response.status, body };
  } catch (error) {
    return { error };
  }
}

async function invokeSelfFix(loopName, blocker, options = {}) {
  const repoRoot = options.repoRoot || path.resolve(__dirname, "../../..");
  const script = path.join(repoRoot, "skills/self/self-fix.sh");
  const spawn = options.spawnSync || spawnSync;
  const result = spawn("/bin/bash", [script, loopName, blocker], {
    cwd: repoRoot,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  if (!result || result.status !== 0) throw new Error(String(result && result.stderr || "self-fix launch failed").trim());
  return String(result.stdout || "").trim();
}

function parseOpenClawMessageId(output) {
  let value = output;
  if (typeof output === "string") {
    try { value = JSON.parse(output); } catch { value = null; }
  }
  const raw = value && value.messageId;
  const numeric = Number(raw);
  if (!Number.isSafeInteger(numeric) || numeric <= 0) {
    throw new Error("Telegram delivery needs a positive message ID");
  }
  return String(numeric);
}

function incidentAlert(verdict) {
  return [
    "⚠️ Connectorの応募処理が停止しました",
    "イベント応募を処理するLife Manager workerを正常に確認できません。",
    `状態: ${verdict.code}`,
    "自動復旧を開始しました。確認できていない応募を応募済みとは報告しません。",
  ].join("\n");
}

function recoveryAlert() {
  return [
    "✅ Connectorの応募処理が復旧しました",
    "イベント応募workerへの接続と定期処理を再確認しました。",
    "停止中に未確認だった応募は、証拠を確認してから処理を再開します。",
  ].join("\n");
}

function notificationMessageId(receipt) {
  if (typeof receipt === "string") return parseOpenClawMessageId(receipt);
  return parseOpenClawMessageId(JSON.stringify(receipt || {}));
}

function createFileIncidentStore(filePath) {
  const target = path.resolve(filePath);
  return {
    async load() {
      try { return JSON.parse(fs.readFileSync(target, "utf8")); } catch { return null; }
    },
    async save(value) {
      fs.mkdirSync(path.dirname(target), { recursive: true });
      const temp = `${target}.${process.pid}.tmp`;
      fs.writeFileSync(temp, `${JSON.stringify(value)}\n`, { mode: 0o600 });
      fs.renameSync(temp, target);
    },
    async clear() {
      try { fs.unlinkSync(target); } catch (error) {
        if (error && error.code !== "ENOENT") throw error;
      }
    },
  };
}

async function notifyOpenClaw(message, options = {}) {
  const target = String(options.telegramTarget || "").trim();
  if (!target) throw new Error("Telegram target is required");
  const spawn = options.spawnSync || spawnSync;
  const result = spawn("openclaw", [
    "message", "send", "--channel", "telegram", "--target", target,
    "--message", message, "--json",
  ], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
  if (!result || result.status !== 0) {
    throw new Error(String(result && result.stderr || "Telegram delivery failed").trim());
  }
  return { messageId: parseOpenClawMessageId(String(result.stdout || "")) };
}

async function recoverDockerWorker(options = {}) {
  const container = String(options.workerContainer || "").trim();
  if (!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(container)) return false;
  const spawn = options.spawnSync || spawnSync;
  const result = spawn("docker", ["restart", container], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  if (!result || result.status !== 0) return false;
  const attempts = Number.isSafeInteger(options.attempts) ? options.attempts : 30;
  const sleep = options.sleep || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  const readHealth = options.fetchHealth || fetchWorkerHealth;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const observation = await readHealth(options.healthUrl || DEFAULT_HEALTH_URL, options);
    const verdict = classifyOutboundWorkerHealth({
      ...observation,
      nowMs: options.nowMs,
      maxPollAgeMs: options.maxPollAgeMs,
    });
    if (verdict.ok) return true;
    if (attempt + 1 < attempts) await sleep(1000);
  }
  return false;
}

async function runOutboundGuardian(options = {}) {
  const healthUrl = String(options.healthUrl || DEFAULT_HEALTH_URL);
  const observation = await (options.fetchHealth || fetchWorkerHealth)(healthUrl, options);
  const verdict = classifyOutboundWorkerHealth({ ...observation, nowMs: options.nowMs, maxPollAgeMs: options.maxPollAgeMs });
  const blocker = `Connector runtime Guardian ${verdict.code} at ${healthUrl}: ${verdict.detail}. Inspect the existing Life Manager worker, database, and outbound.event.apply wiring; fix and verify the real /health endpoint.`;
  const managedIncident = options.incidentStore && typeof options.notify === "function";
  if (!managedIncident) {
    if (!verdict.ok) await (options.selfFix || invokeSelfFix)("connector-outbound", blocker, options);
    return verdict;
  }

  const incident = await options.incidentStore.load();
  if (verdict.ok) {
    if (!incident) return verdict;
    const recoveryMessageId = notificationMessageId(await options.notify(recoveryAlert()));
    await options.incidentStore.clear();
    return {
      ...verdict,
      recovered: true,
      telegram: {
        alertMessageId: String(incident.alert_message_id),
        recoveryMessageId,
      },
    };
  }

  let alertMessageId = incident && String(incident.alert_message_id || "");
  if (!alertMessageId) {
    alertMessageId = notificationMessageId(await options.notify(incidentAlert(verdict)));
    await options.incidentStore.save({
      code: verdict.code,
      alert_message_id: alertMessageId,
      opened_at: new Date(Number.isFinite(options.nowMs) ? options.nowMs : Date.now()).toISOString(),
    });
  }

  const restartAttempted = typeof options.recover === "function"
    ? await options.recover(verdict)
    : false;
  if (restartAttempted) {
    const after = await (options.fetchHealth || fetchWorkerHealth)(healthUrl, options);
    const recoveredVerdict = classifyOutboundWorkerHealth({
      ...after,
      nowMs: options.nowMs,
      maxPollAgeMs: options.maxPollAgeMs,
    });
    if (recoveredVerdict.ok) {
      const recoveryMessageId = notificationMessageId(await options.notify(recoveryAlert()));
      await options.incidentStore.clear();
      return {
        ...verdict,
        recovered: true,
        telegram: { alertMessageId, recoveryMessageId },
      };
    }
  }
  await (options.selfFix || invokeSelfFix)("connector-outbound", blocker, options);
  return {
    ...verdict,
    recovered: false,
    telegram: { alertMessageId, recoveryMessageId: null },
  };
}

async function main(env = process.env) {
  const healthUrl = env.LM_OUTBOUND_WORKER_HEALTH_URL || DEFAULT_HEALTH_URL;
  const stateRoot = env.LM_OUTBOUND_STATE_DIR
    || path.join(env.HOME || process.env.HOME || ".", ".local/state/life-manager/state");
  const shared = {
    healthUrl,
    maxPollAgeMs: Number(env.LM_OUTBOUND_MAX_POLL_AGE_MS || DEFAULT_MAX_POLL_AGE_MS),
  };
  const verdict = await runOutboundGuardian({
    ...shared,
    incidentStore: createFileIncidentStore(path.join(stateRoot, "outbound-guardian-incident.json")),
    notify: (message) => notifyOpenClaw(message, {
      telegramTarget: env.LM_OUTBOUND_TELEGRAM_TARGET,
    }),
    recover: () => recoverDockerWorker({
      ...shared,
      workerContainer: env.LM_OUTBOUND_WORKER_CONTAINER,
    }),
  });
  process.stdout.write(`${JSON.stringify(verdict)}\n`);
  if (!verdict.ok) process.exitCode = 1;
}

if (require.main === module) main().catch((error) => {
  process.stderr.write(`${String(error && error.stack || error)}\n`);
  process.exitCode = 1;
});

module.exports = {
  OUTBOUND_CAPABILITY,
  DEFAULT_HEALTH_URL,
  DEFAULT_MAX_POLL_AGE_MS,
  classifyOutboundWorkerHealth,
  fetchWorkerHealth,
  invokeSelfFix,
  parseOpenClawMessageId,
  createFileIncidentStore,
  notifyOpenClaw,
  recoverDockerWorker,
  runOutboundGuardian,
};
