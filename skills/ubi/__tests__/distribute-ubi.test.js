// node:test — the bridge wiring: proves the data-contract fixes, fully OFFLINE + deterministic.
// (1) B1/B2: a run.sh-shape line (earn_usdc/cost_usdc, NO net_usdc) is re-derived via deriveLine
//     so isProfitable passes — without this the dry plan would be 'funding_not_profitable'.
// (2) N1: sibling-AI recipients are read from children.jsonl rows' `wallet` field (not childWallet).
// (3) B3: in dry-run the bridge SKIPS the live RPC balance read, so the test passes ONLINE too
//     (no network; the fake wallet's real balance would otherwise be 0 -> insufficient_balance).
// UBI_DRY_RUN=1 so NOTHING is sent on-chain; the overspend test injects opts.balanceFn (no RPC).
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { distribute } from "../distribute-ubi.mjs";

const SELF = "0x9999999999999999999999999999999999999999";
const CHILD = "0x1111111111111111111111111111111111111111";

test("B1/B2 + N1: run.sh-shape line (no net_usdc) is derived; child `wallet` is the AI recipient", async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "ubi-"));
  const childrenFile = path.join(dir, "children.jsonl");
  const ubiLedger = path.join(dir, "ubi-ledger.jsonl");
  // child-spec.js:37 shape: the wallet is under `wallet`, status active.
  await fs.writeFile(childrenFile, JSON.stringify({ child_id: "anicca-c001", wallet: CHILD, status: "active" }) + "\n");
  // EXACT run.sh 0xwork $JSON shape: earn_usdc/cost_usdc + external:true, but NO net_usdc.
  const rawLine = { wallet: SELF, source: "0xwork", task: "t1", earn_usdc: 1.0, cost_usdc: 0, tx: "0x" + "a".repeat(64), status: "0x1", external: true, wake: "w-derive" };
  process.env.UBI_DRY_RUN = "1";
  process.env.UBI_MIN_POOL_USDC = "0.0001";
  delete process.env.UBI_HUMAN_WALLETS; // AI-only: forces the children.jsonl `wallet` read to matter
  const { line } = await distribute(rawLine, { childrenFile, ubiLedger });
  // If net_usdc were undefined (the bug) -> outcome 'skipped'/funding_not_profitable. Derived -> 'dry'.
  assert.equal(line.outcome, "dry");
  assert.equal(line.recipients, 1);              // the child `wallet` was picked up (N1 fixed)
  assert.ok(line.pool_usdc > 0);                 // net_usdc derived from earn/cost (B1/B2 fixed)
  await fs.rm(dir, { recursive: true, force: true });
});

test("B3: NON-dry-run threads opts.balanceFn into the overspend guard (no RPC) — pool>balance skips", async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "ubi-"));
  const childrenFile = path.join(dir, "children.jsonl");
  const ubiLedger = path.join(dir, "ubi-ledger.jsonl");
  await fs.writeFile(childrenFile, JSON.stringify({ child_id: "anicca-c001", wallet: CHILD, status: "active" }) + "\n");
  const rawLine = { wallet: SELF, source: "0xwork", task: "t1", earn_usdc: 1.0, cost_usdc: 0, tx: "0x" + "a".repeat(64), status: "0x1", external: true, wake: "w-overspend" };
  delete process.env.UBI_DRY_RUN;                // real path -> the live-balance guard is active
  process.env.UBI_MIN_POOL_USDC = "0.0001";
  delete process.env.UBI_HUMAN_WALLETS;
  // inject a balance BELOW the 0.1 USDC pool via opts.balanceFn — deterministic, no Base RPC call,
  // and no executor reached (skipped never spawns python). Proves the bridge wires balanceFn correctly.
  const { line, sent } = await distribute(rawLine, { childrenFile, ubiLedger, balanceFn: async () => 0 });
  assert.equal(sent, false);
  assert.equal(line.outcome, "skipped");
  assert.equal(line.reason, "insufficient_balance");
  await fs.rm(dir, { recursive: true, force: true });
});
