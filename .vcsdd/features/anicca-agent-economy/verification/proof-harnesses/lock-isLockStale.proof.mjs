// Proof harness — anicca-agent-economy Phase 5 (formal hardening), sprint 1.
// Property-based tests (fast-check) for PROP-101a / PROP-101b against the REAL exported
// isLockStale(nowMs, mtimeMs, staleMs) predicate in ~/anicca/skills/economy/gig/lib/lock.mjs.
//
// Why this harness exists: the existing handwritten Tier-1 unit tests
// (skills/economy/gig/__tests__/lock.test.mjs) only exercise a small number of FIXED fixture points
// (staleMs=100 with mtime deltas of 0/50/100/101/1100, and a single heartbeatMs=20/staleMs=100/50-tick
// heartbeat simulation). This harness generates thousands of RANDOM (nowMs, mtimeMs, staleMs) triples
// and randomized heartbeat-interval/staleMs/tick-count combinations to prove the two properties hold
// across the input space, not just the sampled points a human happened to write down.
//
// Run: node --test .vcsdd/features/anicca-agent-economy/verification/proof-harnesses/lock-isLockStale.proof.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import fc from "fast-check";
import { isLockStale } from "/Users/anicca/anicca/skills/economy/gig/lib/lock.mjs";

// PROP-101b (generalized): isLockStale's boundary is EXACTLY "> staleMs", for ANY non-negative
// nowMs/mtimeMs/staleMs triple, not just the 5 fixed fixture points in lock.test.mjs.
test("PROP-101b (fast-check): isLockStale(nowMs, mtimeMs, staleMs) === (nowMs - mtimeMs > staleMs) for all non-negative integer triples", () => {
  fc.assert(
    fc.property(
      fc.integer({ min: 0, max: 10_000_000 }),
      fc.integer({ min: 0, max: 10_000_000 }),
      fc.integer({ min: 0, max: 10_000_000 }),
      (nowMs, mtimeMs, staleMs) => {
        const expected = nowMs - mtimeMs > staleMs;
        assert.equal(isLockStale(nowMs, mtimeMs, staleMs), expected);
      }
    ),
    { numRuns: 5000 }
  );
});

// PROP-101b, boundary-focused: specifically hammer values within a few ms of the staleMs boundary,
// where an off-by-one (>= vs >) bug would most likely hide and a coarse random sample might miss.
test("PROP-101b (fast-check, boundary-focused): values within +/-3ms of the staleMs boundary are classified correctly", () => {
  fc.assert(
    fc.property(
      fc.integer({ min: 0, max: 1_000_000 }), // staleMs
      fc.integer({ min: 0, max: 1_000_000 }), // base offset, keeps mtimeMs >= 0 below
      fc.integer({ min: -3, max: 3 }), // offset around the boundary
      (staleMs, baseNow, offset) => {
        const nowMs = baseNow + staleMs + 1000; // comfortably ahead so mtimeMs below never goes negative
        const mtimeMs = nowMs - staleMs + offset;
        const delta = nowMs - mtimeMs; // == staleMs - offset
        const expected = delta > staleMs;
        assert.equal(isLockStale(nowMs, mtimeMs, staleMs), expected, `staleMs=${staleMs} offset=${offset} delta=${delta}`);
      }
    ),
    { numRuns: 2000 }
  );
});

// PROP-101a (generalized): for ANY staleMs > 0 and ANY heartbeatMs strictly less than staleMs, and ANY
// number of heartbeat ticks (1..200), a lock whose mtime is refreshed every heartbeatMs is NEVER flagged
// stale -- however large the TOTAL elapsed time grows. The handwritten test only exercises
// staleMs=100/heartbeatMs=20/ticks=50; this harness randomizes all three independently, thousands of times.
test("PROP-101a (fast-check): a heartbeat-refreshed lock (heartbeatMs < staleMs) is never stale across randomized tick counts", () => {
  fc.assert(
    fc.property(
      fc.integer({ min: 2, max: 100_000 }), // staleMs
      fc.integer({ min: 1, max: 99 }), // heartbeatMs expressed as a percentage of staleMs -> guarantees heartbeatMs < staleMs
      fc.integer({ min: 1, max: 200 }), // number of heartbeat ticks to simulate
      (staleMs, heartbeatPct, ticks) => {
        const heartbeatMs = Math.max(1, Math.floor((staleMs * heartbeatPct) / 100));
        fc.pre(heartbeatMs < staleMs); // discard the rare rounding case where heartbeatMs === staleMs
        let mtimeMs = 0;
        let nowMs = 0;
        for (let t = 0; t < ticks; t++) {
          nowMs += heartbeatMs;
          assert.equal(
            isLockStale(nowMs, mtimeMs, staleMs),
            false,
            `staleMs=${staleMs} heartbeatMs=${heartbeatMs} tick=${t}: heartbeat-refreshed lock must never be stale`
          );
          mtimeMs = nowMs;
        }
      }
    ),
    { numRuns: 1000 }
  );
});

// Negative control: once heartbeats stop (holder crashed) and enough time passes, isLockStale MUST
// eventually return true. This guards against a vacuously-true "never stale" property -- e.g. a buggy
// isLockStale that always returns false would wrongly pass the property above forever; this test proves
// the predicate is not degenerate.
test("PROP-101a/b (fast-check, negative control): once heartbeats stop, isLockStale eventually becomes true after staleMs elapses", () => {
  fc.assert(
    fc.property(
      fc.integer({ min: 2, max: 100_000 }),
      fc.integer({ min: 1, max: 5000 }),
      (staleMs, extra) => {
        const mtimeMs = 0;
        const nowMs = staleMs + extra; // strictly past the boundary
        assert.equal(isLockStale(nowMs, mtimeMs, staleMs), true);
      }
    ),
    { numRuns: 500 }
  );
});
