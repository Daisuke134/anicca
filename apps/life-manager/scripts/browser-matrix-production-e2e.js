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

function dependency(deps, group, method) {
  if (!deps || !deps[group] || typeof deps[group][method] !== "function") {
    throw new Error("browser matrix production E2E failed");
  }
  return deps[group][method].bind(deps[group]);
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
  const enqueue = dependency(deps, "durableQueue", "enqueue");
  const read = dependency(deps, "durableQueue", "read");
  const execute = dependency(deps, "executor", "run");
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

  for (const [index, target] of targets.entries()) {
    const queued = await enqueue({ ...target, uid });
    const jobId = boundedId(queued && queued.id);
    const execution = await execute({ jobId });
    if (execution && execution.trace_id != null && String(execution.trace_id) !== jobId) {
      throw new Error("browser matrix production E2E failed");
    }
    const evidence = terminalEvidence(await read({ id: jobId }), {
      jobId,
      uid,
      origin: origins[index],
    });
    result.job_ids.push(jobId);
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
  const {
    enqueueBrowserJob,
    claimBrowserJobById,
    readBrowserJob,
  } = require("../lib/browser-job-store.js");
  const { runNextBrowserJob } = require("../lib/browser-job-runtime.js");
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
    executor: {
      async run({ jobId }) {
        return runNextBrowserJob({
          ...storeOptions,
          ...(boundaries.driver ? { driver: boundaries.driver } : {}),
          ...(boundaries.sendMessage ? { sendMessage: boundaries.sendMessage } : {}),
          ...(boundaries.sendPhoto ? { sendPhoto: boundaries.sendPhoto } : {}),
          telegramToken: env.LM_TELEGRAM_BOT_TOKEN,
          claimJob: () => claimBrowserJobById(jobId, storeOptions),
        });
      },
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
