/**
 * go-live.mjs — Effectful: the one-time REQ-512 go-live operational action.
 *
 * behavioral-spec.md REQ-512: "the one-time operational action that flips REQ-501(b)'s flag to '1'
 * ... SHALL itself append a ledger line with kind:'always_act_go_live' (ts, and the config source it
 * was set from) at the moment of that flip." behavioral-spec.md sec6 item 10 names this a "separate,
 * explicit, logged operational action" — run manually by the operator exactly once when Franklin's
 * live ALWAYS_ACT_ENABLED config flag is actually flipped, deliberately OUT of the wake loop's own
 * control flow (index.mjs never imports or calls this module — no wake, engaged or otherwise, ever
 * writes this ledger line itself; PROP-509-style structural check in
 * __tests__/go-live.test.mjs::"never wired into any wake" confirms this).
 *
 * This is the "recordGoLive()-style function ... invoked manually by the operator's own one-time
 * command" spec-review iteration-2 notes.md observation #2 recommended, and Phase 3 iteration-1
 * FIND-002 flagged as missing: `buildGoLiveRecord`/`shouldRecordGoLive` (always-act-router.mjs, pure
 * planning) + this module's `recordGoLive` (the effectful shell append, reusing the SAME
 * appendLedgerLine/formatRecord machinery every other ledger write in this codebase uses — no new
 * writer primitive).
 */

import path from 'node:path';
import { appendLedgerLine, readLedgerLines } from './ledger.mjs';
import { formatRecord } from './ledger-record.mjs';
import { buildGoLiveRecord, shouldRecordGoLive } from './always-act-router.mjs';

/**
 * recordGoLive — reads the existing ledger tail and, iff no `always_act_go_live` line already exists
 * (shouldRecordGoLive), appends one. Returns `true` iff a line was actually appended; `false` means
 * one was already recorded — a safe no-op (REQ-512's "exactly once at the flip" contract), never a
 * duplicate anchor line.
 *
 * @param {{ledgerPath: string, configSource: string, now?: () => string}} opts
 * @returns {Promise<boolean>}
 */
export async function recordGoLive({ ledgerPath, configSource, now = () => new Date().toISOString() }) {
  const tail = await readLedgerLines(ledgerPath);
  if (!shouldRecordGoLive(tail)) return false;
  const record = buildGoLiveRecord({ ts: now(), configSource });
  await appendLedgerLine(ledgerPath, formatRecord(record));
  return true;
}

// CLI entry point — the operator's own one-time command (behavioral-spec.md sec6 item 10), run AFTER
// vcsdd-converge, at the exact moment ALWAYS_ACT_ENABLED is flipped to "1" in Franklin's live config.
// Usage: ANICCA_HOME=/path/to/home node runtime/loop/go-live.mjs <configSource>
if (import.meta.url === `file://${process.argv[1]}`) {
  const aniccaHome = process.env.ANICCA_HOME;
  if (!aniccaHome) {
    process.stderr.write('[go-live] FATAL: ANICCA_HOME is not set.\n');
    process.exit(1);
  }
  const configSource = process.argv[2] || 'unspecified';
  const ledgerPath = path.join(aniccaHome, 'state', 'ledger.jsonl');
  const wrote = await recordGoLive({ ledgerPath, configSource });
  process.stdout.write(
    wrote
      ? `[go-live] recorded kind:'always_act_go_live' (config_source=${configSource})\n`
      : "[go-live] an always_act_go_live line already exists -- no-op (idempotent, REQ-512's exactly-once contract)\n",
  );
}
