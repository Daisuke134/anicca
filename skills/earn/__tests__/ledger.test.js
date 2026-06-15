// node:test — earn ledger: append-only, immutable, net derivation + GATE-0 classification.
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { deriveLine, isProfitable, appendLedger, readLedger } from "../lib/ledger.mjs";

async function tmpFile() {
  const d = await fs.mkdtemp(path.join(os.tmpdir(), "earn-ledger-"));
  return path.join(d, "earn-ledger.jsonl");
}

test("deriveLine computes net_usdc = earn - cost and stamps ts", () => {
  const l = deriveLine({ wallet: "0xabc", source: "x402", task: "t1", earn_usdc: 0.42, cost_usdc: 0.05, tx: "0xdead", status: "0x1", wake: "w1" });
  assert.equal(l.net_usdc, 0.37);
  assert.equal(l.wallet, "0xabc");
  assert.equal(l.source, "x402");
  assert.equal(typeof l.ts, "number");
  assert.ok(l.ts > 0);
});

test("isProfitable true only when net>0 AND status 0x1 (narrate-only never counts)", () => {
  assert.equal(isProfitable({ net_usdc: 0.1, status: "0x1", tx: "0x1" }), true);
  assert.equal(isProfitable({ net_usdc: 0.1, status: "0x0", tx: "0x1" }), false); // reverted tx
  assert.equal(isProfitable({ net_usdc: -0.1, status: "0x1", tx: "0x1" }), false); // loss
  assert.equal(isProfitable({ net_usdc: 0.1 }), false); // narrate-only (no tx/status)
  assert.equal(isProfitable({ net_usdc: 0.1, status: "0x1" }), false); // no tx hash
});

test("appendLedger is append-only: prior line is byte-identical after a second append", async () => {
  const f = await tmpFile();
  const a = deriveLine({ wallet: "0xa", source: "x402", task: "a", earn_usdc: 1, cost_usdc: 0, tx: "0xaa", status: "0x1", wake: "w1" });
  await appendLedger(f, a);
  const after1 = await fs.readFile(f, "utf8");
  const firstLine1 = after1.split("\n").filter(Boolean)[0];

  const b = deriveLine({ wallet: "0xa", source: "x402", task: "b", earn_usdc: 2, cost_usdc: 0, tx: "0xbb", status: "0x1", wake: "w2" });
  await appendLedger(f, b);
  const after2 = await fs.readFile(f, "utf8");
  const lines2 = after2.split("\n").filter(Boolean);

  assert.equal(lines2.length, 2, "two lines after two appends");
  assert.equal(lines2[0], firstLine1, "first line must be untouched (immutability)");
});

test("readLedger parses every JSONL line into objects", async () => {
  const f = await tmpFile();
  await appendLedger(f, deriveLine({ wallet: "0xa", source: "x402", task: "a", earn_usdc: 1, cost_usdc: 0.2, tx: "0xaa", status: "0x1", wake: "w1" }));
  await appendLedger(f, deriveLine({ wallet: "0xa", source: "litcoin", task: "b", earn_usdc: 0, cost_usdc: 0, wake: "w2" }));
  const rows = await readLedger(f);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].net_usdc, 0.8);
  assert.equal(rows[1].source, "litcoin");
});

test("readLedger returns [] for a missing file (no throw)", async () => {
  const rows = await readLedger("/no/such/path/earn-ledger.jsonl");
  assert.deepEqual(rows, []);
});
