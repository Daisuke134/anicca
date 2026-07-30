"use strict";
// AE-ZERO-START-1 §4.3 — per-tenant key custody, local rail only.
//
// This is the ONLY place in the slice where private key material reaches a disk, and the only place that
// reads it back. Everything else in the feature handles public addresses and `secret://` references, so
// the blast radius of a mistake is confined to this file.
//
// Four rules, each answering a specific way this goes wrong.
//
// 1. A key file is 0600 in a 0700 directory, and the mode is re-checked on every read — the same check
//    `scripts/run-agent-payout.js:38-62` performs, for the same reason: a key another process can read is
//    not a key. The check is on `lstat` first, so a symlink cannot borrow its target's mode.
//
// 2. Creation is atomic AND non-clobbering. The payload is written to a temp file, fsynced, and then
//    hard-LINKED into place: `link(2)` fails with EEXIST if the name already exists, whereas `rename(2)`
//    would silently overwrite. §4.3 asks for tmp+rename atomicity and §5.4 asks that a pre-existing key
//    is never overwritten; rename cannot deliver the second, and link delivers both. A crash mid-write
//    leaves only a temp file, never a half-written key under the real name.
//
// 3. The file and the database must agree about which wallet a tenant owns. If they disagree — or if the
//    database names an address whose key file is gone — this hard-stops with a coded error and touches
//    nothing. Minting a replacement would abandon whatever has already been sent to the recorded
//    address, which is exactly the silent money loss this slice exists to avoid.
//
// 4. No secret leaves this module except through the deliberate `readTenantWallet` /
//    `createTenantWalletKeychain` doors. `ensureTenantWallets` returns public identity only, and no
//    thrown error interpolates file contents.

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { randomUUID } = require("node:crypto");

const { deriveAddress, generateAgentWallet } = require("./agent-wallet.js");
const { deriveSolanaAddress, generateSolanaAgentWallet } = require("./agent-wallet-solana.js");

// Same tenant grammar the secret provider enforces (`lib/secret-provider.js:5`). It excludes `/` and
// cannot match `..`, so a uid can never escape its own directory.
const TENANT_ID = /^[a-z0-9][a-z0-9._-]{0,127}$/i;
const MAX_WALLET_BYTES = 4096;
const KEY_NAMESPACE = "lm-agent-wallet";

const RAILS = Object.freeze({
  base: Object.freeze({
    file: "base.json",
    chain: "base",
    secretField: "privateKey",
    column: "agent_wallet_address",
    keyRefColumn: "agent_wallet_key_ref",
    derive: deriveAddress,
    generate: generateAgentWallet,
    readSecret: (wallet) => wallet.privateKey,
  }),
  solana: Object.freeze({
    file: "solana.json",
    chain: "solana",
    secretField: "secretKey",
    column: "agent_wallet_solana_address",
    keyRefColumn: "agent_wallet_solana_key_ref",
    derive: deriveSolanaAddress,
    generate: generateSolanaAgentWallet,
    readSecret: (wallet) => wallet.secretKey,
  }),
});

function coded(message, code, rail) {
  const error = new Error(message);
  error.code = code;
  if (rail) error.rail = rail;
  return error;
}

function requiredTenantId(uid) {
  const value = typeof uid === "string" ? uid.trim() : "";
  if (!value || !TENANT_ID.test(value) || value !== uid) {
    throw coded("a valid tenant identity is required for wallet custody", "WALLET_TENANT_INVALID");
  }
  return value;
}

function requiredRail(rail) {
  const key = String(rail == null ? "" : rail).trim();
  if (!Object.prototype.hasOwnProperty.call(RAILS, key)) {
    throw coded("wallet rail must be base or solana", "WALLET_RAIL_INVALID");
  }
  return key;
}

function walletRootDir(env = process.env) {
  const configured = String((env && env.LM_DATA_ROOT) || "").trim();
  const root = configured || path.join(os.homedir(), ".anicca");
  if (!path.isAbsolute(root)) {
    throw coded("LM_DATA_ROOT must be an absolute path", "WALLET_ROOT_INVALID");
  }
  return path.join(path.resolve(root), "wallets");
}

function tenantWalletPaths(uid, env = process.env) {
  const tenantId = requiredTenantId(uid);
  const dir = path.join(walletRootDir(env), tenantId);
  return Object.freeze({
    dir,
    base: path.join(dir, RAILS.base.file),
    solana: path.join(dir, RAILS.solana.file),
  });
}

function tenantWalletKeyRef(uid, rail) {
  return `secret://${KEY_NAMESPACE}/${requiredTenantId(uid)}/${requiredRail(rail)}`;
}

function parseTenantWalletKeyRef(ref) {
  const match = new RegExp(`^secret://${KEY_NAMESPACE}/([^/]+)/([^/]+)$`).exec(String(ref || ""));
  if (!match) return null;
  try {
    return { uid: requiredTenantId(match[1]), rail: requiredRail(match[2]) };
  } catch {
    return null;
  }
}

// The mode/shape gate. Deliberately duplicated in spirit from scripts/run-agent-payout.js rather than
// shared with it: that reader owns one operator-managed file, this one owns a per-tenant tree, and a
// single "flexible" reader is how a tenant scope check gets lost.
function readTenantWallet(uid, rail, opts = {}) {
  const tenantId = requiredTenantId(uid);
  const railKey = requiredRail(rail);
  const spec = RAILS[railKey];
  const filePath = tenantWalletPaths(tenantId, opts.env || process.env)[railKey];

  const linkStat = fs.lstatSync(filePath);
  if (linkStat.isSymbolicLink() || !linkStat.isFile()) {
    throw coded("a tenant key file must be a regular file, never a symlink", "WALLET_KEY_NOT_REGULAR_FILE", railKey);
  }
  const fileStat = fs.statSync(filePath);
  if ((fileStat.mode & 0o777) !== 0o600) {
    throw coded("a tenant key file must have mode 0600", "WALLET_KEY_MODE_INVALID", railKey);
  }
  if (fileStat.size <= 0 || fileStat.size > MAX_WALLET_BYTES) {
    throw coded("a tenant key file has an invalid bounded size", "WALLET_KEY_SIZE_INVALID", railKey);
  }

  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    // The caught message is not interpolated: a JSON parse error quotes the input, and the input is a key.
    throw coded("a tenant key file is not valid JSON", "WALLET_KEY_MALFORMED", railKey);
  }

  const address = String((parsed && parsed.address) || "");
  const secret = String((parsed && parsed[spec.secretField]) || "");
  if (!address || !secret) {
    throw coded("a tenant key file is missing its address or its key", "WALLET_KEY_INCOMPLETE", railKey);
  }
  let derived;
  try {
    derived = spec.derive(secret);
  } catch {
    throw coded("a tenant key file does not hold a usable key", "WALLET_KEY_UNUSABLE", railKey);
  }
  if (derived !== address) {
    throw coded("a tenant key file does not derive its own stored address", "WALLET_KEY_DERIVE_MISMATCH", railKey);
  }
  // §12.3 NEW-9 — fail closed on an ABSENT uid. `parsed.uid || tenantId` defaulted a missing field to the
  // requester's own id, i.e. it fell back to trusting precisely the value it exists to verify. §9.4 calls
  // this line the guard against a cross-tenant leak on a case-insensitive filesystem, so a key file that
  // does not say who it belongs to is unusable, not assumed to belong to whoever asked.
  if (typeof parsed.uid !== "string" || parsed.uid !== tenantId) {
    throw coded("a tenant key file belongs to a different tenant", "WALLET_KEY_TENANT_MISMATCH", railKey);
  }
  return { address, secret, chain: spec.chain, created_at: parsed.created_at || null };
}

function keyFileExists(filePath) {
  try {
    fs.lstatSync(filePath);
    return true;
  } catch (error) {
    if (error && error.code === "ENOENT") return false;
    throw error;
  }
}

// Atomic and non-clobbering: see rule 2 in the header.
function writeKeyFileExclusive(filePath, payload) {
  const dir = path.dirname(filePath);
  const temporary = path.join(dir, `.${path.basename(filePath)}.${process.pid}.${randomUUID()}.tmp`);
  const handle = fs.openSync(temporary, fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL, 0o600);
  try {
    fs.writeFileSync(handle, `${JSON.stringify(payload, null, 2)}\n`);
    fs.fsyncSync(handle);
  } finally {
    fs.closeSync(handle);
  }
  try {
    // umask can widen the open() mode, so the mode is asserted rather than assumed.
    fs.chmodSync(temporary, 0o600);
    fs.linkSync(temporary, filePath);
  } finally {
    fs.unlinkSync(temporary);
  }
}

function provisionRail({ tenantId, railKey, env, existing, generate, nowIso }) {
  const spec = RAILS[railKey];
  const filePath = tenantWalletPaths(tenantId, env)[railKey];
  const recorded = String((existing && existing[spec.column]) || "").trim();
  const present = keyFileExists(filePath);

  if (present) {
    const stored = readTenantWallet(tenantId, railKey, { env });
    if (recorded && recorded !== stored.address) {
      // §5.4: never overwrite. One of the two is the address someone may already have funded.
      throw coded(
        `the ${spec.chain} key file and the recorded address disagree — refusing to overwrite a tenant key`,
        "WALLET_KEY_ADDRESS_MISMATCH",
        railKey,
      );
    }
    return {
      status: "existing",
      address: stored.address,
      key_ref: tenantWalletKeyRef(tenantId, railKey),
      created_at: stored.created_at || null,
    };
  }

  if (recorded) {
    // The database says this tenant owns an address whose key is gone. Minting a new one would silently
    // abandon anything already at the recorded address, so this stops and says so.
    throw coded(
      `the recorded ${spec.chain} address has no key file — refusing to mint a replacement wallet`,
      "WALLET_KEY_FILE_MISSING",
      railKey,
    );
  }

  const wallet = generate();
  const secret = spec.readSecret(wallet);
  writeKeyFileExclusive(filePath, {
    schema_version: 1,
    chain: spec.chain,
    uid: tenantId,
    address: wallet.address,
    [spec.secretField]: secret,
    created_at: nowIso,
  });
  return {
    status: "created",
    address: wallet.address,
    key_ref: tenantWalletKeyRef(tenantId, railKey),
    created_at: nowIso,
  };
}

// Returns the public identity and the exact `lm_users` columns to write. The caller does the database
// I/O, so no transport credential and no SQL lives next to the key material.
function ensureTenantWallets(uid, opts = {}) {
  const tenantId = requiredTenantId(uid);
  const env = opts.env || process.env;
  const nowIso = typeof opts.now === "function" ? String(opts.now()) : new Date().toISOString();
  const existing = opts.existing && typeof opts.existing === "object" ? opts.existing : null;

  const dir = tenantWalletPaths(tenantId, env).dir;
  fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  // recursive mkdir applies the mode only to directories it creates, and umask can widen it.
  fs.chmodSync(dir, 0o700);

  const base = provisionRail({
    tenantId,
    railKey: "base",
    env,
    existing,
    generate: typeof opts.generateBase === "function" ? opts.generateBase : RAILS.base.generate,
    nowIso,
  });
  const solana = provisionRail({
    tenantId,
    railKey: "solana",
    env,
    existing,
    generate: typeof opts.generateSolana === "function" ? opts.generateSolana : RAILS.solana.generate,
    nowIso,
  });

  const createdAt = String((existing && existing.agent_wallet_created_at) || "").trim()
    || base.created_at
    || solana.created_at
    || nowIso;

  return Object.freeze({
    uid: tenantId,
    status: base.status === "created" || solana.status === "created" ? "created" : "existing",
    base: Object.freeze({ status: base.status, address: base.address, key_ref: base.key_ref }),
    solana: Object.freeze({ status: solana.status, address: solana.address, key_ref: solana.key_ref }),
    columns: Object.freeze({
      agent_wallet_address: base.address,
      agent_wallet_solana_address: solana.address,
      agent_wallet_key_ref: base.key_ref,
      agent_wallet_solana_key_ref: solana.key_ref,
      agent_wallet_created_at: createdAt,
    }),
    paths: Object.freeze({
      base: tenantWalletPaths(tenantId, env).base,
      solana: tenantWalletPaths(tenantId, env).solana,
    }),
  });
}

// The `lib/secret-provider.js` local seam for wallet keys.
//
// §10 MINOR-11 — honest status: NOTHING in the running path calls this today. The zero-start adapter reads
// key files through `ensureTenantWallets`, and no shipped code needs a tenant's signing key yet. It is kept
// deliberately, as a stated exception to the delete-unused-code rule, because AE-X402-TENANT-ROUTING-1 and
// AE-CLOUD-CUSTODY-1 both need exactly this seam; it is covered by tests so it cannot rot in the meantime.
// Do not read the check below as protecting a live path — it is the contract a future caller must meet.
function createTenantWalletKeychain(options = {}) {
  const env = options.env || process.env;
  return {
    async get(requestTenantId, ref) {
      const parsed = parseTenantWalletKeyRef(ref);
      if (!parsed) throw coded("not a tenant wallet key reference", "WALLET_KEY_REF_INVALID");
      if (parsed.uid !== requestTenantId) {
        throw coded("tenant wallet key scope mismatch", "WALLET_KEY_SCOPE_MISMATCH");
      }
      return readTenantWallet(parsed.uid, parsed.rail, { env }).secret;
    },
    async health() {
      const root = walletRootDir(env);
      try {
        fs.mkdirSync(root, { recursive: true, mode: 0o700 });
        fs.accessSync(root, fs.constants.R_OK | fs.constants.W_OK);
        return { ok: true };
      } catch {
        return { ok: false };
      }
    },
  };
}

module.exports = {
  KEY_NAMESPACE,
  MAX_WALLET_BYTES,
  RAILS,
  createTenantWalletKeychain,
  ensureTenantWallets,
  parseTenantWalletKeyRef,
  readTenantWallet,
  tenantWalletKeyRef,
  tenantWalletPaths,
  walletRootDir,
};
