// node:test — earn ledger: append-only, immutable, net derivation + GATE-0 classification.
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { deriveLine, isProfitable, appendLedger, readLedger, alreadyRecordedSig } from "../ledger.mjs";

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

test("isProfitable true only for EXTERNAL revenue: net>0 AND status 0x1 AND external:true AND not a swap", () => {
  // external 0xwork/x402 inbound — the only GATE-0-eligible shape.
  assert.equal(isProfitable({ source: "0xwork", net_usdc: 0.1, status: "0x1", tx: "0x1", external: true }), true);
  assert.equal(isProfitable({ source: "0xwork", net_usdc: 0.1, status: "0x0", tx: "0x1", external: true }), false); // reverted tx
  assert.equal(isProfitable({ source: "0xwork", net_usdc: -0.1, status: "0x1", tx: "0x1", external: true }), false); // loss
  assert.equal(isProfitable({ net_usdc: 0.1 }), false); // narrate-only (no tx/status)
  assert.equal(isProfitable({ source: "0xwork", net_usdc: 0.1, status: "0x1", external: true }), false); // no tx hash
  // swaps are asset rotation — NEVER GATE-0, even with a real 0x1 tx and positive net.
  assert.equal(isProfitable({ source: "swap-eth-usdc", net_usdc: 0.1, status: "0x1", tx: "0x1" }), false);
  // any line missing external:true is rejected (the false-green guard).
  assert.equal(isProfitable({ source: "0xwork", net_usdc: 0.1, status: "0x1", tx: "0x1" }), false);
});

// --- Solana support (promote.fun clip-earn pays USDC on Solana; the gate must accept a
//     confirmed signature line, not only an EVM 0x1 receipt) -------------------------------
test("deriveLine carries the Solana fields sig/confirmed/chain (else the persisted line loses the proof)", () => {
  const l = deriveLine({ wallet: "soL", source: "promote.fun", task: "clip", earn_usdc: 0.5, cost_usdc: 0.01,
    sig: "52RZsig", confirmed: true, chain: "solana", external: true, wake: "w1" });
  assert.equal(l.sig, "52RZsig");
  assert.equal(l.confirmed, true);
  assert.equal(l.chain, "solana");
  assert.equal(l.external, true);
  assert.equal(l.net_usdc, 0.49);
  assert.equal(l.tx, undefined, "no EVM tx on a Solana line");
});

test("isProfitable accepts a Solana line: net>0 AND sig AND confirmed AND external AND not-swap", () => {
  assert.equal(isProfitable({ source: "promote.fun", net_usdc: 0.5, sig: "sigA", confirmed: true, external: true, chain: "solana" }), true);
  assert.equal(isProfitable({ source: "promote.fun", net_usdc: 0.5, sig: "sigA", confirmed: false, external: true }), false); // not confirmed
  assert.equal(isProfitable({ source: "promote.fun", net_usdc: 0.5, sig: "sigA", confirmed: true }), false); // no external
  assert.equal(isProfitable({ source: "promote.fun", net_usdc: 0, sig: "sigA", confirmed: true, external: true }), false); // net 0
  assert.equal(isProfitable({ source: "promote.fun", net_usdc: 0.5, confirmed: true, external: true }), false); // no sig
});

test("isProfitable still rejects the OLD EVM negatives unchanged (no regression)", () => {
  assert.equal(isProfitable({ source: "0xwork", net_usdc: 0.1, status: "0x1", tx: "0x1", external: true }), true);
  assert.equal(isProfitable({ source: "0xwork", net_usdc: 0.1, status: "0x0", tx: "0x1", external: true }), false);
  assert.equal(isProfitable({ source: "swap-eth-usdc", net_usdc: 0.1, sig: "s", confirmed: true, external: true }), false); // swap never counts, even on Solana
  assert.equal(isProfitable({ net_usdc: 0.1 }), false);
});

test("alreadyRecordedSig: true only when a line with that sig already exists in the ledger", async () => {
  const f = await tmpFile();
  assert.equal(await alreadyRecordedSig(f, "sigX"), false); // missing file
  await appendLedger(f, deriveLine({ wallet: "soL", source: "promote.fun", task: "c", earn_usdc: 0.3, cost_usdc: 0, sig: "sigX", confirmed: true, chain: "solana", external: true, wake: "w1" }));
  assert.equal(await alreadyRecordedSig(f, "sigX"), true);
  assert.equal(await alreadyRecordedSig(f, "sigY"), false);
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
