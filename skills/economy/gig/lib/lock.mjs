// economy/gig/lib/lock.mjs — per-resource file lock so concurrent calls that mutate the SAME gig (or
// the shared nextId counter) cannot race past each other. Fixes a real double-pay drain an adversary
// found live: two concurrent gig_verify_and_pay(true) calls both read status 'delivered' before either
// wrote back, both settled a REAL on-chain payout, and the JSON ledger only recorded one (last-write-
// wins) -- the escrow was drained twice for a single gig. This lock makes "load -> decide -> network
// settle -> save" an exclusive critical section per lock key: a caller that can't acquire the lock is
// rejected immediately (fail-closed), never queued -- so at most one call ever reaches a real payout.
//
// Implementation: POSIX exclusive file creation (`wx` = O_CREAT|O_EXCL) is atomic even across separate
// OS processes on the same filesystem -- this protects against both same-process (Promise.all) races
// AND two separate `node scripts/...` invocations racing, which is the scenario the adversary actually
// hit (two concurrent verify_and_pay calls, real tx 0xd0af29c3 + 0x6573886b, both paid).
import { promises as fs } from "node:fs";
import path from "node:path";

const STALE_MS = 30_000; // a lock older than this is assumed to be from a crashed process, not a live race

function lockPaths(statePath, lockKey) {
  const dir = path.join(path.dirname(statePath), "locks");
  return { dir, file: path.join(dir, `${lockKey}.lock`) };
}

async function acquire(statePath, lockKey) {
  const { dir, file } = lockPaths(statePath, lockKey);
  await fs.mkdir(dir, { recursive: true });
  try {
    const handle = await fs.open(file, "wx");
    await handle.close();
    return true;
  } catch (e) {
    if (e.code !== "EEXIST") throw e;
    // Stale-lock recovery: a lock left behind by a crashed process must not wedge the board forever.
    try {
      const stat = await fs.stat(file);
      if (Date.now() - stat.mtimeMs > STALE_MS) {
        await fs.unlink(file).catch(() => {});
        const handle = await fs.open(file, "wx");
        await handle.close();
        return true;
      }
    } catch {
      // lost the race to another process clearing/recreating it -- fall through to "locked"
    }
    return false;
  }
}

async function release(statePath, lockKey) {
  const { file } = lockPaths(statePath, lockKey);
  await fs.unlink(file).catch(() => {});
}

/**
 * withGigLock — run `fn()` only if `lockKey` (a gigId, or a fixed key like "_post" for the shared
 * nextId counter) is not currently locked. If another call already holds the lock, returns a
 * fail-closed rejection WITHOUT ever calling `fn()` -- no queueing, no waiting, no window where two
 * callers can both reach a network settle for the same resource.
 */
export async function withGigLock(statePath, lockKey, fn) {
  const got = await acquire(statePath, lockKey);
  if (!got) {
    return {
      ok: false,
      reason: `'${lockKey}' is currently being processed by another call -- rejected (fail-closed, prevents a double-settle race)`,
    };
  }
  try {
    return await fn();
  } finally {
    await release(statePath, lockKey);
  }
}
