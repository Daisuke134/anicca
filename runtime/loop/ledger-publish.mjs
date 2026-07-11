/**
 * ledger-publish.mjs — Effectful (+ small pure core): per-wake, best-effort commit+push of the
 * loop's own ledger.jsonl evidence into the `~/anicca` repo (github.com/Daisuke134/anicca), so
 * "the balance/actions grow every hour" is third-party-verifiable from git history alone.
 *
 * franklin-ledger-push (P2) — spec: .vcsdd/features/franklin-ledger-push/specs/behavioral-spec.md
 * (REQ-701..707). Design source: docs/loop-engineering/20-implementation-certainty-2026-07-11.md §D
 * (anicca-project repo).
 *
 * Idiom copied VERBATIM from skills/earn/lib/evolve.mjs:154-192's own git() helper + path-scoped
 * `git add -- <path>` / `git -c user.name=... -c user.email=... commit -m ... -- <path>` pattern —
 * this file does not invent a new commit style.
 *
 * Pure core (no I/O, directly unit-testable):
 *   - decidePublish()  — REQ-704 push throttle decision.
 *   - extractWakeId()  — parse a ledger line's wake_id for the commit message.
 *
 * Effectful shell:
 *   - readMarker/writeMarker  — throttle/cursor state at $ANICCA_HOME/state/.ledger-publish-marker.
 *   - readSourceLinesRaw/appendRawLines — ledger.jsonl -> state/franklin-ledger/<instance>.jsonl.
 *   - defaultGit — child_process wrapper (injectable via opts.git for tests — never real git in
 *     any test in this package; production wiring in index.mjs uses the real default).
 *   - publishLedgerCycle — the orchestrator; the ONLY function index.mjs calls.
 *
 * REQ-703 (non-fatality) is enforced at TWO layers: every individual git call is wrapped in its own
 * try/catch with a specific `reason`, AND the whole function body is wrapped in an outermost
 * try/catch so publishLedgerCycle() can never throw/reject under any input, ever.
 */

import { promises as fs } from 'node:fs';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { redactPrivateKeyPatterns } from './env-filter.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// REQ-704: 10 new committed lines OR 15 minutes since the last successful push, whichever first.
export const DEFAULT_MIN_LINES = 10;
export const DEFAULT_MIN_INTERVAL_MS = 15 * 60 * 1000;

/**
 * decidePublish(...) — pure REQ-704 throttle decision. No I/O.
 *
 * @param {{pendingLineCount: number, lastPushTs: number, nowMs: number, minLines?: number, minIntervalMs?: number}} args
 * @returns {{shouldPush: boolean, reason: string}}
 */
export function decidePublish({
  pendingLineCount,
  lastPushTs,
  nowMs,
  minLines = DEFAULT_MIN_LINES,
  minIntervalMs = DEFAULT_MIN_INTERVAL_MS,
}) {
  const pending = Number(pendingLineCount) || 0;
  if (pending <= 0) return { shouldPush: false, reason: 'no-pending-lines' };
  if (pending >= minLines) return { shouldPush: true, reason: 'line-threshold' };
  const elapsed = Number(nowMs) - Number(lastPushTs || 0);
  if (elapsed >= minIntervalMs) return { shouldPush: true, reason: 'time-threshold' };
  return { shouldPush: false, reason: 'throttled' };
}

/**
 * extractWakeId(line) — pure. Parses a single ledger.jsonl line and returns its wake_id, or
 * 'unknown' for anything malformed/missing (never throws — REQ-702's commit message must always be
 * constructible).
 *
 * @param {string} line
 * @returns {string}
 */
export function extractWakeId(line) {
  try {
    const parsed = JSON.parse(line);
    return typeof parsed.wake_id === 'string' && parsed.wake_id ? parsed.wake_id : 'unknown';
  } catch {
    return 'unknown';
  }
}

// ── Effectful shell ──────────────────────────────────────────────────────────────────────────────

function defaultGit(args, cwd) {
  return execFileSync('git', args, { cwd, encoding: 'utf8' });
}

const MARKER_DEFAULTS = { copiedLineCount: 0, pendingLinesSincePush: 0, lastPushTs: 0 };

async function readMarker(markerPath) {
  try {
    const raw = await fs.readFile(markerPath, 'utf8');
    const parsed = JSON.parse(raw);
    return {
      copiedLineCount: Number.isInteger(parsed.copiedLineCount) ? parsed.copiedLineCount : 0,
      pendingLinesSincePush: Number.isInteger(parsed.pendingLinesSincePush) ? parsed.pendingLinesSincePush : 0,
      lastPushTs: Number.isFinite(parsed.lastPushTs) ? parsed.lastPushTs : 0,
    };
  } catch {
    return { ...MARKER_DEFAULTS };
  }
}

async function writeMarker(markerPath, marker) {
  await fs.mkdir(path.dirname(markerPath), { recursive: true });
  await fs.writeFile(markerPath, JSON.stringify(marker) + '\n');
}

async function readSourceLinesRaw(ledgerPath) {
  let raw;
  try {
    raw = await fs.readFile(ledgerPath, 'utf8');
  } catch (err) {
    if (err.code === 'ENOENT') return [];
    throw err;
  }
  return raw.split('\n').filter((l) => l.trim().length > 0);
}

async function appendRawLines(destPath, lines) {
  await fs.mkdir(path.dirname(destPath), { recursive: true });
  await fs.appendFile(destPath, lines.map((l) => l + '\n').join(''));
}

/**
 * publishLedgerCycle(opts) — the orchestrator. Called once per completed wake from index.mjs's main
 * loop. NEVER throws (REQ-703) — every failure path returns a `reason` string instead.
 *
 * @param {{
 *   enabled?: boolean,
 *   ledgerPath: string,
 *   destPath?: string,
 *   repoRoot?: string,
 *   instance?: string,
 *   markerPath: string,
 *   git?: (args: string[], cwd: string) => string,
 *   now?: () => number,
 *   log?: (msg: string) => void,
 *   minLines?: number,
 *   minIntervalMs?: number,
 * }} opts
 * @returns {Promise<{published: boolean, pushed: boolean, reason: string}>}
 */
export async function publishLedgerCycle(opts) {
  const {
    enabled = process.env.LEDGER_PUBLISH_ENABLED === '1',
    ledgerPath,
    repoRoot = path.resolve(__dirname, '..', '..'),
    instance = process.env.ANICCA_INSTANCE || 'clawrouter',
    destPath = path.join(repoRoot, 'state', 'franklin-ledger', `${instance}.jsonl`),
    markerPath,
    git = defaultGit,
    now = () => Date.now(),
    log = (msg) => process.stderr.write(msg),
    minLines = DEFAULT_MIN_LINES,
    minIntervalMs = DEFAULT_MIN_INTERVAL_MS,
  } = opts;

  if (!enabled) return { published: false, pushed: false, reason: 'disabled' };

  try {
    const marker = await readMarker(markerPath);
    const sourceLines = await readSourceLinesRaw(ledgerPath);
    const newLines = sourceLines.slice(marker.copiedLineCount);
    const hasWork = newLines.length > 0 || marker.pendingLinesSincePush > 0;
    if (!hasWork) return { published: false, pushed: false, reason: 'no-new-lines' };

    // REQ-705: sync BEFORE any local commit — keeps the branch fast-forward-able for the eventual
    // push. Failure here skips the ENTIRE cycle non-fatally; the next wake retries from scratch.
    try {
      git(['fetch', 'origin', 'main'], repoRoot);
      git(['merge', '--ff-only', 'origin/main'], repoRoot);
    } catch (err) {
      log(`[ledger-publish] sync failed, skipping cycle: ${err.message}\n`);
      return { published: false, pushed: false, reason: 'sync-failed' };
    }

    let copiedLineCount = marker.copiedLineCount;
    let pendingLinesSincePush = marker.pendingLinesSincePush;
    let published = false;

    if (newLines.length > 0) {
      const safeLines = newLines.map((l) => redactPrivateKeyPatterns(l));
      await appendRawLines(destPath, safeLines);
      // REQ-707: persist the advanced cursor BEFORE attempting commit, so a commit failure never
      // causes these same source lines to be read+appended again on the next cycle.
      copiedLineCount += newLines.length;
      await writeMarker(markerPath, { copiedLineCount, pendingLinesSincePush, lastPushTs: marker.lastPushTs });

      try {
        git(['add', '--', destPath], repoRoot);
        const wakeId = extractWakeId(safeLines[safeLines.length - 1]);
        git(
          [
            '-c', 'user.name=Anicca Ledger Publish',
            '-c', 'user.email=ledger-publish@anicca.local',
            'commit', '-m', `ledger(${instance}): wake ${wakeId}`,
            '--', destPath,
          ],
          repoRoot,
        );
        pendingLinesSincePush += newLines.length;
        published = true;
      } catch (err) {
        log(`[ledger-publish] commit failed: ${err.message}\n`);
      }
    }

    const nowMs = now();
    const decision = decidePublish({ pendingLineCount: pendingLinesSincePush, lastPushTs: marker.lastPushTs, nowMs, minLines, minIntervalMs });
    let pushed = false;
    let lastPushTs = marker.lastPushTs;

    if (decision.shouldPush && pendingLinesSincePush > 0) {
      try {
        git(['push', 'origin', 'main'], repoRoot);
        pushed = true;
        lastPushTs = nowMs;
        pendingLinesSincePush = 0;
      } catch (err) {
        log(`[ledger-publish] push skipped: ${err.message}\n`);
      }
    }

    await writeMarker(markerPath, { copiedLineCount, pendingLinesSincePush, lastPushTs });
    return { published, pushed, reason: decision.reason };
  } catch (err) {
    // Outermost safety net (REQ-703): NOTHING escapes this function, ever.
    log(`[ledger-publish] cycle failed unexpectedly: ${err.message}\n`);
    return { published: false, pushed: false, reason: 'error' };
  }
}
