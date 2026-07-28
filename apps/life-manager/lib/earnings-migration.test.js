"use strict";
// FIN-c — the shape of the earnings table itself.
//
// A ledger is only evidence if the database refuses to let it change after the fact. These assertions
// are about that refusal: append-only enforced in the engine rather than by convention, amounts stored
// as whole minor units, and no column that could hold a key.

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SQL = fs.readFileSync(
  path.join(__dirname, "../migrations/2026-07-25-lm-agent-earnings.sql"),
  "utf8",
);
const ATOMIC_SQL = fs.readFileSync(
  path.join(__dirname, "../migrations/2026-07-28-lm-agent-earnings-atomic.sql"),
  "utf8",
);
const SOLANA_SQL = fs.readFileSync(
  path.join(__dirname, "../migrations/2026-07-28-lm-agent-earnings-solana.sql"),
  "utf8",
);

test("the table is created additively and never replaces anything", () => {
  assert.match(SQL, /CREATE TABLE IF NOT EXISTS public\.lm_agent_earnings/i);
  assert.doesNotMatch(SQL, /\bDROP TABLE\b/i);
  assert.doesNotMatch(SQL, /\bALTER TABLE public\.lm_(users|score_outcomes)\b/i);
});

test("the database enforces append-only, so a row cannot be edited after it is written", () => {
  assert.match(SQL, /BEFORE UPDATE OR DELETE ON public\.lm_agent_earnings/i);
  assert.match(SQL, /lm_agent_earnings is append-only/i);
  assert.match(SQL, /REVOKE UPDATE, DELETE ON TABLE public\.lm_agent_earnings FROM service_role/i);
});

test("an entry key is unique, so a retried earn-loop write cannot double-count revenue", () => {
  assert.match(SQL, /entry_key text NOT NULL/i);
  assert.match(SQL, /UNIQUE\s*\(\s*wallet_address\s*,\s*entry_key\s*\)/i);
});

test("amounts are whole non-negative minor units — direction lives in the kind", () => {
  assert.match(SQL, /amount_minor numeric NOT NULL/i);
  assert.match(SQL, /amount_minor = trunc\(amount_minor\)/i);
  assert.match(SQL, /amount_minor >= 0/i);
  assert.match(SQL, /currency ~ '\^\[A-Z\]\{3\}\$'/i);
});

test("only the kinds spec 9.9 defines can be stored", () => {
  for (const kind of [
    "financial_external_income", "financial_realized_loss", "financial_fee", "financial_user_transfer",
    "financial_self_funding", "financial_deposit", "financial_internal_move", "financial_unverified",
  ]) {
    assert.ok(SQL.includes(`'${kind}'`), `${kind} must be an allowed kind`);
  }
});

test("the table is service-only and holds nothing secret", () => {
  assert.match(SQL, /ENABLE ROW LEVEL SECURITY/i);
  assert.match(SQL, /REVOKE ALL ON TABLE public\.lm_agent_earnings FROM PUBLIC, anon, authenticated/i);
  assert.doesNotMatch(SQL, /\b(private_key|privatekey|mnemonic|seed|secret)\b/i);
});

test("the additive precision migration stores exactly one exact amount representation", () => {
  assert.match(ATOMIC_SQL, /ADD COLUMN IF NOT EXISTS amount_atomic numeric/i);
  assert.match(ATOMIC_SQL, /ADD COLUMN IF NOT EXISTS amount_decimals smallint/i);
  assert.match(ATOMIC_SQL, /ALTER COLUMN amount_minor DROP NOT NULL/i);
  assert.match(ATOMIC_SQL, /amount_atomic = trunc\(amount_atomic\)/i);
  assert.match(ATOMIC_SQL, /amount_decimals BETWEEN 0 AND 6/i);
  assert.match(ATOMIC_SQL, /amount_minor IS NOT NULL AND amount_atomic IS NULL/i);
  assert.match(ATOMIC_SQL, /amount_minor IS NULL AND amount_atomic IS NOT NULL/i);
  assert.doesNotMatch(ATOMIC_SQL, /\b(UPDATE|DELETE FROM|DROP TABLE)\b/i);
});

test("the additive chain migration accepts EVM and Solana proofs without changing rows", () => {
  assert.match(SOLANA_SQL, /DROP CONSTRAINT IF EXISTS lm_agent_earnings_wallet_address_check/i);
  assert.match(SOLANA_SQL, /wallet_address ~ '\^0x\[0-9a-fA-F\]\{40\}\$'/i);
  assert.match(SOLANA_SQL, /wallet_address ~ '\^\[1-9A-HJ-NP-Za-km-z\]\{32,44\}\$'/i);
  assert.match(SOLANA_SQL, /tx_hash ~ '\^0x\[0-9a-fA-F\]\{64\}\$'/i);
  assert.match(SOLANA_SQL, /tx_hash ~ '\^\[1-9A-HJ-NP-Za-km-z\]\{87,88\}\$'/i);
  assert.match(SOLANA_SQL, /VALIDATE CONSTRAINT lm_agent_earnings_wallet_address_check/i);
  assert.match(SOLANA_SQL, /VALIDATE CONSTRAINT lm_agent_earnings_tx_hash_check/i);
  assert.doesNotMatch(SOLANA_SQL, /\b(UPDATE|DELETE FROM|DROP TABLE)\b/i);
});
