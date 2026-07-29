"use strict";

const net = require("node:net");
const { createHash } = require("node:crypto");

const CATEGORIES = Object.freeze(["booking", "inquiry", "application"]);
const URL_ENV = Object.freeze({
  booking: "BROWSER_MATRIX_BOOKING_URL",
  inquiry: "BROWSER_MATRIX_INQUIRY_URL",
  application: "BROWSER_MATRIX_APPLICATION_URL",
});
const REQUIRED_ENV = Object.freeze([
  ...Object.values(URL_ENV),
  "BROWSER_MATRIX_TENANT_UID",
  "BROWSER_MATRIX_TELEGRAM_CHAT_ID",
  "LM_FEEDBACK_DATABASE_URL",
  "LM_TELEGRAM_BOT_TOKEN",
  "GEMINI_API_KEY",
  "LM_AGENT_BROWSER_EMAIL",
  "LM_AGENT_BROWSER_NAME",
]);
const PROVIDER_RECEIPT_KEYS = Object.freeze([
  "confirmation_id",
  "confirmed",
  "current_url",
  "handoff_reason",
  "handoff_required",
  "status",
]);
const OUTPUT_KEYS = Object.freeze([
  "categories",
  "job_ids",
  "provider_origins",
  "steel_session_ids",
  "telegram_evidence_ids",
  "provider_receipt_hashes",
  "released",
]);
// Mirrors TERMINAL_STATUSES in ../lib/browser-job-store.js; only "completed" passes.
const TERMINAL_STATUSES = Object.freeze([
  "completed",
  "possibly_completed",
  "handoff_required",
  "failed",
]);
const POLL_ENV = Object.freeze({
  timeoutMs: "BROWSER_MATRIX_POLL_TIMEOUT_MS",
  intervalMs: "BROWSER_MATRIX_POLL_INTERVAL_MS",
});
const DEFAULT_POLL_TIMEOUT_MS = 900_000;
const MAX_POLL_TIMEOUT_MS = 3_600_000;
const DEFAULT_POLL_INTERVAL_MS = 5_000;
const MAX_POLL_INTERVAL_MS = 60_000;

class ConfigurationError extends Error {}

function requiredEnvironment(env) {
  const missing = REQUIRED_ENV.filter((name) => !String(env && env[name] || "").trim());
  if (missing.length) {
    throw new ConfigurationError(`Missing required environment variables: ${missing.join(", ")}`);
  }
}

function publicTarget(raw) {
  let value;
  try { value = new URL(String(raw || "")); } catch {
    throw new ConfigurationError("browser matrix target must be a public HTTPS URL");
  }
  const host = value.hostname.toLowerCase();
  const unbracketed = host.startsWith("[") && host.endsWith("]")
    ? host.slice(1, -1)
    : host;
  if (
    value.protocol !== "https:" ||
    value.username ||
    value.password ||
    !host ||
    host === "localhost" ||
    host.endsWith(".local") ||
    host.endsWith(".internal") ||
    net.isIP(unbracketed) !== 0
  ) {
    throw new ConfigurationError("browser matrix target must be a public HTTPS URL");
  }
  value.username = "";
  value.password = "";
  value.hash = "";
  return value;
}

function boundedMilliseconds(env, key, fallback, max) {
  const name = POLL_ENV[key];
  const raw = String(env && env[name] || "").trim();
  if (!raw) return fallback;
  if (!/^[0-9]{1,9}$/.test(raw)) {
    throw new ConfigurationError(`browser matrix poll setting ${name} must be a positive integer of milliseconds`);
  }
  const value = Number(raw);
  if (!Number.isSafeInteger(value) || value < 1 || value > max) {
    throw new ConfigurationError(`browser matrix poll setting ${name} must be between 1 and ${max} milliseconds`);
  }
  return value;
}

function pollSettings(env) {
  const timeoutMs = boundedMilliseconds(env, "timeoutMs", DEFAULT_POLL_TIMEOUT_MS, MAX_POLL_TIMEOUT_MS);
  const intervalMs = boundedMilliseconds(env, "intervalMs", DEFAULT_POLL_INTERVAL_MS, MAX_POLL_INTERVAL_MS);
  if (intervalMs > timeoutMs) {
    throw new ConfigurationError(
      `browser matrix poll setting ${POLL_ENV.intervalMs} must not exceed ${POLL_ENV.timeoutMs}`,
    );
  }
  return Object.freeze({ timeoutMs, intervalMs, attempts: Math.ceil(timeoutMs / intervalMs) + 1 });
}

function dependency(deps, group, method) {
  if (!deps || !deps[group] || typeof deps[group][method] !== "function") {
    throw new Error("browser matrix production E2E failed");
  }
  return deps[group][method].bind(deps[group]);
}

function optionalDependency(deps, group, method, fallback) {
  const holder = deps && Object.prototype.hasOwnProperty.call(deps, group) ? deps[group] : null;
  if (holder && typeof holder[method] === "function") return holder[method].bind(holder);
  return fallback;
}

function defaultSleep(ms) {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, ms);
    if (timer && typeof timer.unref === "function") timer.unref();
  });
}

function boundedId(value) {
  const id = String(value == null ? "" : value).trim();
  if (!id || id.length > 200) throw new Error("browser matrix production E2E failed");
  return id;
}

function canonicalProviderReceipt(value, expectedOrigin) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("browser matrix production E2E failed");
  }
  if (Object.keys(value).sort().join(",") !== [...PROVIDER_RECEIPT_KEYS].sort().join(",")) {
    throw new Error("browser matrix production E2E failed");
  }
  const current = publicTarget(value.current_url);
  const status = String(value.status || "").trim();
  if (
    value.confirmed !== true ||
    value.handoff_required !== false ||
    value.handoff_reason != null ||
    !status ||
    status === "unknown" ||
    current.origin !== expectedOrigin
  ) {
    throw new Error("browser matrix production E2E failed");
  }
  return {
    confirmed: true,
    status: status.slice(0, 100),
    confirmation_id: value.confirmation_id == null
      ? null
      : boundedId(value.confirmation_id),
    current_url: `${current.origin}${current.pathname}`,
    handoff_required: false,
    handoff_reason: null,
  };
}

function terminalEvidence(row, expected) {
  if (!row || row.id !== expected.jobId || row.uid !== expected.uid || row.status !== "completed") {
    throw new Error("browser matrix production E2E failed");
  }
  const receipt = row.receipt;
  if (!receipt || typeof receipt !== "object" || receipt.steel_released !== true) {
    throw new Error("browser matrix production E2E failed");
  }
  const selectedOrigin = String(receipt.selected_origin || "");
  if (selectedOrigin !== expected.origin) throw new Error("browser matrix production E2E failed");
  const provider = canonicalProviderReceipt(receipt.provider_receipt, expected.origin);
  return {
    sessionId: boundedId(receipt.session_id),
    evidenceId: boundedId(receipt.evidence_message_id),
    providerHash: createHash("sha256").update(JSON.stringify(provider)).digest("hex"),
  };
}

function isTerminal(row) {
  return Boolean(row) && TERMINAL_STATUSES.includes(String(row.status || ""));
}

// The resident production browser loop is the only claimer: this verifier only waits.
async function pollTerminalRows(read, jobIds, poll) {
  const rows = new Array(jobIds.length).fill(null);
  const startedAt = poll.now();
  for (let attempt = 0; attempt < poll.attempts; attempt += 1) {
    let pending = 0;
    for (const [index, jobId] of jobIds.entries()) {
      if (rows[index]) continue;
      const row = await read({ id: jobId });
      if (isTerminal(row)) rows[index] = row;
      else pending += 1;
    }
    if (!pending) return rows;
    if (poll.now() - startedAt >= poll.timeoutMs) break;
    await poll.sleep(poll.intervalMs);
  }
  throw new Error("browser matrix production E2E failed");
}

async function runBrowserMatrixProductionE2E({ env = process.env, deps } = {}) {
  requiredEnvironment(env);
  const targets = CATEGORIES.map((category) => ({
    category,
    url: publicTarget(env[URL_ENV[category]]).toString(),
  }));
  const origins = targets.map(({ url }) => new URL(url).origin);
  if (new Set(origins).size !== CATEGORIES.length) {
    throw new ConfigurationError("browser matrix targets must use distinct provider origins");
  }
  const settings = pollSettings(env);
  const enqueue = dependency(deps, "durableQueue", "enqueue");
  const read = dependency(deps, "durableQueue", "read");
  const poll = {
    ...settings,
    sleep: optionalDependency(deps, "clock", "sleep", defaultSleep),
    now: optionalDependency(deps, "clock", "now", () => Date.now()),
  };
  const uid = String(env.BROWSER_MATRIX_TENANT_UID);
  const result = {
    categories: [...CATEGORIES],
    job_ids: [],
    provider_origins: [],
    steel_session_ids: [],
    telegram_evidence_ids: [],
    provider_receipt_hashes: [],
    released: false,
  };

  for (const target of targets) {
    const queued = await enqueue({ ...target, uid });
    result.job_ids.push(boundedId(queued && queued.id));
  }
  const rows = await pollTerminalRows(read, result.job_ids, poll);
  for (const [index, row] of rows.entries()) {
    const evidence = terminalEvidence(row, {
      jobId: result.job_ids[index],
      uid,
      origin: origins[index],
    });
    result.provider_origins.push(origins[index]);
    result.steel_session_ids.push(evidence.sessionId);
    result.telegram_evidence_ids.push(evidence.evidenceId);
    result.provider_receipt_hashes.push(evidence.providerHash);
  }
  if (
    new Set(result.steel_session_ids).size !== CATEGORIES.length ||
    new Set(result.provider_receipt_hashes).size !== CATEGORIES.length
  ) {
    throw new Error("browser matrix production E2E failed");
  }
  result.released = true;
  return Object.freeze(result);
}

function goalFor(category, url) {
  if (category === "booking") {
    return `Book exactly one zero-cost controlled appointment at ${url} using the agent-owned identity. Choose the earliest available slot at least 24 hours from now.`;
  }
  if (category === "inquiry") {
    return `Submit exactly one non-binding controlled inquiry at ${url} using the agent-owned identity. For the message use: Browser matrix inquiry verification.`;
  }
  return `Submit exactly one non-binding controlled application at ${url} using the agent-owned identity. For required non-personal text use: Browser matrix application verification.`;
}

function makeProductionDeps(env, boundaries = {}) {
  const { enqueueBrowserJob, readBrowserJob } = require("../lib/browser-job-store.js");
  const storeOptions = typeof boundaries.query === "function" ? { query: boundaries.query } : {};
  let sequence = 0;
  return {
    durableQueue: {
      async enqueue({ category, url, uid }) {
        const suffix = `${Date.now()}-${++sequence}`;
        const queued = await enqueueBrowserJob({
          uid,
          chatId: String(env.BROWSER_MATRIX_TELEGRAM_CHAT_ID),
          messageId: `browser-matrix-${category}-${suffix}`,
          updateId: `browser-matrix-${category}-${suffix}`,
          rawPrompt: `Run controlled browser matrix category ${category}.`,
          classification: {
            locale: "en",
            goal: goalFor(category, url),
            actionKind: category,
            requiresLogin: false,
            principalKind: "none",
          },
        }, storeOptions);
        return { id: queued && queued.job && queued.job.id };
      },
      async read({ id }) {
        return readBrowserJob(id, storeOptions);
      },
    },
    clock: {
      sleep: defaultSleep,
      now: () => Date.now(),
    },
  };
}

function cliError(error) {
  return error instanceof ConfigurationError
    ? error.message
    : "browser matrix production E2E failed";
}

if (require.main === module) {
  runBrowserMatrixProductionE2E({
    env: process.env,
    deps: makeProductionDeps(process.env),
  })
    .then((result) => process.stdout.write(`${JSON.stringify(result)}\n`))
    .catch((error) => {
      process.stderr.write(`${cliError(error)}\n`);
      process.exitCode = 1;
    });
}

module.exports = {
  OUTPUT_KEYS,
  makeProductionDeps,
  runBrowserMatrixProductionE2E,
};
