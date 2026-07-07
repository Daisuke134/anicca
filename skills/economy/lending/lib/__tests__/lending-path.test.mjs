// node:test — lending-path.mjs (Phase 2a RED, anicca-agent-lending REQ-106/PROP-106d).
// RED phase: this file is written BEFORE ../lending-path.mjs exists, so the import itself is the
// first failing assertion (module not found). GREEN = implement to make all pass.
//
// LOANS_LEDGER_PATH is the SINGLE canonical statePath every loan-issuance lock acquisition and every
// loans.jsonl read/write must import and reuse — mirrors anicca-agent-spawn's own
// CITIZENS_REGISTRY_PATH discipline exactly (REQ-106). The actual import-identity check across every
// real call site (PROP-106d) is Tier-0 — verified in Phase 3 by a structural source-read, not here.
// This file only proves the exported constant itself has the correct shape: an absolute path ending
// in economy/lending/state/loans.jsonl, DISTINCT from anicca-agent-spawn's own children.jsonl and
// economy/ubi's colony-wallets.json (REQ-106's own Dependencies-section "never commingle two
// independently-owned record types in one physical file" discipline).
import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { LOANS_LEDGER_PATH } from "../lending-path.mjs";

test("LOANS_LEDGER_PATH is a non-empty string", () => {
  assert.equal(typeof LOANS_LEDGER_PATH, "string");
  assert.ok(LOANS_LEDGER_PATH.length > 0);
});

test("LOANS_LEDGER_PATH is an absolute filesystem path", () => {
  assert.equal(path.isAbsolute(LOANS_LEDGER_PATH), true);
});

test("LOANS_LEDGER_PATH points at a dedicated economy/lending/state/loans.jsonl file (REQ-106) — never spawn's children.jsonl or ubi's colony-wallets.json", () => {
  const normalized = LOANS_LEDGER_PATH.split(path.sep).join("/");
  assert.match(normalized, /economy\/lending\/state\/loans\.jsonl$/);
  assert.doesNotMatch(normalized, /children\.jsonl$/);
  assert.doesNotMatch(normalized, /colony-wallets\.json$/);
});

test("LOANS_LEDGER_PATH is a stable import identity — re-importing the module yields the SAME value (PROP-106d's own import-identity discipline depends on every call site converging on one constant, never independently recomputed strings)", async () => {
  const mod2 = await import("../lending-path.mjs");
  assert.equal(mod2.LOANS_LEDGER_PATH, LOANS_LEDGER_PATH);
});
