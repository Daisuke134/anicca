// resolve-swap-state-dir.mjs — spawn-funding-swap's own STATE_DIR resolution (REQ-008 "self-contained
// config" fix, Phase-3 impl-review FIND-002: bin/spawn-funding-swap.mjs previously read
// `process.env.SPAWN_FUNDING_SWAP_STATE_DIR` with NO default at all -- unlike its THRESHOLD_AKT/
// LEG_TIMEOUT_MS siblings on the same two lines -- so an unset env var meant `createLedgerStore({stateDir:
// undefined})` would hit `path.join(undefined, "ledger-state.json")` (lib/ledger-store.mjs:37) and throw a
// raw, untested `TypeError [ERR_INVALID_ARG_TYPE]` the instant identity resolved in production. Caught
// only by main().catch() (fails closed on money-safety, but not intentionally), and REQ-008's own edge
// case requires the command to depend on nothing beyond akt-treasury.sh's exports plus "its own
// self-contained config" -- an undefaulted required env var is not self-contained.
//
// Fix direction (Option A): default to a "spawn-funding-swap" subdirectory of the SAME durable,
// /tmp-rejecting state-dir convention already reused colony-wide within skills/self/spawn/ for
// children.jsonl (spawn-orchestrator.mjs), citizens.json (registry-path.mjs), and
// shelter-cost.jsonl/children.jsonl (wake-gate.mjs) -- resolveStateDir() from
// skills/self/spawn/lib/state-path.js. This is the SAME sibling skill directory
// (skills/self/spawn-funding-swap/ next to skills/self/spawn/), so reusing rather than inventing a new
// convention (per repo-wide "never reinvent the wheel" policy). resolveStateDir() itself already
// fail-closes (throws) rather than ever returning a /tmp-rooted or otherwise unsafe path, so this function
// either returns a concrete, non-empty string or throws an explicit error -- it NEVER returns `undefined`
// for a downstream `path.join(undefined, ...)` to explode on.
//
// SPAWN_FUNDING_SWAP_STATE_DIR remains a supported explicit override (unchanged behavior for anyone who
// already sets it) -- this only closes the previously-undefaulted case.
import path from "node:path";
import { resolveStateDir } from "../../spawn/lib/state-path.js";

/**
 * resolveSwapStateDir — the directory spawn-funding-swap's REQ-005/REQ-010 ledger+lock file lives under.
 * Priority: `SPAWN_FUNDING_SWAP_STATE_DIR` (explicit override, if set to a non-empty string) > a
 * "spawn-funding-swap" subdirectory of `resolveStateDir()`'s own colony-wide durable-state default.
 * @param {{env?: Record<string, string>}} [opts] env: environment map to read from; defaults to
 *   process.env (mainly a test seam, mirrors resolve-swap-identity.mjs's own injectable-env shape).
 * @returns {string} a concrete, non-empty state directory path — never `undefined`.
 */
export function resolveSwapStateDir({ env } = {}) {
  const e = env || process.env;
  if (typeof e.SPAWN_FUNDING_SWAP_STATE_DIR === "string" && e.SPAWN_FUNDING_SWAP_STATE_DIR.length > 0) {
    return e.SPAWN_FUNDING_SWAP_STATE_DIR;
  }
  return path.join(resolveStateDir({ env: e }), "spawn-funding-swap");
}
