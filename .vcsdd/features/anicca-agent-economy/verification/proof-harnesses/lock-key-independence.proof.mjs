// Proof harness — anicca-agent-economy Phase 5 (formal hardening), sprint 1.
// Property-based test (fast-check) for PROP-101d against the REAL exported withGigLock(...) in
// ~/anicca/skills/economy/gig/lib/lock.mjs.
//
// Tier honesty note (see verification/purity-audit.md for the full discussion): PROP-201d... sorry,
// PROP-101d is labeled Tier 1 in specs/verification-architecture.md ("does not depend on isLockStale at
// all, so remains Tier 1 regardless of the extraction's landing order"), but the ONLY exported surface
// that can observe key-independence is withGigLock() itself -- lockPaths()/acquire() are private,
// unexported helpers. withGigLock() performs real fs.mkdir/fs.open/fs.stat/fs.rename, which the same
// document's own Tier definitions classify as Tier 2 ("real fs ... concurrent Promise.all calls").
// This harness does not paper over that mismatch: it runs the property against real temp-directory fs
// state (genuinely Tier 2), while still satisfying the SPIRIT of PROP-101d (randomized-input coverage
// beyond the 4 hardcoded literal key names "keyA".."keyD" already in lock.test.mjs) that this Phase 5
// pass was asked to add. The tier-label mismatch itself is recorded in purity-audit.md, not hidden here.
//
// Run: node --test .vcsdd/features/anicca-agent-economy/verification/proof-harnesses/lock-key-independence.proof.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import fc from "fast-check";
import { promises as fsp } from "node:fs";
import os from "node:os";
import path from "node:path";
import { withGigLock } from "/Users/anicca/anicca/skills/economy/gig/lib/lock.mjs";

test("PROP-101d (fast-check): two DIFFERENT lock keys never contend, across randomized key-name pairs", async () => {
  await fc.assert(
    fc.asyncProperty(
      fc.stringMatching(/^[A-Za-z0-9_-]{1,24}$/),
      fc.stringMatching(/^[A-Za-z0-9_-]{1,24}$/),
      async (keyA, keyB) => {
        fc.pre(keyA !== keyB);
        const dir = await fsp.mkdtemp(path.join(os.tmpdir(), "lock-proof-"));
        const statePath = path.join(dir, "gigs.json");
        try {
          const [a, b] = await Promise.all([
            withGigLock(statePath, keyA, async () => ({ ok: true }), { staleMs: 200, heartbeatMs: 40 }),
            withGigLock(statePath, keyB, async () => ({ ok: true }), { staleMs: 200, heartbeatMs: 40 }),
          ]);
          assert.equal(a.ok, true, `key "${keyA}" must succeed independent of "${keyB}"`);
          assert.equal(b.ok, true, `key "${keyB}" must succeed independent of "${keyA}"`);
        } finally {
          await fsp.rm(dir, { recursive: true, force: true });
        }
      }
    ),
    { numRuns: 30 } // real fs I/O per run -- deliberately smaller than the pure-function harnesses
  );
});
