// spawn-funding-swap effectful shell — REQ-005, REQ-010. createLedgerStore({stateDir}): the on-disk
// idempotency ledger (REQ-005 resumability) AND the canonical destination-address-keyed lock (REQ-010),
// backed by the SAME statePath. REUSES the existing, already-adversary-hardened `withGigLock`
// (economy/gig/lib/lock.mjs, unmodified — REQ-010's own binding instruction) under the destination
// Akash address as the lock key, exactly mirroring skills/self/spawn/lib/spawn-orchestrator.mjs's own
// reuse pattern ("colony-spawn" lock key) for a different feature's mutual exclusion.
import { promises as fs } from "node:fs";
import path from "node:path";
import { withGigLock } from "../../../economy/gig/lib/lock.mjs";

// serializeState/deserializeState — the ledger's persisted state routinely carries bigint fields (leg
// nonces, quoteSnapshot.amountOutUakt) that JSON.stringify/JSON.parse cannot handle natively. This
// marker-object round-trip (NOT a lossy Number coercion) preserves bigint values exactly across the
// disk write/read cycle.
const BIGINT_MARKER_KEY = "__spawnFundingSwapBigInt__";

function jsonReplacer(_key, value) {
  return typeof value === "bigint" ? { [BIGINT_MARKER_KEY]: value.toString() } : value;
}

function jsonReviver(_key, value) {
  if (value && typeof value === "object" && typeof value[BIGINT_MARKER_KEY] === "string") {
    return BigInt(value[BIGINT_MARKER_KEY]);
  }
  return value;
}

function stateFilePath(stateDir, destinationAddress) {
  return path.join(stateDir, `${destinationAddress}.json`);
}

/**
 * createLedgerStore — REQ-005/REQ-010: the effectful ledger read/write + canonical lock primitive.
 * @param {{stateDir: string}} params
 */
export function createLedgerStore({ stateDir }) {
  const statePath = path.join(stateDir, "ledger-state.json"); // withGigLock only uses this for its dirname (locks/ subdir); the file itself need not exist.

  return {
    /**
     * withLock — REQ-010: atomically acquires the canonical lock keyed by `destinationAddress` (NOT by
     * any Skip route/quote id) and runs `fn()` inside it. Returns `{ok:false, reason}` immediately,
     * WITHOUT ever calling `fn()`, when the lock is already held by an incomplete prior operation.
     * Returns `{ok:true, result: <fn's return value>}` when `fn()` actually ran — matching
     * lib/__tests__/fakes/fake-clients.mjs's `createFakeLedgerStore.withLock` contract exactly (driver.mjs
     * relies on this uniform shape regardless of which ledgerStore implementation is injected).
     * `withGigLock` itself returns `fn()`'s value UNWRAPPED on success (only its own pre-`fn()`
     * lock-rejection path returns `{ok:false, reason}`) — `fnWasCalled` disambiguates the two cases
     * without any shape-sniffing of `fn()`'s own return value (which could otherwise collide with
     * `{ok:false, reason}` coincidentally).
     */
    async withLock(destinationAddress, fn) {
      await fs.mkdir(stateDir, { recursive: true });
      let fnWasCalled = false;
      const outcome = await withGigLock(statePath, destinationAddress, async () => {
        fnWasCalled = true;
        return fn();
      });
      if (!fnWasCalled) return outcome; // withGigLock's own {ok:false, reason} lock-rejection shape.
      return { ok: true, result: outcome };
    },

    /** readState — REQ-005: reads the destination's persisted ledger state, or null if never written. */
    async readState(destinationAddress) {
      try {
        const raw = await fs.readFile(stateFilePath(stateDir, destinationAddress), "utf8");
        return JSON.parse(raw, jsonReviver);
      } catch (err) {
        if (err && err.code === "ENOENT") return null;
        throw err;
      }
    },

    /** writeState — REQ-005/PROP-020: durably persists the destination's ledger state. */
    async writeState(destinationAddress, state) {
      await fs.mkdir(stateDir, { recursive: true });
      const serialized = JSON.stringify(state, jsonReplacer, 2);
      await fs.writeFile(stateFilePath(stateDir, destinationAddress), serialized, "utf8");
    },
  };
}
