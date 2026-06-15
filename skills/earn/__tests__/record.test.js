// node:test — record bridge: appends a line + classifies profitable.
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { record } from "../lib/record.mjs";

async function tmpLedger() {
  const d = await fs.mkdtemp(path.join(os.tmpdir(), "earn-record-"));
  return path.join(d, "earn-ledger.jsonl");
}

test("record() appends a profitable line and flags it PROFITABLE", async () => {
  const f = await tmpLedger();
  const { line, profitable } = await record(
    JSON.stringify({ wallet: "0xa", source: "x402", task: "sell", earn_usdc: 0.5, cost_usdc: 0.1, tx: "0xfeed", status: "0x1", wake: "w1" }),
    f
  );
  assert.equal(line.net_usdc, 0.4);
  assert.equal(profitable, true);
  const rows = (await fs.readFile(f, "utf8")).split("\n").filter(Boolean);
  assert.equal(rows.length, 1);
});

test("record() narrate-only (no tx) is NOT profitable", async () => {
  const f = await tmpLedger();
  const { profitable } = await record(
    JSON.stringify({ wallet: "0xa", source: "x402", task: "discover", earn_usdc: 0, cost_usdc: 0, wake: "w2" }),
    f
  );
  assert.equal(profitable, false);
});
