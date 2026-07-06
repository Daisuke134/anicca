// node:test — lib/lock.mjs tests (round-3 adversary GAP 1: stale-lock steal from a live holder).
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { withGigLock } from "../lib/lock.mjs";

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
