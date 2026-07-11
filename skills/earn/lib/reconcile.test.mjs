// reconcile.test.mjs — pure-logic + I/O tests for wallet-anchored ledger truth (#1 baseline + #2 scope).
// Run: node --test skills/earn/lib/reconcile.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { readLedger } from "../../_shared/lib/ledger.mjs";
import {
  computeDrift, recordedEarnSince, lastSnapshot, buildReconcileLine, reconcile, scopeToWallet,
} from "./reconcile.mjs";

// ---- computeDrift ----------------------------------------------------------
test("computeDrift books the loss the ledger missed", () => {
  assert.equal(computeDrift(4.95, 12.79, 1.55), -9.39);
});
test("computeDrift zero when wallet matches recorded earns", () => {
  assert.equal(computeDrift(11.0, 10.0, 1.0), 0);
});

// ---- recordedEarnSince -----------------------------------------------------
test("recordedEarnSince sums only non-reconcile lines after ts", () => {
  const rows = [
    { ts: 100, source: "polymarket-redeem", net_usdc: 2 },
    { ts: 90, source: "polymarket-redeem", net_usdc: 5 },
    { ts: 110, source: "reconcile", net_usdc: -9 },
    { ts: 120, source: "gig", net_usdc: 0.02 },
  ];
  assert.equal(recordedEarnSince(rows, 95), 2.02);
});

// ---- lastSnapshot ----------------------------------------------------------
test("lastSnapshot returns latest reconcile with balance_after", () => {
  const rows = [
    { ts: 1, source: "reconcile", balance_after: 12.79 },
    { ts: 2, source: "gig", net_usdc: 0.02 },
    { ts: 3, source: "reconcile", balance_after: 4.95 },
  ];
  assert.deepEqual(lastSnapshot(rows), { ts: 3, source: "reconcile", balance_after: 4.95 });
});
test("lastSnapshot null when none", () => {
  assert.equal(lastSnapshot([{ ts: 1, source: "gig" }]), null);
});

// ---- buildReconcileLine ----------------------------------------------------
test("buildReconcileLine marks losses, never external", () => {
  const line = buildReconcileLine("0xabc", -9.39, 4.95, 555);
  assert.equal(line.source, "reconcile");
  assert.equal(line.net_usdc, -9.39);
  assert.equal(line.balance_after, 4.95);
  assert.equal(line.external, undefined);
  assert.match(line.task, /loss/);
});

// ---- scopeToWallet (#2) ----------------------------------------------------
test("scopeToWallet keeps only the own wallet's rows (case-insensitive)", () => {
  const rows = [
    { wallet: "0x904B", source: "polymarket-redeem", net_usdc: 1 },
    { wallet: "0xA3CDD4", source: "x402", net_usdc: 5 },
    { wallet: "0x904b", source: "reconcile", balance_after: 3 },
    { source: "gig", net_usdc: 9 }, // walletless excluded when filtering
  ];
  const out = scopeToWallet(rows, "0x904b");
  assert.equal(out.length, 2);
  assert.ok(out.every((r) => String(r.wallet).toLowerCase() === "0x904b"));
});
test("scopeToWallet no filter returns all when ownWallet omitted", () => {
  const rows = [{ wallet: "0x1" }, { wallet: "0x2" }];
  assert.equal(scopeToWallet(rows).length, 2);
});

// ---- reconcile I/O ---------------------------------------------------------
test("reconcile: baseline then books a subsequent loss; ledger total == wallet delta", async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "recon-"));
  const led = path.join(dir, "earn-ledger.jsonl");
  await fs.writeFile(led, "");
  const W = "0xwallet";
  let r = await reconcile(W, led, async () => 12.79, 1000);
  assert.equal(r.baseline, true);
  await fs.appendFile(led, JSON.stringify({ ts: 1500, source: "polymarket-redeem", net_usdc: 1.55 }) + "\n");
  r = await reconcile(W, led, async () => 4.95, 2000);
  assert.equal(r.drift, -9.39);
  const rows = await readLedger(led);
  const since = rows.filter((x) => x.ts >= 1500);
  const total = since.reduce((s, x) => s + Number(x.net_usdc || 0), 0);
  assert.equal(Math.round(total * 100) / 100, -7.84);
});

test("reconcile: fail-closed on balance fetch failure (books nothing)", async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "recon-"));
  const led = path.join(dir, "earn-ledger.jsonl");
  await fs.writeFile(led, "");
  const r = await reconcile("0xw", led, async () => null, 1);
  assert.equal(r.ok, false);
  assert.equal((await readLedger(led)).length, 0);
});

// #2: wallet-scoped reconcile ignores a foreign wallet's rows in a shared file
test("reconcile: ownWallet scoping ignores foreign-wallet rows in a shared ledger", async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "recon-"));
  const led = path.join(dir, "earn-ledger.jsonl");
  await fs.writeFile(led, "");
  const PM = "0x904b";
  // baseline for pm at $10
  await reconcile(PM, led, async () => 10.0, 1000, PM);
  // a FOREIGN wallet's big earn row lands in the same file — must NOT affect pm's drift
  await fs.appendFile(led, JSON.stringify({ ts: 1500, wallet: "0xa3cdd4", source: "x402", net_usdc: 999 }) + "\n");
  // pm's own real earn +2
  await fs.appendFile(led, JSON.stringify({ ts: 1600, wallet: PM, source: "polymarket-redeem", net_usdc: 2 }) + "\n");
  // pm wallet actually dropped to $8 (a $4 loss hidden). drift = (8-10) - 2 = -4, NOT -1001
  const r = await reconcile(PM, led, async () => 8.0, 2000, PM);
  assert.equal(r.drift, -4);
});
