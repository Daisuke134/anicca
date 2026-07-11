/**
 * ledger-publish.mjs — Effectful (+ pure core): per-wake, best-effort commit+push of the loop's
 * own ledger.jsonl evidence into github.com/Daisuke134/anicca, so "the balance/actions grow every
 * hour" is third-party-verifiable from git history alone -- WITHOUT ever touching the git working
 * tree/index/branches the loop itself (or a sibling process such as evolve.mjs's promote()) is
 * concurrently using.
 *
 * franklin-ledger-push (P2) — spec: .vcsdd/features/franklin-ledger-push/specs/behavioral-spec.md
 * (REQ-701..710). iter1 redesign (this file): a fresh-context adversary found the previous
 * `git push origin main` design unscoped against a SHARED checkout also written to by evolve.mjs's
 * promote() and concurrently by other same-host instances (FIND-001/002/005). This version
 * publishes into a DEDICATED, per-instance orphan branch of a DEDICATED clone
 * ($ANICCA_HOME/state/.ledger-publish-repo) that this feature owns exclusively -- the shared
 * checkout (`repoRoot`) is used ONLY to read `git remote get-url origin` (a read-only config
 * lookup), never written to, in this file or any test of it (FIND-001/002 killed structurally,
 * not just guarded).
 *
 * Pure core (no I/O, directly unit-testable):
 *   - decidePublish()             — REQ-704 push throttle decision.
 *   - extractWakeId()             — parse a ledger line's wake_id for the commit message.
 *   - projectLedgerLine()         — REQ-706b field-allowlist projection (FIND-003): parses one raw
 *     ledger.jsonl line and returns ONLY an explicit allowlist of known-safe fields, type-checked;
 *     every other field (including the model-authored free-form `args` object) is DROPPED,
 *     fail-closed. `result`/`skip_reason` free-text fields are additionally redacted (see below)
 *     and capped at 200 chars. Malformed/non-object JSON -> null (dropped entirely, never published
 *     as raw garbage).
 *   - redactBroaderSecretPatterns() — a second, STRICTER redaction pass applied only to the
 *     free-text fields projectLedgerLine() allows through (`result`/`skip_reason`), on top of the
 *     existing `redactPrivateKeyPatterns` -- covers base58 64-88 char runs (Solana secret-key
 *     shape) and generic 40+ hex char runs (a stricter bar than env-filter.mjs's own 64-hex-only
 *     contract, deliberately: content bound for a PUBLIC git branch gets a higher redaction floor
 *     than content that only ever stays in a local ledger.jsonl).
 *   - Reused: redactPrivateKeyPatterns (env-filter.mjs, unmodified).
 *
 * Effectful shell:
 *   - readMarker/writeMarker      — throttle/cursor state at $ANICCA_HOME/state/.ledger-publish-marker.
 *   - readSourceLinesRaw/appendRawLines — ledger.jsonl -> <publishRepoDir>/<instance>.jsonl.
 *   - acquireLock/releaseLock     — REQ-709 same-instance-overlap guard: an mkdir-atomic lock at
 *     $ANICCA_HOME/state/.ledger-publish-<instance>.lock with pid-staleness reclaim, copied from
 *     this repo's own established idiom (skills/self/claude-p-mainloop.sh's pidfile guard +
 *     scripts/disk-cleaner.sh's mkdir-atomic lock — macOS has no flock(1), both those scripts
 *     already solve this the same way).
 *   - ensurePublishRepo           — REQ-708 (FIND-001/002): idempotently sets up the DEDICATED
 *     clone at `publishRepoDir`, checked out to (or freshly orphan-creating) `ledger-<instance>`,
 *     tracking `origin/ledger-<instance>` when it already exists. Every git call in this function
 *     runs with cwd=publishRepoDir -- repoRoot is passed nowhere near it.
 *   - recoverFromDivergence       — REQ-710 (FIND-005): on a rejected (non-fast-forward) push,
 *     fetch + hard-reset the publish repo's branch to origin, then RE-PROJECT every source line
 *     from `marker.pushedLineCount` (the only cursor that means "confirmed on origin") through the
 *     current end of ledger.jsonl, recommit, and retry the push once. Never derives from
 *     `copiedLineCount` (a merely-local, possibly-just-discarded cursor) -- so a line already
 *     locally committed but never pushed is re-derived from source, never silently dropped.
 *   - defaultGit                  — child_process wrapper (injectable via opts.git for tests).
 *   - publishLedgerCycle          — the orchestrator; the ONLY function index.mjs calls.
 *
 * REQ-703 (non-fatality) is enforced at multiple layers: every individual git call is wrapped in
 * its own try/catch with a specific `reason`, the lock is released in a `finally`, and the whole
 * function body is wrapped in an outermost try/catch so publishLedgerCycle() can never throw/reject
 * under any input, ever.
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

// ── FIND-003: field-allowlist projection (pure) ─────────────────────────────────────────────────

// Matches self-eval.mjs's OWN real earn-ledger field-naming convention (net_usdc/cost_usdc/earn_usdc)
// generalised to any net_*/earn_*/cost_* numeric field this or a future ledger line may carry.
const NUMERIC_STAT_FIELD = /^(net|earn|cost)_[A-Za-z0-9]+$/;
// Matches evolve.mjs's own earn-ledger `tx` field convention (a tx hash), plus tx_hash/txHash spellings.
const TX_HASH_FIELD = /^tx([_-]?hash)?$/i;
const TX_HASH_VALUE = /^0x[0-9a-fA-F]{6,64}$/;

// Base58 (Bitcoin/Solana alphabet — excludes 0/O/I/l) run of 64-88 chars: the shape of a Solana
// base58-encoded secret key. A generic 40+ hex run: a stricter bar than env-filter.mjs's 64-hex-
// only PRIVKEY_PATTERN, deliberately, since this text is bound for a PUBLIC git branch.
const BASE58_SECRET_RUN = /[1-9A-HJ-NP-Za-km-z]{64,88}/g;
const HEX_40PLUS_RUN = /(0x)?[0-9a-fA-F]{40,}/g;

/**
 * redactBroaderSecretPatterns(str) — pure. Second, stricter redaction pass for free-text fields
 * only (result/skip_reason), applied ON TOP OF redactPrivateKeyPatterns.
 *
 * @param {string} str
 * @returns {string}
 */
export function redactBroaderSecretPatterns(str) {
  if (typeof str !== 'string') return String(str ?? '');
  return str.replace(BASE58_SECRET_RUN, '[REDACTED]').replace(HEX_40PLUS_RUN, '[REDACTED]');
}

function redactFreeText(value) {
  if (typeof value !== 'string') return undefined;
  const passOne = redactPrivateKeyPatterns(value);
  const passTwo = redactBroaderSecretPatterns(passOne);
  return passTwo.slice(0, 200);
}

function isFiniteNumber(v) {
  return typeof v === 'number' && Number.isFinite(v);
}

function projectField(key, value) {
  switch (key) {
    case 'ts': return isFiniteNumber(value) ? value : undefined;
    case 'wake_id': return typeof value === 'string' ? value : undefined;
    case 'kind': return typeof value === 'string' ? value : undefined;
    case 'slot': return typeof value === 'string' || value === null ? value : undefined;
    case 'attemptsUsed': return isFiniteNumber(value) ? value : undefined;
    case 'profitable': return typeof value === 'boolean' ? value : undefined;
    case 'exit_code': return isFiniteNumber(value) || value === null ? value : undefined;
    case 'sleep_s': return isFiniteNumber(value) ? value : undefined;
    case 'model': return typeof value === 'string' ? value : undefined;
    case 'result': return redactFreeText(value);
    case 'skip_reason': return redactFreeText(value);
    default:
      if (NUMERIC_STAT_FIELD.test(key)) return isFiniteNumber(value) ? value : undefined;
      if (TX_HASH_FIELD.test(key)) return typeof value === 'string' && TX_HASH_VALUE.test(value) ? value : undefined;
      return undefined; // fail-closed: every other field (incl. the model-authored `args` object) is DROPPED.
  }
}

/**
 * projectLedgerLine(rawLine) — pure. Parses one raw ledger.jsonl line and returns a JSON string
 * (no trailing newline) containing ONLY the explicit field allowlist above, or `null` if the line
 * isn't parseable JSON / isn't a plain object (dropped entirely — never published as raw text).
 *
 * @param {string} rawLine
 * @returns {string|null}
 */
export function projectLedgerLine(rawLine) {
  let parsed;
  try {
    parsed = JSON.parse(rawLine);
  } catch {
    return null;
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null;
  const out = {};
  for (const [key, value] of Object.entries(parsed)) {
    const projected = projectField(key, value);
    if (projected !== undefined) out[key] = projected;
  }
  return JSON.stringify(out);
}

// ── Effectful shell ──────────────────────────────────────────────────────────────────────────────

function defaultGit(args, cwd) {
  return execFileSync('git', args, { cwd, encoding: 'utf8' });
}

const MARKER_DEFAULTS = { copiedLineCount: 0, pushedLineCount: 0, pendingLinesSincePush: 0, lastPushTs: 0 };

async function readMarker(markerPath) {
  try {
    const raw = await fs.readFile(markerPath, 'utf8');
    const parsed = JSON.parse(raw);
    return {
      copiedLineCount: Number.isInteger(parsed.copiedLineCount) ? parsed.copiedLineCount : 0,
      pushedLineCount: Number.isInteger(parsed.pushedLineCount) ? parsed.pushedLineCount : 0,
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
  if (lines.length === 0) return;
  await fs.mkdir(path.dirname(destPath), { recursive: true });
  await fs.appendFile(destPath, lines.map((l) => l + '\n').join(''));
}

async function pathExists(p) {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

async function ensureReadme(readmePath, instance) {
  if (await pathExists(readmePath)) return false;
  const content =
    `# Anicca ledger-publish — ${instance}\n\n` +
    `Append-only, field-allowlisted projection of this instance's ledger.jsonl. Machine-generated ` +
    `by \`runtime/loop/ledger-publish.mjs\` (feature: franklin-ledger-push). Unknown fields are ` +
    `dropped before publish; free-text fields are redacted. This branch is dedicated to instance ` +
    `\`${instance}\` only — see github.com/Daisuke134/anicca.\n`;
  await fs.mkdir(path.dirname(readmePath), { recursive: true });
  await fs.writeFile(readmePath, content);
  return true;
}

// ── FIND-009/010 (same-instance overlap guard): mkdir-atomic lock with pid-staleness reclaim ────
// Copied idiom from skills/self/claude-p-mainloop.sh (pidfile) + scripts/disk-cleaner.sh (mkdir
// atomic lock) — macOS has no flock(1) binary, both those scripts already solve this the same way.

function isProcessAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

async function acquireLock(lockDir) {
  try {
    await fs.mkdir(lockDir);
  } catch (err) {
    if (err.code !== 'EEXIST') throw err;
    let stale = false;
    try {
      const pidRaw = await fs.readFile(path.join(lockDir, 'pid'), 'utf8');
      const pid = Number(pidRaw.trim());
      stale = !Number.isInteger(pid) || !isProcessAlive(pid);
    } catch {
      stale = true; // no readable pid file — treat as a stale/crashed lock, safe to reclaim.
    }
    if (!stale) return false; // a live process genuinely holds the lock — caller must skip this cycle.
    await fs.rm(lockDir, { recursive: true, force: true });
    await fs.mkdir(lockDir);
  }
  await fs.writeFile(path.join(lockDir, 'pid'), String(process.pid));
  return true;
}

async function releaseLock(lockDir) {
  try {
    await fs.rm(lockDir, { recursive: true, force: true });
  } catch {
    // best-effort — a failed unlock is not fatal (next cycle's staleness check reclaims it).
  }
}

// ── FIND-001/002 (dedicated per-instance orphan publish branch) ─────────────────────────────────

/**
 * ensurePublishRepo(...) — idempotently sets up the DEDICATED clone at `publishRepoDir`, on branch
 * `ledger-<instance>`. Every git call here runs with cwd=publishRepoDir; `repoRoot`/the shared
 * checkout is NEVER passed to this function or touched by it.
 */
async function ensurePublishRepo({ publishRepoDir, originUrl, branch, git }) {
  const gitMetaDir = path.join(publishRepoDir, '.git');
  if (!(await pathExists(gitMetaDir))) {
    await fs.mkdir(path.dirname(publishRepoDir), { recursive: true });
    git(['clone', '--no-checkout', '--quiet', originUrl, publishRepoDir]);
  }
  let remoteBranchExists = true;
  try {
    git(['fetch', '--quiet', 'origin', branch], publishRepoDir);
  } catch {
    remoteBranchExists = false;
  }
  if (remoteBranchExists) {
    git(['checkout', '-B', branch, `origin/${branch}`], publishRepoDir);
  } else {
    try {
      git(['checkout', '--orphan', branch], publishRepoDir);
    } catch {
      // Already sitting on an unborn `branch` from a previous partial run — fine, continue.
    }
  }
}

/**
 * recoverFromDivergence(...) — REQ-710 (FIND-005): on a rejected push, fetch + hard-reset the
 * publish repo's branch to origin, then RE-PROJECT every source line from `pushedLineCount` (the
 * only cursor that means "confirmed on origin") through the end of `sourceLines`, recommit, and
 * retry the push once. Throws on failure (caller treats that as an ordinary best-effort push miss —
 * the next cycle retries the same recovery from the same safe `pushedLineCount` cursor).
 */
async function recoverFromDivergence({ publishRepoDir, branch, git, sourceLines, pushedLineCount, instance, destPath, readmePath }) {
  git(['fetch', '--quiet', 'origin', branch], publishRepoDir);
  git(['reset', '--quiet', '--hard', `origin/${branch}`], publishRepoDir);

  const toReproject = sourceLines.slice(pushedLineCount);
  let copiedLineCount = pushedLineCount;
  let pendingLinesSincePush = 0;

  if (toReproject.length > 0) {
    const projected = toReproject.map(projectLedgerLine).filter((l) => l !== null);
    await appendRawLines(destPath, projected);
    copiedLineCount = pushedLineCount + toReproject.length;

    const readmeCreated = await ensureReadme(readmePath, instance);
    const relDest = `${instance}.jsonl`;
    const addArgs = readmeCreated ? ['add', '--', relDest, 'README.md'] : ['add', '--', relDest];
    git(addArgs, publishRepoDir);
    const wakeId = extractWakeId(toReproject[toReproject.length - 1]);
    git(
      [
        '-c', 'user.name=Anicca Ledger Publish',
        '-c', 'user.email=ledger-publish@anicca.local',
        'commit', '-m', `ledger(${instance}): recovery wake ${wakeId}`,
        '--', relDest, ...(readmeCreated ? ['README.md'] : []),
      ],
      publishRepoDir,
    );
    pendingLinesSincePush = toReproject.length;
  }

  git(['push', 'origin', branch], publishRepoDir);
  return { copiedLineCount, pendingLinesSincePush, pushed: true, pushedLineCount: copiedLineCount };
}

/**
 * publishLedgerCycle(opts) — the orchestrator. Called once per completed wake from index.mjs's main
 * loop. NEVER throws (REQ-703) — every failure path returns a `reason` string instead.
 *
 * @param {{
 *   enabled?: boolean,
 *   ledgerPath: string,
 *   markerPath: string,
 *   instance?: string,
 *   repoRoot?: string,             // the SHARED checkout — used ONLY to read `git remote get-url origin`.
 *   publishRepoDir?: string,       // DEDICATED clone, default $ANICCA_HOME/state/.ledger-publish-repo.
 *   lockDir?: string,              // default $ANICCA_HOME/state/.ledger-publish-<instance>.lock.
 *   originUrl?: string,            // injectable (tests point this at a file:// bare-repo fixture).
 *   git?: (args: string[], cwd?: string) => string,
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
    markerPath,
    publishRepoDir = path.join(path.dirname(markerPath), '.ledger-publish-repo'),
    lockDir = path.join(path.dirname(markerPath), `.ledger-publish-${instance}.lock`),
    originUrl,
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

    const gotLock = await acquireLock(lockDir);
    if (!gotLock) return { published: false, pushed: false, reason: 'locked' };

    try {
      const branch = `ledger-${instance}`;
      const destPath = path.join(publishRepoDir, `${instance}.jsonl`);
      const readmePath = path.join(publishRepoDir, 'README.md');

      let resolvedOriginUrl = originUrl;
      let copiedLineCount = marker.copiedLineCount;
      let pendingLinesSincePush = marker.pendingLinesSincePush;
      let pushedLineCount = marker.pushedLineCount;
      let published = false;

      try {
        if (!resolvedOriginUrl) resolvedOriginUrl = git(['remote', 'get-url', 'origin'], repoRoot).trim();
        await ensurePublishRepo({ publishRepoDir, originUrl: resolvedOriginUrl, branch, git });
      } catch (err) {
        log(`[ledger-publish] publish-repo setup failed, skipping cycle: ${err.message}\n`);
        return { published: false, pushed: false, reason: 'setup-failed' };
      }

      if (newLines.length > 0) {
        const projected = newLines.map(projectLedgerLine).filter((l) => l !== null);
        await appendRawLines(destPath, projected);
        copiedLineCount += newLines.length;
        // REQ-707: persist the advanced cursor BEFORE attempting commit, so a commit failure never
        // causes these same source lines to be read+appended again on the next cycle.
        await writeMarker(markerPath, { copiedLineCount, pushedLineCount, pendingLinesSincePush, lastPushTs: marker.lastPushTs });

        try {
          const readmeCreated = await ensureReadme(readmePath, instance);
          const relDest = `${instance}.jsonl`;
          const addArgs = readmeCreated ? ['add', '--', relDest, 'README.md'] : ['add', '--', relDest];
          git(addArgs, publishRepoDir);
          const wakeId = extractWakeId(newLines[newLines.length - 1]);
          git(
            [
              '-c', 'user.name=Anicca Ledger Publish',
              '-c', 'user.email=ledger-publish@anicca.local',
              'commit', '-m', `ledger(${instance}): wake ${wakeId}`,
              '--', relDest, ...(readmeCreated ? ['README.md'] : []),
            ],
            publishRepoDir,
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
          git(['push', 'origin', branch], publishRepoDir);
          pushed = true;
          lastPushTs = nowMs;
          pushedLineCount = copiedLineCount;
          pendingLinesSincePush = 0;
        } catch (pushErr) {
          log(`[ledger-publish] push rejected, attempting divergence recovery: ${pushErr.message}\n`);
          try {
            const recovered = await recoverFromDivergence({
              publishRepoDir, branch, git, sourceLines, pushedLineCount, instance, destPath, readmePath,
            });
            copiedLineCount = recovered.copiedLineCount;
            pendingLinesSincePush = recovered.pendingLinesSincePush;
            pushedLineCount = recovered.pushedLineCount;
            pushed = true;
            lastPushTs = nowMs;
          } catch (recoverErr) {
            // Best-effort: local `copiedLineCount`/`pendingLinesSincePush` are already correct
            // (advanced during the append step above) and independent of the publish repo's actual
            // git state, which is fully rebuildable next cycle from `pushedLineCount` alone — no
            // line is ever silently dropped, it is simply retried on the next wake.
            log(`[ledger-publish] divergence recovery failed, will retry next cycle: ${recoverErr.message}\n`);
          }
        }
      }

      await writeMarker(markerPath, { copiedLineCount, pushedLineCount, pendingLinesSincePush, lastPushTs });
      return { published, pushed, reason: decision.reason };
    } finally {
      await releaseLock(lockDir);
    }
  } catch (err) {
    // Outermost safety net (REQ-703): NOTHING escapes this function, ever.
    log(`[ledger-publish] cycle failed unexpectedly: ${err.message}\n`);
    return { published: false, pushed: false, reason: 'error' };
  }
}
