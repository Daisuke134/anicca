import { test } from "node:test";
import assert from "node:assert/strict";
import {
  evaluateRenewal,
  DEFAULT_NOS_MOVE_OUT_RESERVE,
  DEFAULT_SOL_FEE_FLOOR,
  DEFAULT_NOS_PER_EXTEND,
} from "../renew.mjs";

// A job that is running and about to expire — i.e. one that SHOULD renew if money allows.
const DUE = { state: 1, timeStart: 1000, timeout: 600 };
const NOW = 1000 + 600 - 60; // 60s left, inside the 180s margin

const RICH = { nosBalance: 5, solBalance: 0.05 };

test("renews when the lease is nearly up and there is money behind it", () => {
  const r = evaluateRenewal({ job: DUE, nowTs: NOW, ...RICH });
  assert.equal(r.renew, true);
});

test("stops renewing while it can still afford to move house, not after", () => {
  // Enough for this extension, but paying for it would eat into the move-out reserve.
  const nosBalance = DEFAULT_NOS_MOVE_OUT_RESERVE + DEFAULT_NOS_PER_EXTEND / 2;
  const r = evaluateRenewal({ job: DUE, nowTs: NOW, nosBalance, solBalance: 0.05 });
  assert.equal(r.renew, false);
  assert.match(r.reason, /move/i);
});

test("the reserve is what makes this different from a time ceiling: same job, same clock, money decides", () => {
  const broke = evaluateRenewal({ job: DUE, nowTs: NOW, nosBalance: 0.05, solBalance: 0.05 });
  const rich = evaluateRenewal({ job: DUE, nowTs: NOW, ...RICH });
  assert.equal(broke.renew, false);
  assert.equal(rich.renew, true);
});

test("refuses when SOL can no longer pay transaction fees", () => {
  const r = evaluateRenewal({ job: DUE, nowTs: NOW, nosBalance: 5, solBalance: DEFAULT_SOL_FEE_FLOOR / 2 });
  assert.equal(r.renew, false);
  assert.match(r.reason, /SOL/);
});

test("reproduces the live drain: 0.894 NOS extends a while, then stops with a reserve intact", () => {
  // Live 2026-07-27: job AzUFmVa5 went 600s -> 19800s and left 0.027 NOS, which could not buy
  // even one more 10-minute lease. With a floor, the same run must stop holding the reserve.
  let nos = 0.894;
  let timeout = 600;
  let extensions = 0;
  for (let i = 0; i < 200; i++) {
    const job = { state: 1, timeStart: 1000, timeout };
    const r = evaluateRenewal({ job, nowTs: 1000 + timeout - 60, nosBalance: nos, solBalance: 0.05 });
    if (!r.renew) break;
    nos -= DEFAULT_NOS_PER_EXTEND;
    timeout += 600;
    extensions++;
  }
  assert.ok(extensions > 0, "it should still renew while it is solvent");
  assert.ok(nos >= DEFAULT_NOS_MOVE_OUT_RESERVE, `left ${nos} NOS, below the ${DEFAULT_NOS_MOVE_OUT_RESERVE} reserve`);
  assert.ok(timeout < 19800, `ran to ${timeout}s — the floor did not bite before the live run's ceiling`);
});

test("the time ceiling still applies independently of money", () => {
  const job = { state: 1, timeStart: 1000, timeout: 6 * 60 * 60 };
  const r = evaluateRenewal({ job, nowTs: 1000 + 6 * 60 * 60 - 60, ...RICH });
  assert.equal(r.renew, false);
  assert.match(r.reason, /ceiling/);
});

test("balances left unspecified do not silently disable the floor", () => {
  const r = evaluateRenewal({ job: DUE, nowTs: NOW });
  assert.equal(r.renew, false);
  assert.match(r.reason, /balance/i);
});

test("a job that is not running is never renewed regardless of balance", () => {
  const r = evaluateRenewal({ job: { state: 2, timeStart: 1000, timeout: 600 }, nowTs: NOW, ...RICH });
  assert.equal(r.renew, false);
});
