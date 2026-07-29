"use strict";

const { createHash, randomBytes, randomUUID } = require("node:crypto");
const { spawnSync } = require("node:child_process");

const {
  openBrowserContext,
  readBrowserAuthSession,
  upsertBrowserAuthSession,
} = require("../lib/browser-auth-session-store.js");

const E2E_ORIGIN = "https://example.com";
const PRINCIPAL_KIND = "agent_owned";
const COOKIE_NAME = "browser_auth_e2e";
const UID_PREFIX = "browser-auth-e2e-";
const HASH_PATTERN = /^[a-f0-9]{64}$/;

class TenantIsolationError extends Error {}

function markerHash(value) {
  return createHash("sha256").update(String(value || ""), "utf8").digest("hex");
}

function controlledIdentities() {
  return [
    { uid: `${UID_PREFIX}${randomUUID()}`, marker: randomBytes(32).toString("hex") },
    { uid: `${UID_PREFIX}${randomUUID()}`, marker: randomBytes(32).toString("hex") },
  ];
}

function validIdentities(value) {
  return Array.isArray(value)
    && value.length === 2
    && value.every(({ uid, marker }) => (
      typeof uid === "string"
      && uid.startsWith(UID_PREFIX)
      && uid.length <= 200
      && HASH_PATTERN.test(String(marker || ""))
    ))
    && new Set(value.map(({ uid }) => uid)).size === 2
    && new Set(value.map(({ marker }) => marker)).size === 2;
}

function requireDeps(deps) {
  const methods = [
    "identities",
    "hashMarker",
    "removeStale",
    "upsert",
    "readFresh",
    "crossReadFails",
    "ciphertextPlaintextHits",
    "cleanup",
    "count",
    "close",
  ];
  if (!deps || methods.some((method) => typeof deps[method] !== "function")) {
    throw new TenantIsolationError("browser auth tenant isolation unavailable");
  }
}

async function runBrowserAuthTenantIsolationE2E({ deps } = {}) {
  requireDeps(deps);
  let identities = [];
  let cleaned = false;
  try {
    await deps.removeStale();
    identities = deps.identities();
    if (!validIdentities(identities)) {
      throw new TenantIsolationError("browser auth tenant isolation unavailable");
    }

    const saved = [];
    for (const identity of identities) {
      const result = await deps.upsert(identity);
      const contextHash = String(result && result.contextHash || "");
      if (!HASH_PATTERN.test(contextHash)) {
        throw new TenantIsolationError("browser auth tenant isolation unavailable");
      }
      saved.push({ ...identity, contextHash });
    }

    const freshReads = [];
    for (const identity of saved) {
      const read = await deps.readFresh({ uid: identity.uid });
      if (
        !read
        || read.contextHash !== identity.contextHash
        || read.markerHash !== deps.hashMarker(identity.marker)
        || !HASH_PATTERN.test(String(read.contextHash || ""))
        || !HASH_PATTERN.test(String(read.markerHash || ""))
      ) {
        throw new TenantIsolationError("browser auth tenant isolation unavailable");
      }
      freshReads.push(read);
    }

    const crossReadResults = await Promise.all([
      deps.crossReadFails({ sourceUid: saved[0].uid, targetUid: saved[1].uid }),
      deps.crossReadFails({ sourceUid: saved[1].uid, targetUid: saved[0].uid }),
    ]);
    if (crossReadResults.some((result) => result !== true)) {
      throw new TenantIsolationError("browser auth tenant isolation unavailable");
    }

    const plaintextHits = await deps.ciphertextPlaintextHits({
      uids: saved.map(({ uid }) => uid),
      markers: saved.map(({ marker }) => marker),
    });
    if (plaintextHits !== 0 || new Set(saved.map(({ contextHash }) => contextHash)).size !== 2) {
      throw new TenantIsolationError("browser auth tenant isolation unavailable");
    }

    const cleanupCount = await deps.cleanup({ uids: saved.map(({ uid }) => uid) });
    const postCleanupRows = await deps.count({ uids: saved.map(({ uid }) => uid) });
    if (cleanupCount !== 2 || postCleanupRows !== 0) {
      throw new TenantIsolationError("browser auth tenant isolation unavailable");
    }
    cleaned = true;

    return Object.freeze({
      tenant_count: 2,
      origin: E2E_ORIGIN,
      context_hashes: saved.map(({ contextHash }) => contextHash),
      fresh_process_reads: freshReads.length,
      distinct_contexts: true,
      cross_read_zero: true,
      ciphertext_plaintext_hits: plaintextHits,
      cleanup_count: cleanupCount,
      post_cleanup_rows: postCleanupRows,
    });
  } catch {
    throw new TenantIsolationError("browser auth tenant isolation unavailable");
  } finally {
    if (!cleaned && identities.length === 2) {
      try { await deps.cleanup({ uids: identities.map(({ uid }) => uid) }); } catch {}
    }
    try { await deps.close(); } catch {}
  }
}

function makeProductionDeps(env = process.env, boundaries = {}) {
  const keyHex = String(env.LM_BROWSER_SESSION_KEY || "").trim();
  const connectionString = String(env.LM_FEEDBACK_DATABASE_URL || "").trim();
  if (!HASH_PATTERN.test(keyHex) || !connectionString) {
    throw new TenantIsolationError("browser auth tenant isolation unavailable");
  }

  let ownedPool;
  let query = boundaries.query;
  if (typeof query !== "function") {
    const { Pool } = require("pg");
    ownedPool = new Pool({ connectionString, max: 2 });
    query = ownedPool.query.bind(ownedPool);
  }
  const child = boundaries.spawnSync || spawnSync;
  const storeOptions = { query, keyHex };

  return {
    identities: controlledIdentities,
    hashMarker: markerHash,
    async removeStale() {
      const result = await query(`
        DELETE FROM public.lm_browser_auth_sessions
        WHERE origin = $1
          AND principal_kind = $2
          AND uid LIKE $3
          AND updated_at < clock_timestamp() - interval '15 minutes'
      `, [E2E_ORIGIN, PRINCIPAL_KIND, `${UID_PREFIX}%`]);
      return Number(result && result.rowCount || 0);
    },
    async upsert({ uid, marker }) {
      const saved = await upsertBrowserAuthSession({
        uid,
        origin: E2E_ORIGIN,
        principalKind: PRINCIPAL_KIND,
        context: {
          cookies: [{
            name: COOKIE_NAME,
            value: marker,
            domain: "example.com",
            path: "/",
            hostOnly: true,
            secure: true,
          }],
        },
        expiresAt: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
        lastVerifiedAt: new Date().toISOString(),
      }, storeOptions);
      return { contextHash: saved.context_sha256 };
    },
    async readFresh({ uid }) {
      const result = child(process.execPath, [__filename, "read-child"], {
        encoding: "utf8",
        maxBuffer: 64 * 1024,
        timeout: 30_000,
        env: {
          ...env,
          BROWSER_AUTH_E2E_UID: uid,
        },
      });
      if (!result || result.status !== 0 || result.signal || result.stderr) {
        throw new TenantIsolationError("browser auth tenant isolation unavailable");
      }
      let parsed;
      try { parsed = JSON.parse(String(result.stdout || "")); } catch {
        throw new TenantIsolationError("browser auth tenant isolation unavailable");
      }
      return parsed;
    },
    async crossReadFails({ sourceUid, targetUid }) {
      const rows = (await query(`
        SELECT *
        FROM public.lm_browser_auth_sessions
        WHERE uid = $1 AND origin = $2 AND principal_kind = $3
        LIMIT 1
      `, [sourceUid, E2E_ORIGIN, PRINCIPAL_KIND])).rows;
      if (!Array.isArray(rows) || rows.length !== 1) return false;
      try {
        openBrowserContext({ ...rows[0], uid: targetUid }, keyHex);
        return false;
      } catch {
        return true;
      }
    },
    async ciphertextPlaintextHits({ uids, markers }) {
      const rows = (await query(`
        SELECT ciphertext, iv, auth_tag
        FROM public.lm_browser_auth_sessions
        WHERE uid = ANY($1::text[]) AND origin = $2 AND principal_kind = $3
      `, [uids, E2E_ORIGIN, PRINCIPAL_KIND])).rows;
      const sealed = JSON.stringify(rows || []);
      return markers.filter((marker) => sealed.includes(marker)).length;
    },
    async cleanup({ uids }) {
      const result = await query(`
        DELETE FROM public.lm_browser_auth_sessions
        WHERE uid = ANY($1::text[]) AND origin = $2 AND principal_kind = $3
      `, [uids, E2E_ORIGIN, PRINCIPAL_KIND]);
      return Number(result && result.rowCount || 0);
    },
    async count({ uids }) {
      const rows = (await query(`
        SELECT count(*)::int AS count
        FROM public.lm_browser_auth_sessions
        WHERE uid = ANY($1::text[]) AND origin = $2 AND principal_kind = $3
      `, [uids, E2E_ORIGIN, PRINCIPAL_KIND])).rows;
      return Number(rows && rows[0] && rows[0].count);
    },
    async close() {
      if (ownedPool) await ownedPool.end();
    },
  };
}

async function readChild(env = process.env) {
  const uid = String(env.BROWSER_AUTH_E2E_UID || "");
  const keyHex = String(env.LM_BROWSER_SESSION_KEY || "").trim();
  const connectionString = String(env.LM_FEEDBACK_DATABASE_URL || "").trim();
  if (!uid.startsWith(UID_PREFIX) || uid.length > 200 || !HASH_PATTERN.test(keyHex) || !connectionString) {
    throw new TenantIsolationError("browser auth tenant isolation unavailable");
  }
  const { Pool } = require("pg");
  const pool = new Pool({ connectionString, max: 1 });
  try {
    const session = await readBrowserAuthSession({
      uid,
      origin: E2E_ORIGIN,
      principalKind: PRINCIPAL_KIND,
      keyHex,
    }, { query: pool.query.bind(pool), keyHex });
    const cookies = session && session.context && session.context.cookies;
    const markerCookie = Array.isArray(cookies)
      ? cookies.find((cookie) => cookie && cookie.name === COOKIE_NAME)
      : null;
    if (!session || !markerCookie || !HASH_PATTERN.test(String(markerCookie.value || ""))) {
      throw new TenantIsolationError("browser auth tenant isolation unavailable");
    }
    return {
      contextHash: session.context_sha256,
      markerHash: markerHash(markerCookie.value),
    };
  } finally {
    await pool.end();
  }
}

async function main() {
  try {
    if (process.argv[2] === "read-child") {
      process.stdout.write(`${JSON.stringify(await readChild())}\n`);
      return;
    }
    const result = await runBrowserAuthTenantIsolationE2E({
      deps: makeProductionDeps(process.env),
    });
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } catch {
    process.stderr.write("browser auth tenant isolation unavailable\n");
    process.exitCode = 1;
  }
}

if (require.main === module) main();

module.exports = {
  makeProductionDeps,
  runBrowserAuthTenantIsolationE2E,
};
