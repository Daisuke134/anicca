"use strict";
// AE-ZERO-START-1 §4.1 / §5.3 — the shape of the tenant agent wallet columns.
//
// The invariant this migration carries is "plaintext keys in the database = 0 by schema, not by
// convention". So these assertions are about what the database REFUSES: a key-ref column may hold a
// `secret://` reference and nothing that looks like key material.
//
// Two layers, deliberately. The text assertions pin the exact predicate the migration installs (the
// AND/OR composition of the CHECK). The behavioural assertions then run each pinned regex against real
// attack strings, so a pattern that is present but wrong fails here rather than in production. The
// third layer — the constraints actually rejecting inserts in a live PostgreSQL — is
// `test/postgres/tenant-agent-wallets.integration.sh`, because only a real engine can prove a CHECK.

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SQL = fs.readFileSync(
  path.join(__dirname, "../migrations/2026-07-30-lm-tenant-agent-wallets.sql"),
  "utf8",
);
// The EVM column and its CHECK are owned by an earlier migration and must survive untouched.
const REPORT_SQL = fs.readFileSync(
  path.join(__dirname, "../migrations/2026-07-27-lm-financial-reports.sql"),
  "utf8",
);

// The exact literals the migration must use. Pinned here so the behavioural tests below and the
// installed constraint cannot drift apart.
const SOLANA_ADDRESS_PATTERN = "^[1-9A-HJ-NP-Za-km-z]{32,44}$";
const SECRET_REF_PATTERN = "^secret://[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)+$";
const EVM_KEY_PREFIX_PATTERN = "^0[xX]";
const HEX_KEY_RUN_PATTERN = "[0-9a-fA-F]{64}";
const BASE58_SECRET_RUN_PATTERN = "[1-9A-HJ-NP-Za-km-z]{80,}";

const KEY_REF_COLUMNS = ["agent_wallet_key_ref", "agent_wallet_solana_key_ref"];

// The composition the migration installs, mirrored so an accept/reject table can be executed. Bound to
// the migration by `pins the whole key-ref predicate` below, which asserts this exact text is the SQL.
function keyRefPredicate(column) {
  return [
    `${column} IS NULL`,
    `        OR (`,
    `          ${column} ~ '${SECRET_REF_PATTERN}'`,
    `          AND ${column} !~ '${EVM_KEY_PREFIX_PATTERN}'`,
    `          AND ${column} !~ '${HEX_KEY_RUN_PATTERN}'`,
    `          AND ${column} !~ '${BASE58_SECRET_RUN_PATTERN}'`,
    `          AND char_length(${column}) BETWEEN 12 AND 200`,
    `        )`,
  ].join("\n");
}

function keyRefAccepts(value) {
  if (value === null) return true;
  if (typeof value !== "string") return false;
  return new RegExp(SECRET_REF_PATTERN).test(value)
    && !new RegExp(EVM_KEY_PREFIX_PATTERN).test(value)
    && !new RegExp(HEX_KEY_RUN_PATTERN).test(value)
    && !new RegExp(BASE58_SECRET_RUN_PATTERN).test(value)
    && value.length >= 12
    && value.length <= 200;
}

test("the migration is additive — it adds nullable columns and rewrites nothing", () => {
  for (const column of [
    "agent_wallet_solana_address text",
    "agent_wallet_key_ref text",
    "agent_wallet_solana_key_ref text",
    "agent_wallet_created_at timestamptz",
  ]) {
    assert.ok(
      SQL.includes(`ADD COLUMN IF NOT EXISTS ${column}`),
      `${column} must be added idempotently`,
    );
  }
  assert.doesNotMatch(SQL, /\bDROP TABLE\b/i);
  assert.doesNotMatch(SQL, /\bDROP COLUMN\b/i);
  assert.doesNotMatch(SQL, /\bUPDATE public\./i);
  assert.doesNotMatch(SQL, /\bDELETE FROM\b/i);
  // A NOT NULL column added to a populated table fails the migration outright, so no ADD COLUMN clause
  // may carry one. (`IS NOT NULL` in the partial indexes below is a different thing entirely.)
  assert.doesNotMatch(SQL, /ADD COLUMN[^,;]*\bNOT NULL\b/i, "a new column must stay nullable");
  assert.doesNotMatch(SQL, /ADD COLUMN[^,;]*\bDEFAULT\b/i, "a default would backfill every tenant row");
});

test("the existing EVM address CHECK is left completely alone", () => {
  // REPORT-1 owns agent_wallet_address. Dropping or replacing its constraint here would silently widen
  // what the EVM column accepts, which is how a Solana string ends up in an EVM address field.
  assert.doesNotMatch(SQL, /DROP CONSTRAINT/i);
  assert.doesNotMatch(
    SQL,
    /agent_wallet_address\s*~/i,
    "this migration must not restate the EVM pattern",
  );
  assert.match(REPORT_SQL, /agent_wallet_address ~ '\^0x\[0-9a-fA-F\]\{40\}\$'/);
});

test("the Solana address column accepts exactly the base58 shape the ledger accepts", () => {
  assert.ok(
    SQL.includes(`agent_wallet_solana_address ~ '${SOLANA_ADDRESS_PATTERN}'`),
    "the Solana CHECK must use the ledger's base58 pattern",
  );
  assert.ok(SQL.includes("agent_wallet_solana_address IS NULL"), "the column must stay nullable");

  const { SOLANA_ADDRESS_RE } = require("./agent-wallet-solana.js");
  assert.equal(
    SOLANA_ADDRESS_RE.source,
    SOLANA_ADDRESS_PATTERN,
    "the schema and the generator must agree on the address shape, or one will reject the other",
  );

  const pattern = new RegExp(SOLANA_ADDRESS_PATTERN);
  const { generateSolanaAgentWallet } = require("./agent-wallet-solana.js");
  for (let attempt = 0; attempt < 8; attempt++) {
    assert.equal(pattern.test(generateSolanaAgentWallet().address), true);
  }
  for (const bad of [
    "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
    "0OIl0OIl0OIl0OIl0OIl0OIl0OIl0OIl",
    "short",
    "1".repeat(45),
    "",
  ]) {
    assert.equal(pattern.test(bad), false, `${bad.slice(0, 12)}… must be refused`);
  }
});

test("pins the whole key-ref predicate for both key columns", () => {
  for (const column of KEY_REF_COLUMNS) {
    assert.ok(
      SQL.includes(keyRefPredicate(column)),
      `${column} must carry the exact anti-plaintext-key predicate`,
    );
  }
});

test("a key-ref column accepts a secret reference and nothing else", () => {
  for (const good of [
    null,
    "secret://lm-agent-wallet/tenant-a/base",
    "secret://lm-agent-wallet/tenant-a/solana",
    "secret://lm-agent-wallet/550e8400-e29b-41d4-a716-446655440000/base",
  ]) {
    assert.equal(keyRefAccepts(good), true, `${good} must be accepted`);
  }
});

test("a key-ref column refuses anything key-shaped — this is the §5.3 invariant", () => {
  const hex64 = "ab".repeat(32);
  const base58Secret = "2".repeat(88);
  for (const bad of [
    // Raw key material, with and without the EVM prefix.
    `0x${hex64}`,
    hex64,
    base58Secret,
    // Key material smuggled inside an otherwise well-formed reference.
    `secret://lm-agent-wallet/${hex64}`,
    `secret://lm-agent-wallet/tenant-a/${hex64}`,
    `secret://lm-agent-wallet/${base58Secret}`,
    // Not a reference at all.
    "lm-agent-wallet/tenant-a/base",
    "secret://",
    "secret://lm-agent-wallet",
    "https://vault.example/lm-agent-wallet/tenant-a/base",
    "file:///Users/anicca/.anicca/wallets/tenant-a/base.json",
    "",
    "   ",
    // Bounded: a reference nobody legitimately writes.
    `secret://lm-agent-wallet/${"a".repeat(240)}/base`,
  ]) {
    assert.equal(keyRefAccepts(bad), false, `${String(bad).slice(0, 24)}… must be refused`);
  }
});

test("one tenant's address or key reference can never be another tenant's", () => {
  // Cross-tenant contamination is the headline risk in this slice, so uniqueness is enforced by the
  // database rather than by whichever code path happens to write the row.
  assert.match(
    SQL,
    /CREATE UNIQUE INDEX IF NOT EXISTS lm_users_agent_wallet_solana_address_key[\s\S]*?WHERE agent_wallet_solana_address IS NOT NULL/,
  );
  for (const column of KEY_REF_COLUMNS) {
    assert.match(
      SQL,
      new RegExp(`CREATE UNIQUE INDEX IF NOT EXISTS lm_users_${column}_key[\\s\\S]*?WHERE ${column} IS NOT NULL`),
      `${column} must be unique per tenant`,
    );
  }
});

test("the migration itself holds nothing secret", () => {
  // The words may appear as part of `secret://`, but never as a column or a value.
  assert.doesNotMatch(SQL, /\b(private_key|privatekey|mnemonic|secret_key|secretkey)\b/i);
  assert.doesNotMatch(SQL, /\bseed\b/i);
  assert.doesNotMatch(SQL, /0x[0-9a-fA-F]{64}/);
});
