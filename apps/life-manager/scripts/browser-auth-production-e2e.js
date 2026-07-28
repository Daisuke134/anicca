"use strict";

const { createHash } = require("node:crypto");

const MODES = new Set([
  "seed-two-tenant-contexts",
  "verify-two-tenant-contexts",
  "verify-expired-handoff",
]);
const OUTPUT_KEYS = [
  "mode",
  "tenant_count",
  "origin",
  "context_hashes",
  "job_ids",
  "steel_session_ids",
  "telegram_evidence_ids",
  "released",
];
const REQUIRED_ENV = [
  "BROWSER_AUTH_PRODUCTION_ORIGIN",
  "BROWSER_AUTH_TENANT_A_UID",
  "BROWSER_AUTH_TENANT_B_UID",
  "LM_BROWSER_SESSION_KEY",
  "LM_FEEDBACK_DATABASE_URL",
  "LM_TELEGRAM_BOT_TOKEN",
  "BROWSER_AUTH_TELEGRAM_CHAT_ID",
];

class ConfigurationError extends Error {}

function requiredEnvironment(env) {
  const missing = REQUIRED_ENV.filter((name) => !String(env && env[name] || "").trim());
  if (missing.length) {
    throw new ConfigurationError(`Missing required environment variables: ${missing.join(", ")}`);
  }
}

function originOf(value) {
  let parsed;
  try { parsed = new URL(String(value || "")); } catch { throw new ConfigurationError("BROWSER_AUTH_PRODUCTION_ORIGIN must be a public HTTPS origin"); }
  if (parsed.protocol !== "https:" || parsed.username || parsed.password || parsed.origin === "null") {
    throw new ConfigurationError("BROWSER_AUTH_PRODUCTION_ORIGIN must be a public HTTPS origin");
  }
  return parsed.origin;
}

function opaqueHash(value) {
  return createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

function requiredDependency(deps, group, method) {
  if (!deps || !deps[group] || typeof deps[group][method] !== "function") {
    throw new Error("browser auth production dependency unavailable");
  }
  return deps[group][method].bind(deps[group]);
}

function boundedId(value, kind) {
  const id = String(value == null ? "" : value).trim();
  if (!id || id.length > 200) throw new Error(`browser auth ${kind} unavailable`);
  return id;
}

async function runBrowserAuthProductionE2E({ mode, env = process.env, deps } = {}) {
  if (!MODES.has(mode)) throw new ConfigurationError(`Unknown browser auth production E2E mode: ${String(mode)}`);
  requiredEnvironment(env);
  const origin = originOf(env.BROWSER_AUTH_PRODUCTION_ORIGIN);
  const tenantInputs = [
    { tenant: "tenant-a", uid: String(env.BROWSER_AUTH_TENANT_A_UID), principalKind: "agent_owned" },
    { tenant: "tenant-b", uid: String(env.BROWSER_AUTH_TENANT_B_UID), principalKind: "agent_owned" },
  ];
  if (tenantInputs[0].uid === tenantInputs[1].uid) {
    throw new ConfigurationError("BROWSER_AUTH_TENANT_A_UID and BROWSER_AUTH_TENANT_B_UID must differ");
  }

  const readTenantAuth = requiredDependency(deps, "authStore", "readTenantAuth");
  const createSession = requiredDependency(deps, "steel", "createSession");
  const createContext = requiredDependency(deps, "steel", "createContext");
  const releaseSession = requiredDependency(deps, "steel", "releaseSession");
  const enqueue = requiredDependency(deps, "durableQueue", "enqueue");
  const readJob = requiredDependency(deps, "durableQueue", "read");
  const execute = requiredDependency(deps, "runtime", "execute");
  const readback = requiredDependency(deps, "provider", "readback");
  const sendEvidence = requiredDependency(deps, "telegram", "sendEvidence");

  const result = {
    mode,
    tenant_count: tenantInputs.length,
    origin,
    context_hashes: [],
    job_ids: [],
    steel_session_ids: [],
    telegram_evidence_ids: [],
    released: false,
  };

  for (const tenantInput of tenantInputs) {
    const auth = await readTenantAuth({ ...tenantInput, origin });
    if (!auth || typeof auth !== "object") throw new Error("browser auth tenant record unavailable");
    const session = await createSession({ ...tenantInput, origin, auth });
    const sessionId = boundedId(session && session.id, "Steel session id");
    let released = false;
    try {
      const context = await createContext({ ...tenantInput, origin, auth, sessionId });
      const contextHash = opaqueHash(context);
      const job = await enqueue({ ...tenantInput, origin, contextHash, sessionId });
      const jobId = boundedId(job && job.id, "job id");
      const durableJob = await readJob({ id: jobId });
      if (!durableJob || String(durableJob.id || "") !== jobId) throw new Error("browser auth durable job readback unavailable");
      const runtime = await execute({ ...tenantInput, origin, sessionId, jobId, mode });
      const provider = await readback({ ...tenantInput, origin, sessionId, jobId, runtime });
      if (!provider || typeof provider !== "object") throw new Error("browser auth provider readback unavailable");
      if (mode === "verify-expired-handoff" && provider.handoffRequired !== true) {
        throw new Error("browser auth expired handoff was not provider-confirmed");
      }
      if (mode === "verify-expired-handoff" && deps.authStore && typeof deps.authStore.invalidateTenantAuth === "function") {
        await deps.authStore.invalidateTenantAuth({ ...tenantInput, origin });
      }
      const evidence = await sendEvidence({ ...tenantInput, origin, jobId, sessionId, contextHash, mode });
      result.context_hashes.push(contextHash);
      result.job_ids.push(jobId);
      result.steel_session_ids.push(sessionId);
      result.telegram_evidence_ids.push(boundedId(evidence && evidence.id, "Telegram evidence id"));
    } finally {
      const release = await releaseSession({ sessionId, tenant: tenantInput.tenant, origin });
      released = Boolean(release && release.released);
      if (!released) throw new Error("browser auth Steel release unavailable");
    }
    if (!released) throw new Error("browser auth Steel session was not released");
  }

  if (new Set(result.context_hashes).size !== tenantInputs.length) {
    throw new Error("browser auth tenant contexts are not isolated");
  }
  result.released = true;
  return Object.freeze(result);
}

function makeProductionDeps(env) {
  const { readBrowserAuthSession, invalidateBrowserAuthSession } = require("../lib/browser-auth-session-store.js");
  const { makeSteelCdpClient } = require("../lib/steel-cdp-client.js");
  const { enqueueBrowserJob } = require("../lib/browser-job-store.js");
  const { sendMessage } = require("../lib/telegram.js");
  const { Pool } = require("pg");
  const steel = makeSteelCdpClient();
  const pool = new Pool({ connectionString: env.LM_FEEDBACK_DATABASE_URL, max: 1 });
  let sequence = 0;

  const uidFor = (tenant) => tenant === "tenant-a"
    ? String(env.BROWSER_AUTH_TENANT_A_UID)
    : String(env.BROWSER_AUTH_TENANT_B_UID);
  return {
    authStore: {
      async readTenantAuth({ tenant, origin, principalKind }) {
        const record = await readBrowserAuthSession({ uid: uidFor(tenant), origin, principalKind });
        if (!record) throw new Error("browser auth session is absent or expired");
        return record;
      },
      async invalidateTenantAuth({ tenant, origin, principalKind }) {
        return invalidateBrowserAuthSession({ uid: uidFor(tenant), origin, principalKind });
      },
    },
    steel: {
      async createSession({ auth }) {
        return steel.createSession({ sessionContext: auth.context });
      },
      async createContext({ sessionId }) {
        return steel.getSessionContext(sessionId);
      },
      async releaseSession({ sessionId }) {
        return { released: await steel.releaseSession(sessionId) };
      },
    },
    durableQueue: {
      async enqueue({ tenant, origin, contextHash }) {
        const suffix = `${Date.now()}-${++sequence}`;
        const queued = await enqueueBrowserJob({
          uid: uidFor(tenant),
          chatId: String(env.BROWSER_AUTH_TELEGRAM_CHAT_ID),
          messageId: `browser-auth-e2e-${tenant}-${suffix}`,
          updateId: `browser-auth-e2e-${tenant}-${suffix}`,
          rawPrompt: `Verify the existing authenticated session at ${origin}.`,
          classification: {
            locale: "en",
            goal: `Read the current authenticated provider page at ${origin}; do not submit any action.`,
            actionKind: "browser_auth_continuity_readback",
            requiresLogin: true,
            principalKind: "agent_owned",
          },
        });
        return { id: queued && queued.job && queued.job.id, contextHash };
      },
      async read({ id }) {
        const rows = (await pool.query("SELECT id FROM public.lm_browser_jobs WHERE id = $1 LIMIT 1", [id])).rows;
        return rows[0] || null;
      },
    },
    runtime: {
      async execute({ sessionId, origin }) {
        await steel.navigate(sessionId, origin);
        return { sessionId };
      },
    },
    provider: {
      async readback({ sessionId }) {
        const readback = await steel.readConfirmation(sessionId);
        const body = String(readback && readback.text || "");
        return { handoffRequired: /\b(?:login|log in|sign in)\b/i.test(body) };
      },
    },
    telegram: {
      async sendEvidence({ tenant, jobId, contextHash, mode }) {
        const sent = await sendMessage(
          env.LM_TELEGRAM_BOT_TOKEN,
          env.BROWSER_AUTH_TELEGRAM_CHAT_ID,
          `Browser auth verification: tenant=${tenant}; mode=${mode}; job=${jobId}; context=${contextHash}`,
        );
        return { id: sent && sent.ok === true && sent.result && sent.result.message_id };
      },
    },
  };
}

function cliError(error) {
  return error instanceof ConfigurationError ? error.message : "browser auth production E2E failed";
}

if (require.main === module) {
  const mode = process.argv[2];
  runBrowserAuthProductionE2E({ mode, env: process.env, deps: makeProductionDeps(process.env) })
    .then((result) => process.stdout.write(`${JSON.stringify(result)}\n`))
    .catch((error) => {
      process.stderr.write(`${cliError(error)}\n`);
      process.exitCode = 1;
    });
}

module.exports = { runBrowserAuthProductionE2E, makeProductionDeps, OUTPUT_KEYS };
