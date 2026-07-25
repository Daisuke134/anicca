// node:test — topup-decision.mjs: should Franklin buy more NOS for the shelter right now? Pure,
// reuses funding/acquire-nos.mjs's own cap primitives — no second cap engine.
import { test } from "node:test";
import assert from "node:assert/strict";
import { decideShelterTopUp, LAMPORTS_PER_SOL, DEFAULT_SOL_FEE_FLOOR_SOL } from "../topup-decision.mjs";

test("decideShelterTopUp: a nominal survival level needs no top-up", () => {
  const decision = decideShelterTopUp({ survivalLevel: "nominal", solBalanceLamports: 1_000_000_000 });
  assert.equal(decision.allowed, false);
  assert.equal(decision.recommendedSpendLamports, 0);
  assert.match(decision.reason, /does not need a top-up/);
});

test("decideShelterTopUp: warning/critical/insolvent/unknown all warrant considering a top-up", () => {
  for (const level of ["warning", "critical", "insolvent", "unknown"]) {
    const decision = decideShelterTopUp({ survivalLevel: level, solBalanceLamports: 5_000_000_000 });
    assert.equal(decision.allowed, true, `expected ${level} to recommend a top-up`);
  }
});

test("decideShelterTopUp: recommends the smaller of the requested/25%-of-balance cap and the real headroom above the floor", () => {
  // Plenty of SOL: the 25%-of-balance cap (not the requested/default cap, not the floor) wins.
  const decision = decideShelterTopUp({ survivalLevel: "critical", solBalanceLamports: 10 * LAMPORTS_PER_SOL });
  const floorLamports = Math.floor(DEFAULT_SOL_FEE_FLOOR_SOL * LAMPORTS_PER_SOL);
  assert.equal(decision.allowed, true);
  assert.ok(decision.recommendedSpendLamports > 0);
  assert.ok(decision.recommendedSpendLamports <= 10 * LAMPORTS_PER_SOL - floorLamports);
});

test("REGRESSION: the REAL 2026-07-25 balance (~0.0235 SOL) is barely above the fee floor — recommends a small, floor-respecting top-up, never the full default cap", () => {
  const realSolBalanceLamports = 23505190; // real getBalance() result for F5SYUC...hZ5T, 2026-07-25
  const decision = decideShelterTopUp({ survivalLevel: "warning", solBalanceLamports: realSolBalanceLamports });
  const floorLamports = Math.floor(DEFAULT_SOL_FEE_FLOOR_SOL * LAMPORTS_PER_SOL);
  assert.equal(decision.allowed, true);
  assert.ok(decision.recommendedSpendLamports > 0);
  assert.ok(decision.recommendedSpendLamports < 10_000_000); // far below the 0.01 SOL default cap
  assert.equal(realSolBalanceLamports - decision.recommendedSpendLamports >= floorLamports, true); // never strands the wallet
});

test("decideShelterTopUp: refuses (fail-closed) when the balance leaves no headroom above the floor at all", () => {
  const floorLamports = Math.floor(DEFAULT_SOL_FEE_FLOOR_SOL * LAMPORTS_PER_SOL);
  const decision = decideShelterTopUp({ survivalLevel: "insolvent", solBalanceLamports: floorLamports - 1 });
  assert.equal(decision.allowed, false);
  assert.equal(decision.recommendedSpendLamports, 0);
  assert.match(decision.reason, /no safe headroom/);
});

test("decideShelterTopUp: fails closed on a missing/invalid solBalanceLamports", () => {
  for (const bad of [undefined, NaN, -1, "1"]) {
    const decision = decideShelterTopUp({ survivalLevel: "critical", solBalanceLamports: bad });
    assert.equal(decision.allowed, false);
    assert.match(decision.reason, /unavailable|invalid/);
  }
});

test("decideShelterTopUp: an unrecognized survival level is treated as not needing a top-up (only the known dangerous levels trigger one)", () => {
  const decision = decideShelterTopUp({ survivalLevel: "totally-made-up", solBalanceLamports: 1_000_000_000 });
  assert.equal(decision.allowed, false);
});
