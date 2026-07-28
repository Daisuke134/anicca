"use strict";

const { createCipheriv, createDecipheriv, createHash, randomBytes } = require("node:crypto");
const canonicalize = require("canonicalize");

const MAX_CONTEXT_BYTES = 1024 * 1024;
const AUTH_CONTEXT_KEYS = new Set(["cookies", "localStorage", "sessionStorage", "indexedDB"]);
const PRINCIPAL_KINDS = new Set(["agent_owned", "user_provided"]);
let defaultPool;

function invalid() {
  throw new Error("browser auth context invalid");
}

function nonEmptyString(value, max = 1000) {
  const text = typeof value === "string" ? value.trim() : "";
  if (!text || text.length > max) invalid();
  return text;
}

function normalizeAuthOrigin(value) {
  if (typeof value !== "string") throw new Error("browser auth origin invalid");
  let parsed;
  try { parsed = new URL(value); } catch { throw new Error("browser auth origin invalid"); }
  if (parsed.protocol !== "https:" || parsed.username || parsed.password || parsed.origin === "null") {
    throw new Error("browser auth origin invalid");
  }
  return parsed.origin;
}

function validateJson(value, depth = 0) {
  if (depth > 64 || value === undefined || typeof value === "function" || typeof value === "symbol" || typeof value === "bigint") invalid();
  if (value === null || typeof value === "string" || typeof value === "boolean") return;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) invalid();
    return;
  }
  if (Array.isArray(value)) {
    for (const item of value) validateJson(item, depth + 1);
    return;
  }
  if (typeof value !== "object" || (Object.getPrototypeOf(value) !== Object.prototype && Object.getPrototypeOf(value) !== null)) invalid();
  for (const [key, item] of Object.entries(value)) {
    if (!key || key.length > 1000) invalid();
    validateJson(item, depth + 1);
  }
}

function canonicalContext(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)
    || Object.getPrototypeOf(value) !== Object.prototype && Object.getPrototypeOf(value) !== null) invalid();
  const keys = Object.keys(value);
  if (keys.some((key) => !AUTH_CONTEXT_KEYS.has(key))) invalid();
  validateJson(value);
  const canonical = canonicalize(value);
  if (typeof canonical !== "string" || Buffer.byteLength(canonical, "utf8") > MAX_CONTEXT_BYTES) invalid();
  return canonical;
}

function validateSessionContext(value) {
  const canonical = canonicalContext(value);
  return JSON.parse(canonical);
}

function principalKind(value) {
  if (!PRINCIPAL_KINDS.has(value)) invalid();
  return value;
}

function authIdentity(input) {
  const uid = nonEmptyString(input && input.uid, 200);
  const origin = normalizeAuthOrigin(input && input.origin);
  const kind = principalKind(input && (input.principalKind === undefined ? input.principal_kind : input.principalKind));
  return { uid, origin, principalKind: kind };
}

function encryptionKey(keyHex) {
  if (typeof keyHex !== "string" || !/^[a-fA-F0-9]{64}$/.test(keyHex)) invalid();
  const key = Buffer.from(keyHex, "hex");
  if (key.length !== 32) invalid();
  return key;
}

function aad({ uid, origin, principalKind }) {
  return Buffer.from(`${uid}\n${origin}\n${principalKind}\n1`, "utf8");
}

function sealBrowserContext(input, keyHex) {
  const identity = authIdentity(input);
  const plaintext = canonicalContext(input && input.context);
  const key = encryptionKey(keyHex);
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", key, iv);
  cipher.setAAD(aad(identity));
  const ciphertext = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
  return {
    ciphertext: ciphertext.toString("base64url"),
    iv: iv.toString("base64url"),
    auth_tag: cipher.getAuthTag().toString("base64url"),
    context_sha256: createHash("sha256").update(plaintext, "utf8").digest("hex"),
    key_version: 1,
  };
}

function fromBase64url(value) {
  if (typeof value !== "string" || !/^[A-Za-z0-9_-]+$/.test(value)) invalid();
  return Buffer.from(value, "base64url");
}

function openBrowserContext(row, keyHex) {
  try {
    const identity = authIdentity(row);
    if (!row || row.key_version !== 1 || !/^[a-f0-9]{64}$/.test(String(row.context_sha256 || ""))) invalid();
    const key = encryptionKey(keyHex);
    const iv = fromBase64url(row.iv);
    const tag = fromBase64url(row.auth_tag);
    if (iv.length !== 12 || tag.length !== 16) invalid();
    const decipher = createDecipheriv("aes-256-gcm", key, iv);
    decipher.setAAD(aad(identity));
    decipher.setAuthTag(tag);
    const plaintext = Buffer.concat([decipher.update(fromBase64url(row.ciphertext)), decipher.final()]).toString("utf8");
    if (createHash("sha256").update(plaintext, "utf8").digest("hex") !== row.context_sha256) invalid();
    const context = JSON.parse(plaintext);
    if (canonicalContext(context) !== plaintext) invalid();
    return context;
  } catch {
    invalid();
  }
}

function database(opts = {}) {
  if (typeof opts.query === "function") return { query: opts.query };
  const connectionString = String(opts.connectionString || process.env.LM_FEEDBACK_DATABASE_URL || "").trim();
  if (!connectionString) throw new Error("browser auth session store unavailable");
  if (!defaultPool) {
    const Pool = opts.Pool || require("pg").Pool;
    defaultPool = new Pool({ connectionString, max: 4 });
  }
  return { query: defaultPool.query.bind(defaultPool) };
}

function sessionKey(input, opts) {
  return input && input.keyHex || opts && opts.keyHex || process.env.LM_BROWSER_AUTH_CONTEXT_KEY_HEX;
}

function optionalTimestamp(value) {
  if (value == null) return null;
  if (typeof value !== "string" || value.length > 100) invalid();
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) invalid();
  return timestamp.toISOString();
}

function authRecord(row, identity, context) {
  if (!row || typeof row !== "object" || row.uid !== identity.uid
    || row.origin !== identity.origin || row.principal_kind !== identity.principalKind) {
    throw new Error("browser auth session row invalid");
  }
  return Object.freeze({
    uid: identity.uid,
    origin: identity.origin,
    principal_kind: identity.principalKind,
    state: row.state,
    expires_at: row.expires_at || null,
    last_verified_at: row.last_verified_at || null,
    created_at: row.created_at || null,
    updated_at: row.updated_at || null,
    context,
  });
}

async function readBrowserAuthSession(input, opts = {}) {
  const identity = authIdentity(input);
  const { query } = database(opts);
  const rows = (await query(`
    SELECT * FROM public.lm_browser_auth_sessions
    WHERE uid = $1 AND origin = $2 AND principal_kind = $3
      AND state = 'active'
      AND (expires_at IS NULL OR expires_at > clock_timestamp())
    LIMIT 1
  `, [identity.uid, identity.origin, identity.principalKind])).rows;
  if (rows.length === 0) return null;
  if (rows.length !== 1) throw new Error("browser auth session read returned multiple rows");
  return authRecord(rows[0], identity, openBrowserContext(rows[0], sessionKey(input, opts)));
}

async function upsertBrowserAuthSession(input, opts = {}) {
  const identity = authIdentity(input);
  const context = validateSessionContext(input && input.context);
  const sealed = sealBrowserContext({ ...identity, context }, sessionKey(input, opts));
  const expiresAt = optionalTimestamp(input && input.expiresAt);
  const lastVerifiedAt = optionalTimestamp(input && input.lastVerifiedAt);
  const { query } = database(opts);
  const rows = (await query(`
    INSERT INTO public.lm_browser_auth_sessions (
      uid, origin, principal_kind, ciphertext, iv, auth_tag, context_sha256,
      key_version, state, expires_at, last_verified_at
    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'active',$9,$10)
    ON CONFLICT (uid, origin, principal_kind) DO UPDATE
    SET ciphertext = EXCLUDED.ciphertext,
        iv = EXCLUDED.iv,
        auth_tag = EXCLUDED.auth_tag,
        context_sha256 = EXCLUDED.context_sha256,
        key_version = EXCLUDED.key_version,
        state = 'active',
        expires_at = EXCLUDED.expires_at,
        last_verified_at = EXCLUDED.last_verified_at,
        updated_at = clock_timestamp()
    RETURNING *
  `, [
    identity.uid,
    identity.origin,
    identity.principalKind,
    sealed.ciphertext,
    sealed.iv,
    sealed.auth_tag,
    sealed.context_sha256,
    sealed.key_version,
    expiresAt,
    lastVerifiedAt,
  ])).rows;
  if (rows.length !== 1) throw new Error("browser auth session upsert lost row");
  return authRecord(rows[0], identity, context);
}

async function invalidateBrowserAuthSession(input, opts = {}) {
  const identity = authIdentity(input);
  const { query } = database(opts);
  const rows = (await query(`
    UPDATE public.lm_browser_auth_sessions
    SET state = 'invalidated', updated_at = clock_timestamp()
    WHERE uid = $1 AND origin = $2 AND principal_kind = $3 AND state = 'active'
    RETURNING uid
  `, [identity.uid, identity.origin, identity.principalKind])).rows;
  if (rows.length > 1) throw new Error("browser auth session invalidation returned multiple rows");
  return rows.length === 1;
}

module.exports = {
  normalizeAuthOrigin,
  validateSessionContext,
  sealBrowserContext,
  openBrowserContext,
  readBrowserAuthSession,
  upsertBrowserAuthSession,
  invalidateBrowserAuthSession,
};
