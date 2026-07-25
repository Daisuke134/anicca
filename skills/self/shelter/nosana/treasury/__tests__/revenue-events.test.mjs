// node:test — revenue-events.mjs: read/shape side of the (currently unwired) shelter-revenue.jsonl
// ledger. Exercises real filesystem I/O against a temp dir (mirrors shelter-cost-ledger.test.js's
// own approach), never against the real state dir.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { readShelterRevenueEvents, buildRevenueEventRecord } from "../revenue-events.mjs";
import { appendChild } from "../../../../spawn/lib/ledger.js";

function tmpFile() {
  return path.join(fs.mkdtempSync(path.join(os.tmpdir(), "shelter-revenue-test-")), "shelter-revenue.jsonl");
}

test("readShelterRevenueEvents: a file that has never been created honestly reports sourceExists:false, rows: []", () => {
  const file = tmpFile(); // mkdtemp created the dir, but this exact file was never written
  const result = readShelterRevenueEvents(file);
  assert.equal(result.sourceExists, false);
  assert.deepEqual(result.rows, []);
});

test("readShelterRevenueEvents: an existing-but-empty ledger is distinct from a missing one", () => {
  const file = tmpFile();
  fs.writeFileSync(file, "");
  const result = readShelterRevenueEvents(file);
  assert.equal(result.sourceExists, true);
  assert.deepEqual(result.rows, []);
});

test("readShelterRevenueEvents reads real appended rows back", () => {
  const file = tmpFile();
  const record = buildRevenueEventRecord({ ts: 1, amountUsd: 5, from: "0xabc", chain: "base", txSignature: "0xdeadbeef", source: "x402" });
  appendChild(file, record);
  const result = readShelterRevenueEvents(file);
  assert.equal(result.sourceExists, true);
  assert.equal(result.rows.length, 1);
  assert.deepEqual(result.rows[0], record);
});

test("buildRevenueEventRecord throws on any missing required field", () => {
  assert.throws(() => buildRevenueEventRecord({ amountUsd: 1, from: "0xabc", chain: "base" }), /ts is required/);
  assert.throws(() => buildRevenueEventRecord({ ts: 1, from: "0xabc", chain: "base" }), /amountUsd is required/);
  assert.throws(() => buildRevenueEventRecord({ ts: 1, amountUsd: 1, chain: "base" }), /from is required/);
  assert.throws(() => buildRevenueEventRecord({ ts: 1, amountUsd: 1, from: "0xabc" }), /chain is required/);
});

test("buildRevenueEventRecord fails closed on a negative/non-finite amountUsd", () => {
  assert.throws(() => buildRevenueEventRecord({ ts: 1, amountUsd: -1, from: "0xabc", chain: "base" }), /non-negative finite number/);
  assert.throws(() => buildRevenueEventRecord({ ts: 1, amountUsd: NaN, from: "0xabc", chain: "base" }), /non-negative finite number/);
});

test("buildRevenueEventRecord defaults optional fields to null, never undefined (JSON-safe)", () => {
  const record = buildRevenueEventRecord({ ts: 1, amountUsd: 1, from: "0xabc", chain: "base" });
  assert.equal(record.txSignature, null);
  assert.equal(record.source, null);
});
