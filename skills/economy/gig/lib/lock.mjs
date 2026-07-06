// economy/gig/lib/lock.mjs — per-resource file lock so concurrent calls that mutate the SAME gig (or
// the shared nextId counter, or the shared board file) cannot race past each other. Fixes a real
// double-pay drain an adversary found live: two concurrent gig_verify_and_pay(true) calls both read
// status 'delivered' before either wrote back, both settled a REAL on-chain payout, and the JSON
// ledger only recorded one (last-write-wins) -- the escrow was drained twice for a single gig. This
// lock makes "load -> decide -> network settle -> save" an exclusive critical section per lock key: a
// caller that can't acquire the lock is rejected immediately (fail-closed), never queued -- so at most
// one call ever reaches a real settle.
//
// Implementation: POSIX exclusive file creation (`wx` = O_CREAT|O_EXCL) is atomic even across separate
// OS processes on the same filesystem -- this protects against both same-process (Promise.all) races
// AND two separate `node scripts/...` invocations racing, which is the scenario the adversary actually
// hit (two concurrent verify_and_pay calls, real tx 0xd0af29c3 + 0x6573886b, both paid).
//
// ROUND-3 FIX (a second adversary pass, 2026-07-07): STALE_MS alone let a second caller STEAL a lock
// after 30s even from a holder that was still genuinely (legitimately) working -- a real settle+retry
// sequence measured at 16.79s plus network/confirmation on top can exceed 30s under congestion,
// reopening the double-pay race the lock exists to close. FIX: the holder now HEARTBEATS its own
// lock's mtime every `heartbeatMs` while `fn()` runs, so a LIVE holder's lock never looks stale to
// anyone else -- staleness now only ever indicates a genuinely dead (crashed) holder, never a merely
// slow one. `staleMs`/`heartbeatMs` are injectable (tests use tiny values; production uses generous
// defaults with a wide safety margin between the two).
import { promises as fs } from "node:fs";
import path from "node:path";

const DEFAULT_STALE_MS = 60_000; // must exceed any realistic settle+retry duration by a wide margin
const DEFAULT_HEARTBEAT_MS = 5_000; // refresh well before staleMs could ever be reached by a live holder

function lockPaths(statePath, lockKey) {
  const dir = path.join(path.dirname(statePath), "locks");
  return { dir, file: path.join(dir, `${lockKey}.lock`) };
}

async function acquire(statePath, lockKey, staleMs) {
  const { dir, file } = lockPaths(statePath, lockKey);
  await fs.mkdir(dir, { recursive: true });
  try {
    const handle = await fs.open(file, "wx");
    await handle.close();
    return true;
  } catch (e) {
    if (e.code !== "EEXIST") throw e;
    // Stale-lock recovery: a lock left behind by a CRASHED process must not wedge the board forever.
    // A live holder's heartbeat keeps mtime fresh, so this branch only ever fires for a genuinely dead
    // holder (no heartbeat for staleMs, which is set far past any realistic live-holder gap).
    try {
      const stat = await fs.stat(file);
      if (Date.now() - stat.mtimeMs > staleMs) {
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

async function touch(statePath, lockKey) {
  const { file } = lockPaths(statePath, lockKey);
  const now = new Date();
  // best-effort: if the file is somehow gone (should be practically unreachable given the wide
  // staleMs/heartbeatMs margin below), there's nothing a heartbeat tick can safely do about it.
  await fs.utimes(file, now, now).catch(() => {});
}

/**
 * withGigLock — run `fn()` only if `lockKey` (a gigId, `"_post"` for the shared nextId counter, or
 * `"_board"` for the shared state-file write, see gig.mjs's `applyAndSave`) is not currently locked.
 * If another call already holds the lock, returns a fail-closed rejection WITHOUT ever calling `fn()`
 * -- no queueing, no waiting, no window where two callers can both reach a network settle for the same
 * resource. While `fn()` runs, the lock's mtime is heartbeated so a live holder is never mistaken for
 * a stale one, however long `fn()` legitimately takes.
 */
export async function withGigLock(statePath, lockKey, fn, { staleMs = DEFAULT_STALE_MS, heartbeatMs = DEFAULT_HEARTBEAT_MS } = {}) {
  const got = await acquire(statePath, lockKey, staleMs);
  if (!got) {
    return {
      ok: false,
      reason: `'${lockKey}' is currently being processed by another call -- rejected (fail-closed, prevents a double-settle race)`,
    };
  }
  const heartbeat = setInterval(() => { touch(statePath, lockKey); }, heartbeatMs);
  if (typeof heartbeat.unref === "function") heartbeat.unref(); // don't keep a process alive just for this timer
  try {
    return await fn();
  } finally {
    clearInterval(heartbeat);
    await release(statePath, lockKey);
  }
}
