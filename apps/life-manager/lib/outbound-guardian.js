"use strict";

const path = require("node:path");
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

async function runOutboundGuardian(options = {}) {
  const healthUrl = String(options.healthUrl || DEFAULT_HEALTH_URL);
  const observation = await (options.fetchHealth || fetchWorkerHealth)(healthUrl, options);
  const verdict = classifyOutboundWorkerHealth({ ...observation, nowMs: options.nowMs, maxPollAgeMs: options.maxPollAgeMs });
  if (!verdict.ok) {
    const blocker = `Connector runtime Guardian ${verdict.code} at ${healthUrl}: ${verdict.detail}. Inspect the existing Life Manager worker, database, and outbound.event.apply wiring; fix and verify the real /health endpoint.`;
    await (options.selfFix || invokeSelfFix)("connector-outbound", blocker, options);
  }
  return verdict;
}

async function main(env = process.env) {
  const verdict = await runOutboundGuardian({
    healthUrl: env.LM_OUTBOUND_WORKER_HEALTH_URL || DEFAULT_HEALTH_URL,
    maxPollAgeMs: Number(env.LM_OUTBOUND_MAX_POLL_AGE_MS || DEFAULT_MAX_POLL_AGE_MS),
  });
  process.stdout.write(`${JSON.stringify(verdict)}\n`);
  if (!verdict.ok) process.exitCode = 1;
}

if (require.main === module) main().catch((error) => {
  process.stderr.write(`${String(error && error.stack || error)}\n`);
  process.exitCode = 1;
});

module.exports = { OUTBOUND_CAPABILITY, DEFAULT_HEALTH_URL, DEFAULT_MAX_POLL_AGE_MS, classifyOutboundWorkerHealth, fetchWorkerHealth, invokeSelfFix, runOutboundGuardian };

