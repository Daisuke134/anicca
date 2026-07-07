// node:test — lib/lock.mjs tests (round-3 adversary GAP 1: stale-lock steal from a live holder).
//
// anicca-agent-economy REQ-101 (Phase 2a, RED): `isLockStale(nowMs, mtimeMs, staleMs) -> boolean` is a
// BINDING acceptance criterion -- the staleness comparison currently inlined in lib/lock.mjs's acquire()
// (`Date.now() - stat.mtimeMs > staleMs`) must be extracted into an independently exported, pure function.
// As of this Phase 2a commit, lib/lock.mjs does NOT export `isLockStale` yet -- the import below is
// EXPECTED TO FAIL at module-load time (Node ESM: "does not provide an export named 'isLockStale'"),
// which fails EVERY test in this file (including the 3 pre-existing ones above this comment), not just
// the new ones below. This is the intended RED-phase signal for REQ-101/PROP-101a/b/c/d -- Phase 2b must
// land the extraction (lib/lock.mjs exports isLockStale; acquire() calls it instead of re-implementing
// the comparison inline) before this file can load and any test in it can pass again.
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { withGigLock, isLockStale, isSafeLockKey } from "../lib/lock.mjs";

async function tmpStatePath() {
  const d = await fs.mkdtemp(path.join(os.tmpdir(), "lock-test-"));
  return path.join(d, "gigs.json");
}

test("★GAP 1★ a live holder's lock is NEVER stolen while it's still working past staleMs (heartbeat keeps it alive)", async () => {
  const statePath = await tmpStatePath();
  const events = [];
  const staleMs = 100;
  const heartbeatMs = 20;

  // the holder runs for 3x staleMs -- well past the point a non-heartbeated lock would look stale.
  const holderPromise = withGigLock(
    statePath,
    "g1",
    async () => {
      await new Promise((r) => setTimeout(r, staleMs * 3));
      events.push("holder-ran");
      return { ok: true, who: "holder" };
    },
    { staleMs, heartbeatMs }
  );

  // give the holder time to acquire, then wait until staleMs has ALREADY elapsed once, while it's
  // still running -- this is exactly the window a non-heartbeated lock would be stealable in.
  await new Promise((r) => setTimeout(r, staleMs + 30));
  const usurper = await withGigLock(
    statePath,
    "g1",
    async () => {
      events.push("usurper-ran");
      return { ok: true, who: "usurper" };
    },
    { staleMs, heartbeatMs }
  );

  const holderResult = await holderPromise;

  assert.equal(usurper.ok, false, "the usurper must be rejected -- the holder is still alive, not stale");
  assert.match(usurper.reason, /currently being processed/);
  assert.equal(holderResult.ok, true, "the real holder must still complete normally");
  assert.deepEqual(events, ["holder-ran"], "the usurper's fn must NEVER run concurrently with the holder's");
});

test("a GENUINELY dead holder's lock (crashed, no heartbeat) IS reclaimable after staleMs", async () => {
  const statePath = await tmpStatePath();
  const lockDir = path.join(path.dirname(statePath), "locks");
  await fs.mkdir(lockDir, { recursive: true });
  const lockFile = path.join(lockDir, "g2.lock");
  await fs.writeFile(lockFile, ""); // simulate an orphaned lock file (holder crashed, no heartbeat ever ran)
  const old = new Date(Date.now() - 5_000);
  await fs.utimes(lockFile, old, old);

  const result = await withGigLock(statePath, "g2", async () => ({ ok: true, ran: true }), { staleMs: 100, heartbeatMs: 20 });
  assert.equal(result.ok, true, "a lock that is genuinely stale (no heartbeat, past staleMs) must still be reclaimable");
  assert.equal(result.ran, true);
});

test("two calls with DIFFERENT lock keys never contend with each other", async () => {
  const statePath = await tmpStatePath();
  const [a, b] = await Promise.all([
    withGigLock(statePath, "keyA", async () => ({ ok: true, who: "a" }), { staleMs: 100, heartbeatMs: 20 }),
    withGigLock(statePath, "keyB", async () => ({ ok: true, who: "b" }), { staleMs: 100, heartbeatMs: 20 }),
  ]);
  assert.equal(a.ok, true);
  assert.equal(b.ok, true);
});

// ============================================================================
// anicca-agent-economy REQ-101 — Tier 1 unit tests directly against the exported,
// pure `isLockStale(nowMs, mtimeMs, staleMs) -> boolean` predicate (Phase 2a RED,
// see the file-header comment above: these fail at IMPORT time until Phase 2b
// extracts isLockStale out of acquire()'s inline comparison).
// ============================================================================

// PROP-101b: boundary behaviour of the staleness comparison itself.
// Mirrors the CURRENT inline comparison in acquire(): `Date.now() - stat.mtimeMs > staleMs`
// (strictly greater than -- exactly staleMs elapsed is NOT yet stale).
test("PROP-101b: isLockStale boundary -- exactly staleMs elapsed is NOT stale, 1ms past IS stale", () => {
  const staleMs = 100;
  assert.equal(isLockStale(1000, 900, staleMs), false, "exactly staleMs elapsed (delta=100) must NOT be stale (boundary is exclusive)");
  assert.equal(isLockStale(1001, 900, staleMs), true, "1ms past the boundary (delta=101) MUST be stale");
  assert.equal(isLockStale(2000, 900, staleMs), true, "well past the boundary (delta=1100) MUST be stale");
  assert.equal(isLockStale(1000, 950, staleMs), false, "well within the window (delta=50) must NOT be stale");
  assert.equal(isLockStale(1000, 1000, staleMs), false, "delta=0 (just created) must NOT be stale");
});

// PROP-101a: a lock whose holder heartbeats at interval H is NEVER stale, however long the TOTAL
// elapsed time grows -- staleness is a function of the delta since the LAST heartbeat refresh, not
// of total wall-clock time since the lock was first created.
test("PROP-101a: isLockStale never flags a heartbeat-refreshed lock as stale, however long total elapsed time grows", () => {
  const staleMs = 100;
  const heartbeatMs = 20; // heartbeatMs << staleMs, matches lib/lock.mjs's own DEFAULT_STALE_MS/DEFAULT_HEARTBEAT_MS safety-margin relationship
  let mtimeMs = 0;
  let nowMs = 0;
  for (let tick = 0; tick < 50; tick++) {
    nowMs += heartbeatMs;
    assert.equal(
      isLockStale(nowMs, mtimeMs, staleMs),
      false,
      `tick ${tick}: heartbeat-refreshed lock must not be stale (nowMs=${nowMs}, mtimeMs=${mtimeMs}, delta=${nowMs - mtimeMs})`
    );
    mtimeMs = nowMs; // simulate touch()'s heartbeat refresh landing exactly on schedule
  }
  assert.ok(
    nowMs > staleMs * 5,
    `sanity: total elapsed time (${nowMs}ms) must exceed staleMs (${staleMs}ms) many times over -- proves the predicate tracks the DELTA since last heartbeat, not total elapsed time`
  );
});

// PROP-101c: isLockStale itself is a pure, side-effect-free, deterministic predicate (no I/O, no
// randomness) -- calling it twice with identical inputs must yield identical output. The REAL
// atomic-reclaim guarantee ("no window where two callers both believe they hold the same key") is a
// property of acquire()'s `fs.open(file, "wx")` primitive, not of this pure predicate, so it is
// verified separately below (Tier 2, real fs, concurrent withGigLock calls against a real backdated
// stale lock file) rather than by isLockStale in isolation.
test("PROP-101c (purity half): isLockStale is deterministic and side-effect-free -- same inputs always yield the same boolean", () => {
  const a1 = isLockStale(5000, 100, 200);
  const a2 = isLockStale(5000, 100, 200);
  assert.equal(a1, a2);
  assert.equal(typeof a1, "boolean");
  const b1 = isLockStale(5000, 4900, 200);
  const b2 = isLockStale(5000, 4900, 200);
  assert.equal(b1, b2);
  assert.equal(typeof b1, "boolean");
});

// PROP-101c (atomicity half, Tier 2): two callers that BOTH observe the SAME backdated-stale lock file
// and BOTH attempt to reclaim it concurrently -- exactly ONE must win the reclaim (acquire()'s
// stat-then-unlink-then-open sequence must not leave a window where a second racer's unlink can delete
// the FIRST racer's freshly-recreated lock file, letting both racers' fs.open("wx") calls each succeed
// in turn). This is a genuine race condition test, not an import-time-only failure -- it exercises the
// real `withGigLock`/`acquire()` code path against a real fs, same as the two pre-existing tests above.
test("★PROP-101c (Tier 2, atomicity)★ two concurrent stale-lock reclaim attempts on the SAME lock key -- exactly ONE must win, never both", async () => {
  const statePath = await tmpStatePath();
  const lockDir = path.join(path.dirname(statePath), "locks");
  await fs.mkdir(lockDir, { recursive: true });
  const lockFile = path.join(lockDir, "g3.lock");
  await fs.writeFile(lockFile, ""); // orphaned lock file, as if its holder crashed
  const old = new Date(Date.now() - 5_000);
  await fs.utimes(lockFile, old, old);

  const ran = [];
  const [a, b] = await Promise.all([
    withGigLock(statePath, "g3", async () => { ran.push("a"); return { ok: true, who: "a" }; }, { staleMs: 100, heartbeatMs: 20 }),
    withGigLock(statePath, "g3", async () => { ran.push("b"); return { ok: true, who: "b" }; }, { staleMs: 100, heartbeatMs: 20 }),
  ]);

  const winners = [a, b].filter((r) => r.ok);
  assert.equal(winners.length, 1, `exactly ONE of the two concurrent stale-lock reclaim attempts must succeed -- got ${winners.length} (${JSON.stringify([a, b])})`);
  assert.equal(ran.length, 1, `fn() must run for exactly ONE racer, never both -- ran: ${JSON.stringify(ran)}`);
});

// PROP-101d: two DIFFERENT lock keys never contend, even under the stale-reclaim path -- this does not
// depend on isLockStale's extraction landing (it's about `acquire()`'s per-key file scoping), so it
// remains valid Tier 1 coverage regardless of extraction order. (The pre-existing "two calls with
// DIFFERENT lock keys never contend with each other" test above already covers the fast/happy path;
// this one additionally backdates BOTH lock files into the stale-reclaim branch to confirm independence
// holds there too.)
test("PROP-101d: two different lock keys, BOTH in the stale-reclaim branch, never contend with each other", async () => {
  const statePath = await tmpStatePath();
  const lockDir = path.join(path.dirname(statePath), "locks");
  await fs.mkdir(lockDir, { recursive: true });
  const old = new Date(Date.now() - 5_000);
  for (const key of ["keyC", "keyD"]) {
    const f = path.join(lockDir, `${key}.lock`);
    await fs.writeFile(f, "");
    await fs.utimes(f, old, old);
  }
  const [a, b] = await Promise.all([
    withGigLock(statePath, "keyC", async () => ({ ok: true, who: "c" }), { staleMs: 100, heartbeatMs: 20 }),
    withGigLock(statePath, "keyD", async () => ({ ok: true, who: "d" }), { staleMs: 100, heartbeatMs: 20 }),
  ]);
  assert.equal(a.ok, true, "keyC's reclaim must succeed independent of keyD");
  assert.equal(b.ok, true, "keyD's reclaim must succeed independent of keyC");
});

// ============================================================================
// SEC-1 (Phase 5 security-report.md): path traversal via unsanitized lockKey. A caller-supplied gigId
// used to flow straight into lockPaths()'s `${lockKey}.lock` filename interpolation with no character
// restriction -- `path.join` collapses "../" segments, so a crafted gigId could make the lock file land
// OUTSIDE the intended <statePath-dir>/locks/ directory (live-verified PoC, see security-report.md).
// mcp-server.mjs's zod schema is the PRIMARY fix (constrains gigId before it reaches here); these tests
// cover the SECOND, independent layer inside lib/lock.mjs itself, which protects any direct caller of
// withGigLock (bypassing the MCP schema entirely, e.g. a Node script importing gig.mjs directly).
// ============================================================================

test("SEC-1: isSafeLockKey rejects a path-traversal lock key, accepts every real lock key shape", () => {
  assert.equal(
    isSafeLockKey("../../../../../../../../../../tmp/anicca-poc-escaped-file-live"),
    false,
    "a traversal sequence must be rejected"
  );
  assert.equal(isSafeLockKey("../etc/passwd"), false, "any '../' segment must be rejected");
  assert.equal(isSafeLockKey("a/b"), false, "an embedded path separator must be rejected");
  assert.equal(isSafeLockKey("/etc/passwd"), false, "an absolute path must be rejected");
  assert.equal(isSafeLockKey(""), false, "an empty string must be rejected");
  assert.equal(isSafeLockKey(null), false, "a non-string (null) must be rejected");
  assert.equal(isSafeLockKey(undefined), false, "a non-string (undefined) must be rejected");
  assert.equal(isSafeLockKey(42), false, "a non-string (number) must be rejected");

  // every real lock key this module actually uses in production must remain accepted:
  assert.equal(isSafeLockKey("1"), true, "a real gigId (String(state.nextId)) must be accepted");
  assert.equal(isSafeLockKey("42"), true, "a real multi-digit gigId must be accepted");
  assert.equal(isSafeLockKey("_post"), true, "the internal POST_LOCK_KEY must be accepted");
  assert.equal(isSafeLockKey("_board"), true, "the internal BOARD_LOCK_KEY must be accepted");
  assert.equal(isSafeLockKey("g1"), true, "an alphanumeric test-style key must be accepted");
});

test("★SEC-1★ withGigLock REJECTS a path-traversal lock key fail-closed -- fn() never runs, no file is created outside locks/", async () => {
  const statePath = await tmpStatePath();
  const escapedTarget = path.join(os.tmpdir(), `anicca-sec1-test-escape-${process.pid}`);
  await fs.rm(escapedTarget, { force: true }).catch(() => {});

  let fnRan = false;
  const maliciousGigId = "../../../../../../../../../../tmp/anicca-poc-escaped-file-live";
  const result = await withGigLock(statePath, maliciousGigId, async () => {
    fnRan = true;
    return { ok: true };
  });

  assert.equal(result.ok, false, "an unsafe lock key must be rejected, not silently accepted");
  assert.match(result.reason, /unsafe lock key/, "the rejection reason must name the SEC-1 guard");
  assert.equal(fnRan, false, "fn() must NEVER run for an unsafe lock key -- no queueing, no partial execution");

  const escapedExists = await fs.stat(path.join(os.tmpdir(), "anicca-poc-escaped-file-live")).then(() => true).catch(() => false);
  assert.equal(escapedExists, false, "no lock file may ever be created outside the intended locks/ directory");

  const lockDirExists = await fs.stat(path.join(path.dirname(statePath), "locks")).then(() => true).catch(() => false);
  assert.equal(lockDirExists, false, "an unsafe key must be rejected before even the locks/ directory is created");
});

test("SEC-1: withGigLock still works normally for a real numeric gigId lock key (no regression)", async () => {
  const statePath = await tmpStatePath();
  const result = await withGigLock(statePath, "7", async () => ({ ok: true, ran: true }));
  assert.equal(result.ok, true, "a normal numeric gigId lock key must continue to work exactly as before");
  assert.equal(result.ran, true);
});
