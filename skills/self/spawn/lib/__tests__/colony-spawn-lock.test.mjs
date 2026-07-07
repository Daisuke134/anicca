// VCSDD anicca-agent-spawn, Phase 2a (RED). REQ-103 — cross-instance spawn mutual exclusion.
// Reuses the EXISTING, already-adversary-hardened `withGigLock` (economy/gig/lib/lock.mjs,
// unmodified) under a NEW lock key, "colony-spawn", with `statePath` set to the exported
// `CITIZENS_REGISTRY_PATH` constant (registry-path.mjs — does not exist yet). This whole file is
// expected to fail at import time (module-not-found) until registry-path.mjs is implemented.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { withGigLock } from "../../../../economy/gig/lib/lock.mjs";
import { CITIZENS_REGISTRY_PATH } from "../registry-path.mjs";

test("PROP-103a/PROP-103d: two concurrent colony-spawn lock attempts on the SAME CITIZENS_REGISTRY_PATH statePath -> exactly one proceeds past wallet generation", async () => {
  fs.mkdirSync(path.dirname(CITIZENS_REGISTRY_PATH), { recursive: true });
  let walletGenCalls = 0;
  const attempt = () =>
    withGigLock(CITIZENS_REGISTRY_PATH, "colony-spawn", async () => {
      walletGenCalls += 1;
      await new Promise((r) => setTimeout(r, 20));
      return { ok: true };
    });
  const [r1, r2] = await Promise.all([attempt(), attempt()]);
  const results = [r1, r2];
  assert.equal(results.filter((r) => r.ok).length, 1);
  const lost = results.find((r) => !r.ok);
  assert.match(lost.reason, /currently being processed/);
  assert.equal(walletGenCalls, 1, "wallet-generation step must be invoked exactly once");
});

test("PROP-103e (staggered race, resolves FIND-1201): the lock remains held across a delayed REQ-304 funding step — a second caller's repeated attempts ALL fail until REQ-305's append (the lock release) actually completes", async () => {
  fs.mkdirSync(path.dirname(CITIZENS_REGISTRY_PATH), { recursive: true });
  let releaseFundingDelay;
  const fundingDelay = new Promise((resolve) => {
    releaseFundingDelay = resolve;
  });
  // Deterministic hand-off (fixes a real ~1-in-5 flake): `withGigLock`'s own `acquire()` does
  // async fs I/O (mkdir + O_EXCL open) scheduled on the libuv threadpool, so firing `firstCaller`
  // below WITHOUT awaiting anything gives no guarantee its lock-file create wins the race against
  // the loop's first attempt just a few lines later -- both calls' fs.open("wx") can be scheduled
  // in either order. `fn()` only ever runs once `acquire()` has resolved `true` (the lock file
  // genuinely exists), so signaling from inside `fn()` -- and awaiting that signal before the loop
  // starts -- proves the lock is held on disk, with zero dependency on thread-pool scheduling order.
  let signalLockHeld;
  const lockHeld = new Promise((resolve) => {
    signalLockHeld = resolve;
  });

  const firstCaller = withGigLock(CITIZENS_REGISTRY_PATH, "colony-spawn", async () => {
    // Simulates REQ-201-205 (wallet gen, identity registration, mcp config) already completed;
    // REQ-304's funding call is still in flight.
    signalLockHeld();
    await fundingDelay;
    // REQ-305's ledger append "completes" here — the lock releases only on return.
    return { ok: true, stage: "ledger-appended" };
  });
  await lockHeld;

  for (let i = 0; i < 5; i++) {
    const attempt = await withGigLock(CITIZENS_REGISTRY_PATH, "colony-spawn", async () => ({ ok: true }));
    assert.equal(attempt.ok, false, `attempt ${i} while REQ-304 funding is still pending must fail`);
    await new Promise((r) => setTimeout(r, 5));
  }

  releaseFundingDelay();
  const firstResult = await firstCaller;
  assert.equal(firstResult.ok, true);

  const afterRelease = await withGigLock(CITIZENS_REGISTRY_PATH, "colony-spawn", async () => ({ ok: true }));
  assert.equal(afterRelease.ok, true, "the lock must be acquirable again only AFTER REQ-305's append actually completed");
});
