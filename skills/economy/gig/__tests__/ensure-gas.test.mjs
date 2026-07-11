// node:test — lib/ensure-gas.mjs (franklin-reputation-gasless G1, RED phase). Every real on-chain call
// (getBalance/sendTransaction/waitForTransactionReceipt) is dependency-injected via `publicClient`/
// `walletClientFactory` in ensureGas() -- these tests exercise OUR OWN decision logic (threshold, testnet
// vs mainnet branch, hard-cap enforcement, daily-drip-count fail-closed refusal) with fast, deterministic
// fakes, never a real network call. decideGasAction/countRecentDrips are pure -- no injection needed.
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  decideGasAction,
  countRecentDrips,
  ensureGas,
  DEFAULT_GAS_THRESHOLD_WEI,
  MAX_DRIP_WEI_PER_OP,
} from "../lib/ensure-gas.mjs";

async function tmpLog() {
  const d = await fs.mkdtemp(path.join(os.tmpdir(), "ensure-gas-test-"));
  return path.join(d, "gas-drip-log.jsonl");
}

// ============ decideGasAction (pure) ============

test("decideGasAction: balance >= threshold -> 'ok', regardless of network", () => {
  const r1 = decideGasAction({ balanceWei: 10n ** 18n, thresholdWei: 1000n, isMainnet: false });
  assert.equal(r1.action, "ok");
  const r2 = decideGasAction({ balanceWei: 1000n, thresholdWei: 1000n, isMainnet: true });
  assert.equal(r2.action, "ok", "exactly-at-threshold counts as ok (boundary)");
});

test("decideGasAction: testnet + low balance -> 'drip' (never 'needs_gas')", () => {
  const r = decideGasAction({ balanceWei: 0n, thresholdWei: 1000n, isMainnet: false });
  assert.equal(r.action, "drip");
});

test("★MONEY-SAFETY★ decideGasAction: mainnet + low balance -> 'needs_gas', NEVER 'drip' (no auto-spend on mainnet)", () => {
  const r = decideGasAction({ balanceWei: 0n, thresholdWei: 1000n, isMainnet: true });
  assert.equal(r.action, "needs_gas");
  assert.equal(r.requiredWei, "1000");
});

// ============ countRecentDrips (pure) ============

test("countRecentDrips: counts only rows for the given address within the window", () => {
  const now = Date.parse("2026-07-12T12:00:00.000Z");
  const rows = [
    { address: "0xAAA", ts: new Date(now - 1000).toISOString() }, // within window
    { address: "0xAAA", ts: new Date(now - 25 * 3600 * 1000).toISOString() }, // outside 24h window
    { address: "0xBBB", ts: new Date(now - 1000).toISOString() }, // different address
  ];
  assert.equal(countRecentDrips(rows, "0xAAA", now, 24 * 3600 * 1000), 1);
  assert.equal(countRecentDrips(rows, "0xaaa", now, 24 * 3600 * 1000), 1, "address match is case-insensitive");
  assert.equal(countRecentDrips(rows, "0xBBB", now, 24 * 3600 * 1000), 1);
  assert.equal(countRecentDrips(rows, "0xCCC", now, 24 * 3600 * 1000), 0);
});

test("countRecentDrips: malformed rows are ignored, never throw", () => {
  const now = Date.now();
  const rows = [null, {}, { address: "0xAAA", ts: "not-a-date" }, { address: 123, ts: new Date().toISOString() }];
  assert.equal(countRecentDrips(rows, "0xAAA", now), 0);
});

// ============ ensureGas (impure, real I/O dependency-injected) ============

function fakePublicClient(balanceWei) {
  return {
    getBalance: async () => BigInt(balanceWei),
    waitForTransactionReceipt: async ({ hash }) => ({ status: "success", transactionHash: hash }),
  };
}

test("ensureGas: sufficient balance -> ok:true, action:'ok', no drip attempted", async () => {
  const dripLogPath = await tmpLog();
  let dripCalled = false;
  const result = await ensureGas({
    address: "0xSomeone000000000000000000000000000000",
    isMainnet: false,
    publicClient: fakePublicClient(10n ** 18n),
    sendDripFn: async () => {
      dripCalled = true;
      return { hash: "0xshouldnotbecalled" };
    },
    dripLogPath,
  });
  assert.equal(result.ok, true);
  assert.equal(result.action, "ok");
  assert.equal(dripCalled, false, "must never attempt a drip when balance is already sufficient");
});

test("★MONEY-SAFETY★ ensureGas: mainnet + low balance -> ok:false, structured 'needs_gas' error, NO drip function ever called", async () => {
  const dripLogPath = await tmpLog();
  let dripCalled = false;
  const result = await ensureGas({
    address: "0xSomeone000000000000000000000000000000",
    isMainnet: true,
    publicClient: fakePublicClient(0n),
    sendDripFn: async () => {
      dripCalled = true;
      return { hash: "0xshouldnotbecalled" };
    },
    dripLogPath,
  });
  assert.equal(result.ok, false);
  assert.equal(result.action, "needs_gas");
  assert.equal(dripCalled, false, "mainnet must NEVER auto-spend, MUST per spec §4");
});

test("ensureGas: testnet + low balance -> auto-drips via sendDripFn, hard-capped at MAX_DRIP_WEI_PER_OP even if a larger amount is requested", async () => {
  const dripLogPath = await tmpLog();
  let sentAmount = null;
  const result = await ensureGas({
    address: "0xSomeone000000000000000000000000000000",
    isMainnet: false,
    publicClient: fakePublicClient(0n),
    dripAmountWei: MAX_DRIP_WEI_PER_OP * 10n, // caller asks for way more than the hard cap
    sendDripFn: async ({ amountWei }) => {
      sentAmount = amountWei;
      return { hash: "0xdriptx1" };
    },
    dripLogPath,
  });
  assert.equal(result.ok, true);
  assert.equal(result.action, "dripped");
  assert.equal(sentAmount, MAX_DRIP_WEI_PER_OP, "★MONEY-SAFETY★ the hard cap must be enforced regardless of caller input");
  assert.equal(result.amountWei, MAX_DRIP_WEI_PER_OP.toString());
});

test("ensureGas: testnet drip refuses (fail-closed) once the daily drip cap for that address is reached, no further drip sent", async () => {
  const dripLogPath = await tmpLog();
  const address = "0xSomeone000000000000000000000000000000";
  let dripCount = 0;
  const opts = {
    address,
    isMainnet: false,
    publicClient: fakePublicClient(0n),
    sendDripFn: async () => {
      dripCount += 1;
      return { hash: `0xdriptx${dripCount}` };
    },
    dripLogPath,
    maxDripsPerDay: 2,
  };
  const r1 = await ensureGas(opts);
  const r2 = await ensureGas(opts);
  const r3 = await ensureGas(opts);
  assert.equal(r1.ok, true);
  assert.equal(r2.ok, true);
  assert.equal(r3.ok, false, "3rd drip within the day must be refused (cap=2)");
  assert.equal(r3.action, "needs_gas");
  assert.equal(dripCount, 2, "sendDripFn must never be called a 3rd time once the cap is hit");
});

test("ensureGas: testnet drip with no funder configured -> ok:false, needs_gas, no throw", async () => {
  const dripLogPath = await tmpLog();
  const result = await ensureGas({
    address: "0xSomeone000000000000000000000000000000",
    isMainnet: false,
    publicClient: fakePublicClient(0n),
    sendDripFn: null, // simulates GIG_GAS_FUNDER_PRIVATE_KEY unset in production wiring
    dripLogPath,
  });
  assert.equal(result.ok, false);
  assert.equal(result.action, "needs_gas");
});

test("ensureGas: a reverted drip tx is reported as failure, never as ok:true", async () => {
  const dripLogPath = await tmpLog();
  const result = await ensureGas({
    address: "0xSomeone000000000000000000000000000000",
    isMainnet: false,
    publicClient: {
      getBalance: async () => 0n,
      waitForTransactionReceipt: async () => ({ status: "reverted" }),
    },
    sendDripFn: async () => ({ hash: "0xrevertedtx" }),
    dripLogPath,
  });
  assert.equal(result.ok, false);
});

test("ensureGas: no address -> ok:false, never crashes", async () => {
  const result = await ensureGas({ isMainnet: false, publicClient: fakePublicClient(0n) });
  assert.equal(result.ok, false);
});

// ============ FIND-003 (adversary round 2): both exception branches, incl. the FIND-001 fix proof ============

test("★FIND-003★ ensureGas: sendDripFn itself throws (tx never broadcasts) -> ok:false, needs_gas, and the daily cap is NOT consumed (nothing was ever broadcast)", async () => {
  const dripLogPath = await tmpLog();
  const address = "0xSomeone000000000000000000000000000000";
  let sendAttempts = 0;
  const result = await ensureGas({
    address,
    isMainnet: false,
    publicClient: fakePublicClient(0n),
    sendDripFn: async () => {
      sendAttempts += 1;
      throw new Error("network down, tx never sent");
    },
    dripLogPath,
    maxDripsPerDay: 1,
  });
  assert.equal(result.ok, false);
  assert.equal(result.action, "needs_gas");
  assert.match(result.reason, /drip tx failed/);
  assert.equal(sendAttempts, 1);

  // a real drip never broadcast (sendDripFn threw before any hash existed) -- a retry against the same
  // cap must still be allowed, proving this failure mode never consumes a cap slot.
  const retry = await ensureGas({
    address,
    isMainnet: false,
    publicClient: fakePublicClient(0n),
    sendDripFn: async () => ({ hash: "0xretrytx1" }),
    dripLogPath,
    maxDripsPerDay: 1,
  });
  assert.equal(retry.ok, true, "a broadcast-never-attempted failure must not consume a daily-cap slot");
  assert.equal(retry.action, "dripped");
});

test("★FIND-001/FIND-003★ ensureGas: waitForTransactionReceipt throws AFTER broadcast -> ok:false, BUT the drip IS counted against the daily cap so a retry cannot double-drip past the cap", async () => {
  const dripLogPath = await tmpLog();
  const address = "0xSomeone000000000000000000000000000000";
  let sendCount = 0;
  const opts = {
    address,
    isMainnet: false,
    publicClient: {
      getBalance: async () => 0n,
      waitForTransactionReceipt: async () => {
        throw new Error("RPC timeout waiting for receipt");
      },
    },
    sendDripFn: async () => {
      sendCount += 1;
      return { hash: `0xdriptx${sendCount}` };
    },
    dripLogPath,
    maxDripsPerDay: 1,
  };

  const r1 = await ensureGas(opts);
  assert.equal(r1.ok, false);
  assert.equal(r1.action, "needs_gas");
  assert.match(r1.reason, /receipt wait failed/);
  assert.equal(r1.tx, "0xdriptx1");
  assert.equal(sendCount, 1, "the drip DID broadcast before the receipt-wait threw");

  // FIND-001: a retry (caller re-invoking ensureGas after the exception) must be refused by the cap --
  // NOT allowed to broadcast a second real drip. Pre-fix, appendDripLog never ran on this path, so the
  // cap counter stayed at 0 and this retry would have broadcast a second tx (sendCount would reach 2).
  const r2 = await ensureGas(opts);
  assert.equal(r2.ok, false);
  assert.equal(r2.action, "needs_gas");
  assert.match(r2.reason, /daily drip cap/);
  assert.equal(sendCount, 1, "sendDripFn must NOT be called again -- the already-broadcast first drip already exhausted the cap (proves FIND-001 fix)");
});
