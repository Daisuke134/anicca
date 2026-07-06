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
    JSON.stringify({ wallet: "0xa", source: "x402", task: "sell", earn_usdc: 0.5, cost_usdc: 0.1, tx: "0xfeed", status: "0x1", external: true, wake: "w1" }),
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

// --- P1 (spec §3/§4): record() also returns the cumulative earn>spend guard's verdict ------
test("record() reports halt.halt=false while this wallet+source stays cumulatively net-positive", async () => {
  const f = await tmpLedger();
  const { halt } = await record(
    JSON.stringify({ wallet: "0xa", source: "x402", task: "sell", earn_usdc: 1, cost_usdc: 0.2, tx: "0x1", status: "0x1", external: true, wake: "w1" }),
    f
  );
  assert.equal(halt.halt, false);
});

test("record() reports halt.halt=true the pass that pushes cumulative net negative for this wallet+source", async () => {
  const f = await tmpLedger();
  await record(
    JSON.stringify({ wallet: "0xa", source: "x402", task: "sell", earn_usdc: 1, cost_usdc: 0, tx: "0x1", status: "0x1", external: true, wake: "w1" }),
    f
  );
  const { halt } = await record(
    JSON.stringify({ wallet: "0xa", source: "x402", task: "sell", earn_usdc: 0, cost_usdc: 2, tx: "0x2", status: "0x1", external: true, wake: "w2" }),
    f
  );
  assert.equal(halt.halt, true);
  assert.equal(halt.reason, "cumulative-net-below-reserve");
});

test("record() CLI stdout contract is UNCHANGED by the halt guard: still exactly PROFITABLE/NARRATE (run.sh does an exact-match `[ \"$OUT\" = \"PROFITABLE\" ]`)", async () => {
  const f = await tmpLedger();
  // drive this wallet+source cumulatively negative first
  await record(JSON.stringify({ wallet: "0xz", source: "x402", earn_usdc: 0, cost_usdc: 5, wake: "w1" }), f);
  const { execFile } = await import("node:child_process");
  const { promisify } = await import("node:util");
  const run = promisify(execFile);
  const recordMjs = new URL("../lib/record.mjs", import.meta.url).pathname;
  const json = JSON.stringify({ wallet: "0xz", source: "x402", task: "sell", earn_usdc: 1, cost_usdc: 0, tx: "0x1", status: "0x1", external: true, wake: "w2" });
  const { stdout, stderr } = await run("node", [recordMjs, json, f]);
  assert.equal(stdout.trim(), "PROFITABLE", "stdout must be the bare token only — no extra HALT line");
  assert.match(stderr, /P1-GUARD HALT/, "the halt reason is reported on stderr, not stdout");
});
