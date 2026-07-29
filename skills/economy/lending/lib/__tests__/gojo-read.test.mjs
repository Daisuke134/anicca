// node:test — gojo-read.mjs (Phase 2a RED, anicca-agent-lending REQ-101/PROP-101f, resolves FIND-005).
// RED phase: this file is written BEFORE ../gojo-read.mjs exists, so the import itself is the first
// failing assertion (module not found). GREEN = implement to make all pass.
//
// readGojoLogRows(gojoLogPath) is a plain, SYNCHRONOUS fs.readFileSync + line-split + JSON.parse
// reader over economy/ubi's own existing __REPO_ROOT__/skills/economy/ubi/state/gojo-log.jsonl — the SAME
// shape run.sh itself already writes: {ts, recipient, recipient_wallet, surplus_above_reserve_usd,
// decision: {amount_usd, reason}, executed}. This module is READ-ONLY — it must NEVER write to that
// file (ubi.js/run.sh own it exclusively); it also never touches ledger.js (that module is this
// feature's OWN loans.jsonl ledger, a completely different file this reader is not involved with).
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { readGojoLogRows } from "../gojo-read.mjs";

function tmpJsonlFile(lines) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gojo-read-test-"));
  const file = path.join(dir, "gojo-log.jsonl");
  fs.writeFileSync(file, lines.map((l) => JSON.stringify(l)).join("\n") + "\n");
  return file;
}

test("readGojoLogRows returns [] when the file does not exist (mirrors ledger.js's own readChildren ENOENT->[] convention already established for loans.jsonl/children.jsonl in this colony)", () => {
  const missing = path.join(os.tmpdir(), "definitely-missing-gojo-" + Date.now(), "gojo-log.jsonl");
  assert.deepEqual(readGojoLogRows(missing), []);
});

test("readGojoLogRows parses the REAL run.sh row shape byte-for-byte", () => {
  const row = {
    ts: "2026-07-01T00:00:00.000Z",
    recipient: "Franklin",
    recipient_wallet: "0xFRANKLIN00000000000000000000000000000F",
    surplus_above_reserve_usd: 3.5,
    decision: { amount_usd: 1, reason: "surplus above reserve" },
    executed: false,
  };
  const file = tmpJsonlFile([row]);
  const rows = readGojoLogRows(file);
  assert.equal(rows.length, 1);
  assert.deepEqual(rows[0], row);
});

test("readGojoLogRows round-trips multiple rows in append order and skips blank lines", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gojo-read-test-"));
  const file = path.join(dir, "gojo-log.jsonl");
  fs.writeFileSync(file, '{"ts":"a","decision":{"amount_usd":1}}\n\n{"ts":"b","decision":{"amount_usd":2}}\n');
  const rows = readGojoLogRows(file);
  assert.deepEqual(rows.map((r) => r.ts), ["a", "b"]);
});

test("readGojoLogRows NEVER writes — file content is byte-identical before and after multiple reads (REQ-101's own read-only discipline: this feature never mutates ubi's gojo-log.jsonl)", () => {
  const file = tmpJsonlFile([{ ts: "a", decision: { amount_usd: 1 } }]);
  const before = fs.readFileSync(file, "utf8");
  readGojoLogRows(file);
  readGojoLogRows(file);
  const after = fs.readFileSync(file, "utf8");
  assert.equal(after, before);
});

test("readGojoLogRows tolerates a trailing-newline-only file (no rows) without throwing", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gojo-read-test-"));
  const file = path.join(dir, "gojo-log.jsonl");
  fs.writeFileSync(file, "\n");
  assert.deepEqual(readGojoLogRows(file), []);
});
