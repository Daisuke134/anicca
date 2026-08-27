import { test } from "node:test";
import assert from "node:assert/strict";
import {
  planRefill,
  executeRefill,
  DEFAULT_SUBWALLET_TARGET_NOS,
  DEFAULT_SUBWALLET_TARGET_SOL,
  DEFAULT_MIN_BRIDGE_USD,
  DEFAULT_KEEP_ON_BASE_USD,
} from "../refill.mjs";

test("default refill target covers one fixed escrow plus the move-out reserve", () => {
  assert.equal(DEFAULT_SUBWALLET_TARGET_NOS, 0.75);
  assert.ok(DEFAULT_SUBWALLET_TARGET_NOS >= 0.3456 + 0.34);
});

test("default shelter target covers one fixed market escrow plus the move-out reserve", () => {
  const liveMarketEscrowNos = 48 * 7200 / 1_000_000;
  const moveOutReserveNos = 0.34;
  assert.ok(
    DEFAULT_SUBWALLET_TARGET_NOS >= liveMarketEscrowNos + moveOutReserveNos,
    `${DEFAULT_SUBWALLET_TARGET_NOS} NOS cannot cover ${liveMarketEscrowNos} escrow + ${moveOutReserveNos} reserve`,
  );
});

// ---------------------------------------------------------------------------------------------
// planRefill — targets the SUB-WALLET (the wallet that actually pays rent), not the treasury.
// ---------------------------------------------------------------------------------------------

test("does nothing when the shelter wallet (the wallet that actually pays rent) is already stocked", () => {
  const p = planRefill({
    subNosBalance: DEFAULT_SUBWALLET_TARGET_NOS + 1,
    subSolBalance: DEFAULT_SUBWALLET_TARGET_SOL + 1,
    ownerNosBalance: 0,
    ownerSolBalance: 0,
    baseUsdc: 50,
  });
  assert.equal(p.act, false);
});

test("moves money when the shelter wallet is short, the treasury can't cover it, and Base has revenue to spare", () => {
  const p = planRefill({
    subNosBalance: 0.02,
    subSolBalance: DEFAULT_SUBWALLET_TARGET_SOL,
    ownerNosBalance: 0,
    ownerSolBalance: 0,
    baseUsdc: 20,
  });
  assert.equal(p.act, true);
  assert.ok(p.bridgeUsd > 0);
  assert.equal(p.swapNeeded, true);
});

test("never bridges the working capital Base itself needs", () => {
  // Base pays for inference and for Modal boxes; draining it to buy NOS trades one starvation
  // for another.
  const p = planRefill({
    subNosBalance: 0,
    subSolBalance: DEFAULT_SUBWALLET_TARGET_SOL,
    ownerNosBalance: 0,
    ownerSolBalance: 0,
    baseUsdc: DEFAULT_KEEP_ON_BASE_USD + 1,
  });
  assert.ok(p.bridgeUsd <= 1);
});

test("refuses a bridge too small to be worth its fees", () => {
  const p = planRefill({
    subNosBalance: 0,
    subSolBalance: DEFAULT_SUBWALLET_TARGET_SOL,
    ownerNosBalance: 0,
    ownerSolBalance: 0,
    baseUsdc: DEFAULT_KEEP_ON_BASE_USD + 0.01,
  });
  assert.equal(p.act, false);
  assert.match(p.reason, /too small/i);
});

test("bridges to cover a pure SOL shortfall without a swap — the bridge lands as native SOL already", () => {
  const p = planRefill({
    subNosBalance: DEFAULT_SUBWALLET_TARGET_NOS,
    subSolBalance: 0.0001,
    ownerNosBalance: 0,
    ownerSolBalance: 0,
    baseUsdc: 20,
  });
  assert.equal(p.act, true);
  assert.ok(p.topUpSol > 0);
  assert.equal(p.swapNeeded, false);
});

test("caps a single pass so one bad quote cannot move everything", () => {
  const p = planRefill({ subNosBalance: 0, subSolBalance: 0, ownerNosBalance: 0, ownerSolBalance: 0, baseUsdc: 10000 });
  assert.ok(p.bridgeUsd <= 25);
});

test("a plan states its reason whether it acts or not", () => {
  for (const p of [
    planRefill({ subNosBalance: 99, subSolBalance: 1, ownerNosBalance: 0, ownerSolBalance: 0, baseUsdc: 99 }),
    planRefill({ subNosBalance: 0, subSolBalance: 0, ownerNosBalance: 0, ownerSolBalance: 0, baseUsdc: 50 }),
  ]) {
    assert.equal(typeof p.reason, "string");
    assert.ok(p.reason.length > 0);
  }
});

// The exact bug this defect report describes: v1 measured the TREASURY (F5SYUC...) and saw it
// stocked, so it did nothing — while the SUB-WALLET (71FfqF...), the only key that actually pays
// Nosana, sat at 0.0267 NOS, unable to afford even one 10-minute lease (0.0302 NOS). The fix is a
// plan that reads the spender's own balance and, seeing the treasury already holds enough, routes
// straight to a top-up — no bridge, no swap, no wasted fees moving money that's already on-chain.
test("given a stocked treasury and a starving sub-wallet, the plan tops up and does NOT bridge — the S19 routing bug", () => {
  const p = planRefill({
    subNosBalance: 0.0267, // measured: cannot afford a single 10-minute lease (0.0302 NOS)
    subSolBalance: DEFAULT_SUBWALLET_TARGET_SOL, // fine
    ownerNosBalance: 0.8, // stocked treasury can cover the larger safe shelter target
    ownerSolBalance: 1, // plenty
    baseUsdc: 50, // Base has revenue too, but it must not be touched for this
  });
  assert.equal(p.act, true);
  assert.ok(p.topUpNos > 0);
  assert.equal(p.bridgeUsd, 0);
  assert.equal(p.swapNeeded, false);
});

// ---------------------------------------------------------------------------------------------
// executeRefill — bridge -> swap -> top-up, each leg gated on the one before it.
// ---------------------------------------------------------------------------------------------

test("executeRefill runs bridge, then swap, then top-up, in that order, when all three are needed", async () => {
  const calls = [];
  const r = await executeRefill({
    plan: { act: true, bridgeUsd: 5, swapNeeded: true, topUpNos: 0.3, topUpSol: 0.001, reason: "short" },
    bridge: async (usd) => { calls.push(["bridge", usd]); return { ok: true, tx: "0xbridge" }; },
    swapToNos: async () => { calls.push(["swap"]); return { ok: true, tx: "solswap" }; },
    topUpSubWallet: async (amounts) => { calls.push(["topup", amounts]); return { ok: true }; },
  });
  assert.equal(r.ok, true);
  assert.deepEqual(calls.map((c) => c[0]), ["bridge", "swap", "topup"]);
});

test("executeRefill does not swap or top up when the bridge failed — money that never arrived cannot be spent", async () => {
  let swapped = false;
  let toppedUp = false;
  const r = await executeRefill({
    plan: { act: true, bridgeUsd: 5, swapNeeded: true, topUpNos: 0.3, reason: "short" },
    bridge: async () => ({ ok: false, reason: "relay refused" }),
    swapToNos: async () => { swapped = true; return { ok: true }; },
    topUpSubWallet: async () => { toppedUp = true; return { ok: true }; },
  });
  assert.equal(r.ok, false);
  assert.equal(swapped, false);
  assert.equal(toppedUp, false);
});

test("executeRefill does not top up when the swap failed, even though the bridge succeeded", async () => {
  const r = await executeRefill({
    plan: { act: true, bridgeUsd: 5, swapNeeded: true, topUpNos: 0.3, topUpSol: 0.001, reason: "short" },
    bridge: async () => ({ ok: true, tx: "0xbridge" }),
    swapToNos: async () => ({ ok: false, reason: "slippage exceeded" }),
    topUpSubWallet: async () => { throw new Error("must not run"); },
  });
  assert.equal(r.ok, false);
});

test("executeRefill is a no-op for a plan that decided not to act", async () => {
  const r = await executeRefill({
    plan: { act: false, reason: "stocked" },
    bridge: async () => { throw new Error("must not run"); },
    swapToNos: async () => { throw new Error("must not run"); },
    topUpSubWallet: async () => { throw new Error("must not run"); },
  });
  assert.equal(r.ok, true);
  assert.equal(r.skipped, true);
});

test("executeRefill goes straight to top-up when the treasury already covers the shortfall — no bridge, no swap", async () => {
  const calls = [];
  const r = await executeRefill({
    plan: { act: true, bridgeUsd: 0, swapNeeded: false, topUpNos: 0.3, topUpSol: 0, reason: "treasury covers it" },
    bridge: async () => { throw new Error("must not run"); },
    swapToNos: async () => { throw new Error("must not run"); },
    topUpSubWallet: async (amounts) => { calls.push(["topup", amounts]); return { ok: true }; },
  });
  assert.equal(r.ok, true);
  assert.deepEqual(calls.map((c) => c[0]), ["topup"]);
});

test("executeRefill accepts a rail that reports success as `sent` rather than `ok`", async () => {
  // Live 2026-07-27: fundSubWallet returns {sent:true,...}. Reading only `ok` reported a completed
  // 0.473 NOS transfer (tx aYGEcC5k) as a failure.
  const { executeRefill } = await import("../refill.mjs");
  const r = await executeRefill({
    plan: { act: true, bridgeUsd: 0, swapNeeded: false, topUpNos: 0.47, topUpSol: 0, reason: "short" },
    topUpSubWallet: async () => ({ sent: true, signatures: { nos: "sig" } }),
  });
  assert.equal(r.ok, true);
});

test("executeRefill accepts acquireNos settled shape with a signature", async () => {
  const calls = [];
  const r = await executeRefill({
    plan: { act: true, bridgeUsd: 0, swapNeeded: true, topUpNos: 0.25, topUpSol: 0, reason: "short" },
    swapToNos: async () => ({
      posted: true,
      signature: "settled-solana-signature",
      nosReceived: 2.9,
    }),
    topUpSubWallet: async () => {
      calls.push("topup");
      return { sent: true, signatures: { nos: "topup-signature" } };
    },
  });
  assert.equal(r.ok, true);
  assert.deepEqual(calls, ["topup"]);
});

test("executeRefill treats an unknown swap result as indeterminate and never tops up", async () => {
  let toppedUp = false;
  const r = await executeRefill({
    plan: { act: true, bridgeUsd: 0, swapNeeded: true, topUpNos: 0.25, topUpSol: 0, reason: "short" },
    swapToNos: async () => ({ something: "unexpected" }),
    topUpSubWallet: async () => {
      toppedUp = true;
      return { sent: true };
    },
  });
  assert.equal(r.ok, false);
  assert.equal(r.indeterminate, true);
  assert.equal(toppedUp, false);
  assert.match(r.reason, /MAY have gone through/);
});

test("an unreadable top-up result is indeterminate, never a plain failure", async () => {
  // The dangerous case: money may already have moved. Reporting "failed" invites a retry that
  // sends it twice.
  const { executeRefill } = await import("../refill.mjs");
  const r = await executeRefill({
    plan: { act: true, bridgeUsd: 0, swapNeeded: false, topUpNos: 0.47, topUpSol: 0, reason: "short" },
    topUpSubWallet: async () => ({ something: "unexpected" }),
  });
  assert.equal(r.ok, false);
  assert.equal(r.indeterminate, true);
  assert.match(r.reason, /MAY have gone through/);
});

test("a genuine refusal still reports the gate's reason, not 'unknown'", async () => {
  const { executeRefill } = await import("../refill.mjs");
  const r = await executeRefill({
    plan: { act: true, bridgeUsd: 0, swapNeeded: false, topUpNos: 0.47, topUpSol: 0, reason: "short" },
    topUpSubWallet: async () => ({ sent: false, ok: false, gate: { allowed: false, reason: "over the NOS cap" } }),
  });
  assert.equal(r.ok, false);
  assert.equal(r.indeterminate, false);
  assert.match(r.reason, /over the NOS cap/);
});
