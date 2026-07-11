# Behavioral Spec — franklin-ledger-push (P2: per-wake ledger auto commit+push)

Mode: **lean**. Source: `docs/loop-engineering/20-implementation-certainty-2026-07-11.md` §D
(anicca-project repo) — "P2 per-wake git push — 認証は生きている、push コードだけ無い". Goal: every
Franklin wake's ledger evidence becomes third-party-verifiable from `github.com/Daisuke134/anicca`
git history alone, without making the wake loop dependent on git/network succeeding.

## Changelog

- **impl-review iter1 redesign: FIND-001..005.** A fresh-context adversary (impl-review iteration 1)
  found the original design's `git push origin main` unscoped against a checkout SHARED with
  `evolve.mjs`'s live-wired `promote()` and with other same-host Anicca instances (FIND-001/002 —
  blocking), the "verified every `safeAppend` call site" claim about copying raw ledger lines
  factually false relative to the actual `args`-containing schema (FIND-003), zero test coverage of
  the push-scope/divergence hazards (FIND-004), and no divergence-recovery story at all (FIND-005).
  This revision replaces REQ-702/705/706/707 and adds REQ-708/709 to kill all five structurally: a
  DEDICATED per-instance orphan publish clone (never the shared checkout), an explicit field
  allowlist (never a raw copy), a push-confirmed cursor (`pushedLineCount`) with fetch+hard-reset+
  reproject recovery on divergence, and a same-instance mkdir-atomic lock.

## Purity Boundary Analysis

- **Pure core**: `decidePublish()` (batch/throttle decision — line-count OR time-elapsed),
  `extractWakeId()` (parse a JSON ledger line, pull `wake_id`), `projectLedgerLine()` (REQ-702's
  field-allowlist projection — parses one raw ledger.jsonl line and returns only known-safe,
  type-checked fields; every other field, including the model-authored `args` object, is dropped),
  `redactBroaderSecretPatterns()` (REQ-706's second, stricter redaction pass for free-text fields),
  and reuse of the existing pure `redactPrivateKeyPatterns()` (`env-filter.mjs`, unmodified). No
  I/O, deterministic, directly unit-testable.
- **Effectful shell**: `readMarker`/`writeMarker` (fs, cursor state at
  `$ANICCA_HOME/state/.ledger-publish-marker`), `readSourceLinesRaw`/`appendRawLines` (fs, source
  `ledger.jsonl` → `<publishRepoDir>/<instance>.jsonl`), `acquireLock`/`releaseLock` (REQ-708,
  mkdir-atomic same-instance-overlap guard), `ensurePublishRepo` (REQ-705, sets up the DEDICATED
  clone + orphan/tracking branch), `recoverFromDivergence` (REQ-709), `defaultGit` (child_process
  `execFileSync`, injectable), and the orchestrator `publishLedgerCycle()` which sequences all of
  the above. Wired into `index.mjs`'s main wake loop (`while (!shuttingDown) { await runOneWake();
  ... }`) — never inside `runOneWake()` itself, so it never affects any of `runOneWake`'s own return
  paths.

## Requirements

### REQ-701: Default OFF
**EARS**: WHEN `LEDGER_PUBLISH_ENABLED` is unset, empty, or any value other than the literal string
`"1"` THE SYSTEM SHALL perform zero git operations and zero filesystem writes related to ledger
publishing (mirrors `ALWAYS_ACT_ENABLED`'s own fail-closed gating style, `index.mjs:282-286`).
**Edge Cases**:
- `LEDGER_PUBLISH_ENABLED="true"` / `"yes"` / `"0"`: treated as disabled (only literal `"1"` enables).
- Flag flips mid-session: resolved fresh on every call (never cached), so a flip takes effect on the
  very next wake.
**Acceptance Criteria**:
- `publishLedgerCycle({ enabled: false, ... })` returns `{ published: false, pushed: false, reason:
  'disabled' }` without touching the injected `git` function or the filesystem.

### REQ-702: Field-allowlist copy + path-scoped local commit into the DEDICATED publish repo
**EARS**: WHEN `LEDGER_PUBLISH_ENABLED="1"` AND the source `ledger.jsonl` has lines not yet copied
THE SYSTEM SHALL project each new line through the explicit field allowlist (`projectLedgerLine()`
— FIND-003) and append the projected lines to `<publishRepoDir>/<ANICCA_INSTANCE>.jsonl` (inside
the DEDICATED clone, REQ-705 — never inside the shared checkout), committing ONLY that path (+ the
one-time `README.md`), copying `evolve.mjs:154-192`'s idiom: `git add -- <path>`, then
`git -c user.name=... -c user.email=... commit -m "ledger(<instance>): wake <wake_id>" -- <path>`.
**Field allowlist** (every other field is DROPPED, fail-closed — this is structural parsing of a
fixed machine format, never judgment): `ts`, `wake_id`, `kind`, `slot`, `attemptsUsed`,
`profitable`, `exit_code`, `sleep_s`, `model`, any `net_*`/`earn_*`/`cost_*` numeric field (matches
`self-eval.mjs`'s own `net_usdc`/`cost_usdc`/`earn_usdc` convention), any `tx`/`tx_hash`/`txHash`
field whose value matches a hash shape (`0x[0-9a-fA-F]{6,64}`), and `result`/`skip_reason` (passed
through REQ-706's two-layer redaction, capped at 200 chars). The model-authored `args` object is
NEVER published (not in the allowlist).
**Edge Cases**:
- `publishRepoDir` does not exist yet: created via REQ-705's `ensurePublishRepo`.
- `ANICCA_INSTANCE` unset: falls back to `"clawrouter"` (matches `anicca-daemon.sh:28`'s own default).
- Zero new source lines: no append, no commit attempted this cycle (`reason: 'no-new-lines'` when
  there is also no push-pending backlog).
- A source line that is malformed JSON or not a plain object: `projectLedgerLine()` returns `null`
  and that line is silently excluded from the destination file (the SOURCE-line cursor still
  advances past it — no index desync, just nothing published for it).
**Acceptance Criteria**:
- After a cycle with N new source lines, the destination file's line count is at most N (fewer if
  any malformed) and each written line's content is a strict subset of the allowlisted fields.
- The commit message matches `ledger(<instance>): wake <wake_id>` where `<wake_id>` is the `wake_id`
  field of the LAST newly-copied raw source line.
- `git commit` is invoked with `-- <relDestPath>` (path-scoped — never a bare `git add -A`/`git
  commit -a`), with `cwd=publishRepoDir` (never the shared checkout).

### REQ-703: Best-effort non-fatality
**EARS**: WHEN any operation in the cycle (origin-url resolution, publish-repo setup, `add`,
`commit`, `push`, or divergence recovery) fails for any reason (offline, merge conflict, lock file,
non-zero exit) THE SYSTEM SHALL log at least one line to stderr describing the failure and SHALL NOT
throw — the wake loop's own `while` loop and every future wake continue unaffected.
**Edge Cases**:
- `git remote get-url origin` (against the shared checkout, read-only) or the publish-repo clone
  fails: the entire cycle is skipped non-fatally (`reason: 'setup-failed'`); no destination-file
  append, no marker mutation.
- The lock (REQ-708) is already held by a live process: the entire cycle is skipped non-fatally
  (`reason: 'locked'`); no destination-file append, no marker mutation, no publish-repo writes.
- `git commit` fails AFTER the destination file was already appended (e.g. lock file): the append is
  NOT undone (best-effort, evidence stays on disk uncommitted) but the marker's `copiedLineCount` is
  still advanced past those lines (REQ-707) so the SAME source lines are never re-appended on retry.
- `git push` fails (including when REQ-709's own recovery retry ALSO fails, e.g. persistent network
  outage): logged, `pendingLinesSincePush`/`pushedLineCount`/`lastPushTs` in the marker are left at
  their pre-attempt values so the next eligible cycle retries both the push and, if needed,
  divergence recovery — no data loss, no duplicate accounting.
- Any unexpected exception anywhere in the cycle (e.g. marker file I/O error): caught by an outermost
  try/catch inside `publishLedgerCycle` itself — the function NEVER throws under any input.
**Acceptance Criteria**:
- With an injected `git` function that throws on `remote`, `clone`, `commit`, or `push` (tested
  independently, including the "push AND recovery both fail" case), `publishLedgerCycle()` resolves
  (never rejects) and the caller sees a non-throwing result object.
- The wiring call site in `index.mjs` additionally wraps the call in try/catch as defense-in-depth
  (belt-and-suspenders — the module contract alone must already hold).

### REQ-704: Push throttle (pure decision)
**EARS**: WHEN deciding whether to `git push` on a given cycle THE SYSTEM SHALL push if AND ONLY IF
at least 10 new lines have been committed locally since the last successful push OR at least 15
minutes have elapsed since the last successful push; local (non-push) commits happen every cycle that
has new source lines, independent of this throttle.
**Edge Cases**:
- Exactly 10 pending lines: pushes (`>=`, not `>`).
- Exactly 15 minutes elapsed: pushes (`>=`, not `>`).
- Zero pending lines: never pushes, regardless of elapsed time (nothing new to push).
- `lastPushTs === 0` (never pushed before) with 1 pending line and `nowMs` far in the future: pushes
  once the 15-minute floor is crossed (no special-cased "first push" bypass).
**Acceptance Criteria**:
- `decidePublish({ pendingLineCount, lastPushTs, nowMs })` is a pure function (no I/O) with the above
  truth table, independently unit-tested across all four edge cases plus the below-threshold case.

### REQ-705: Dedicated per-instance orphan publish repo (FIND-001/002 — never the shared checkout)
**EARS**: WHEN a publish cycle needs to write ANY ledger content THE SYSTEM SHALL do so exclusively
inside a DEDICATED clone at `publishRepoDir` (default `$ANICCA_HOME/state/.ledger-publish-repo`),
checked out to a per-instance orphan branch `ledger-<ANICCA_INSTANCE>` of the SAME origin remote —
resolved via a single READ-ONLY `git remote get-url origin` against the shared checkout (`repoRoot`)
— and SHALL NEVER run `checkout`/`add`/`commit`/`reset`/`push` against `repoRoot` itself, in this
file or in any test of it. Each instance's branch and dedicated clone are exclusive to that
instance, so no two instances (e.g. `automaton` and `Franklin`, confirmed by impl-review iteration 1
to share the same host and default `ANICCA_REPO`) ever write to the same branch or directory.
**Setup** (idempotent, `ensurePublishRepo`): if `publishRepoDir/.git` is missing, `git clone
--no-checkout <originUrl> <publishRepoDir>`. Then `git fetch origin ledger-<instance>`; if that
succeeds (a prior publish already exists on origin), `git checkout -B ledger-<instance>
origin/ledger-<instance>` (tracking); if it fails (first-ever publish for this instance),
`git checkout --orphan ledger-<instance>`. The branch contains ONLY `<instance>.jsonl` + a one-time
`README.md` stub — never any file from `repoRoot`.
**Edge Cases**:
- `repoRoot` has uncommitted AND committed-but-unpushed changes at cycle time (e.g. `evolve.mjs`'s
  `promote()` mid-flight): both are byte-identical before and after the cycle — proven by the
  dedicated "leak test" (FIND-001/002) which asserts `repoRoot`'s `HEAD`, `git status --porcelain`,
  and current branch are unchanged, and that origin's own default branch ref is unchanged.
- Origin already has `ledger-<instance>` from a previous run: tracked via `checkout -B ... origin/...`
  (never re-created as a fresh orphan, which would discard prior history).
- `publishRepoDir` already exists and is already on the right branch: idempotent no-op re-fetch.
**Acceptance Criteria**:
- After a cycle with `pushed:true`, a FRESH clone of `ledger-<instance>` from origin contains ONLY
  `README.md` and `<instance>.jsonl` — nothing else, ever.
- `repoRoot`'s `git rev-parse HEAD`, `git status --porcelain`, and `git branch --show-current` are
  identical before and after any publish cycle, regardless of outcome.

### REQ-706: Two-layer redaction (security)
**EARS**: WHEN a raw ledger line's `result` or `skip_reason` free-text field is projected
(REQ-702) THE SYSTEM SHALL pass it through TWO redaction layers in sequence — (1)
`redactPrivateKeyPatterns()` (the SAME pure filter `index.mjs` already applies to every line at
write time) and (2) `redactBroaderSecretPatterns()` (a NEW, stricter pass scoped to this feature
only: base58 64-88 char runs — the shape of a Solana secret key — and generic 40+ hex char runs) —
then cap the result at 200 chars. Structured allowlisted fields (`tx`/`tx_hash`/`txHash`) are
validated by shape instead (REQ-702) and are never routed through this free-text redaction (they are
public on-chain data, not secrets).
**Edge Cases**:
- A line whose `result` field contains a `0x[0-9a-fA-F]{64}` pattern: redacted to `[REDACTED]` by
  layer 1.
- A line whose `result` field contains a Solana-shaped base58 88-char run: redacted by layer 2
  (layer 1 alone would miss this — it only matches `0x`-prefixed hex).
- A line whose `result` field contains a 40-hex string (e.g. a wallet address): redacted by layer 2
  — a DELIBERATELY stricter bar than `env-filter.mjs`'s own 64-hex-only contract, because this text
  is bound for a PUBLIC git branch rather than staying local.
- A field NOT in REQ-702's allowlist is never redacted because it is never published at all (dropped
  upstream by `projectLedgerLine()` — redaction is defense-in-depth on top of, never instead of, the
  allowlist).
**Acceptance Criteria**:
- Given a fabricated `result` value containing a 64-hex `0x...` pattern, a base58 88-char run, and a
  bare 40+-hex run, none of the three raw substrings appear in the published field; `[REDACTED]`
  does; the field is `<= 200` chars.

### REQ-707: Idempotent cursor advance (two cursors: local vs push-confirmed)
**EARS**: The marker persists TWO distinct cursors — `copiedLineCount` (source lines already
appended to the publish repo's working file, whether pushed or not) and `pushedLineCount` (source
lines CONFIRMED present on origin, the only cursor REQ-709's recovery ever trusts). WHEN new source
lines are appended THE SYSTEM SHALL persist the advanced `copiedLineCount` BEFORE attempting `git
commit` for that batch, so that a subsequent cycle never re-reads and re-appends the same source
lines into the destination file. WHEN a push succeeds THE SYSTEM SHALL advance `pushedLineCount` to
match `copiedLineCount` ONLY at that point — never speculatively.
**Edge Cases**:
- Commit fails right after a successful append+marker-write: next cycle's `readSourceLinesRaw` slice
  starts strictly after the already-copied lines — no duplicate append.
- Push fails (with or without a divergence-recovery attempt): `pushedLineCount` is left at its prior
  (last-confirmed) value — never advanced on a failed or merely-attempted push.
- Marker write itself fails (disk error): caught by REQ-703's outermost try/catch; the cycle is a
  no-op for accounting purposes (an acceptable, documented, non-money-critical risk — evidence
  duplication if it ever recurs is harmless for third-party verifiability, never silently lost).
**Acceptance Criteria**:
- Two consecutive `publishLedgerCycle()` calls where the FIRST call's injected `git` throws on
  `commit`: the SECOND call's destination-file content contains each source line exactly once (no
  duplicates), because its `newLines` slice starts from the already-advanced `copiedLineCount`.
- After a successful push, `marker.pushedLineCount === marker.copiedLineCount` and
  `marker.pendingLinesSincePush === 0`.

### REQ-708: Same-instance overlap lock (mkdir-atomic, pid-staleness reclaim)
**EARS**: WHEN a publish cycle is about to touch the publish repo THE SYSTEM SHALL first acquire an
mkdir-atomic lock at `lockDir` (default `$ANICCA_HOME/state/.ledger-publish-<instance>.lock`),
copying the idiom already established in this repo by `skills/self/claude-p-mainloop.sh` (pidfile
guard) and `scripts/disk-cleaner.sh` (mkdir-atomic lock — macOS has no `flock(1)` binary, both those
scripts already solve this the same way). WHEN the lock is already held by a LIVE process (`pid`
alive per `process.kill(pid, 0)`) THE SYSTEM SHALL skip the entire cycle non-fatally
(`reason: 'locked'`). WHEN the lock is held by a DEAD/unreadable pid THE SYSTEM SHALL reclaim it and
proceed. The lock is released in a `finally` block regardless of outcome.
**Edge Cases**:
- A live-held lock: zero publish-repo writes occur this cycle; the marker and source ledger are
  untouched.
- A stale lock (dead pid, or an unreadable/missing pid file): reclaimed, the cycle proceeds normally,
  and the lock is released again at the end of that same cycle.
- Cross-INSTANCE concurrency (e.g. `automaton` and `Franklin` on the same host) is structurally
  impossible to collide on, independent of this lock, because REQ-705 gives each instance its own
  `publishRepoDir`/branch/`lockDir` (all namespaced by `<instance>`) — this lock exists ONLY to guard
  the SAME instance racing itself (e.g. an unclean restart while a prior cycle was mid-flight).
**Acceptance Criteria**:
- With `lockDir` pre-seeded with this test process's own live pid, `publishLedgerCycle()` returns
  `reason: 'locked'` and creates no `publishRepoDir`.
- With `lockDir` pre-seeded with an astronomically-unlikely-to-be-alive pid, the cycle proceeds and
  the lock directory no longer exists once the cycle returns.

### REQ-709: Divergence recovery on a rejected push (FIND-005)
**EARS**: WHEN a `git push` is rejected (any push failure, most commonly a non-fast-forward
divergence — e.g. a stale local publish-repo state after an unclean shutdown) THE SYSTEM SHALL: (1)
`git fetch origin ledger-<instance>` then `git reset --hard origin/ledger-<instance>` in the publish
repo (never the shared checkout); (2) RE-PROJECT every source line from `marker.pushedLineCount`
(the only cursor known to be safely on origin — NEVER from the possibly-just-discarded
`copiedLineCount`) through the current end of `ledger.jsonl`, through REQ-702's field allowlist
again; (3) append, path-scoped commit, and retry the push exactly once. WHEN that retry ALSO fails
THE SYSTEM SHALL fall through to REQ-703's non-fatality contract (log, return non-throwing,
`pendingLinesSincePush`/`pushedLineCount` left at their pre-attempt values for the next cycle to
retry from scratch) — no line is ever silently dropped, because every recovery always starts from
`pushedLineCount`, never from local (potentially wiped) state.
**Edge Cases**:
- The publish repo has fallen behind origin (someone/something else advanced `ledger-<instance>`,
  e.g. this same instance restarting with a fresh/reset local clone): `reset --hard` fast-forwards
  onto origin's tip, PRESERVING whatever commits are already there (never a force-overwrite of
  origin) — only the LOCAL working copy is reset, then rebuilt on top.
- The origin branch doesn't exist yet at recovery time (a pathological first-cycle push failure):
  `git fetch` fails inside recovery too — caught by the SAME outer non-fatal contract (REQ-703), no
  special-casing needed.
**Acceptance Criteria**:
- Given a first successful publish (branch established on origin) followed by an OUTSIDE process
  pushing an unrelated commit to `ledger-<instance>`, and then a second local cycle with new source
  lines that reaches the push threshold: the second cycle's `pushed` is `true`, a FRESH clone of the
  branch contains every `wake_id` from BOTH the first and second cycle exactly once (no duplicates,
  no drops), and the outside process's commit is still present in history (never overwritten).
- `marker.pushedLineCount` after a successful recovery equals the total number of source lines
  processed so far; `marker.pendingLinesSincePush` is `0`.

## Non-Functional Requirements
- **Performance**: a disabled-flag cycle (the default) must add negligible overhead to the wake loop
  (no I/O at all — single env-var string comparison).
- **Security**: never publishes `daemon.err`, `.env`, wallet files, the model-authored `args` object,
  or any field outside REQ-702's explicit allowlist; free-text fields get REQ-706's two-layer
  redaction; the destination is a single instance-scoped file inside a DEDICATED clone, never a
  directory sweep, never the shared checkout.
- **Concurrency**: cross-instance concurrency is structurally impossible (REQ-705 — disjoint
  `publishRepoDir`/branch/`lockDir` per instance); same-instance overlap is guarded by REQ-708's
  mkdir-atomic lock. The shared checkout (`repoRoot`) is touched by AT MOST one read-only `git
  remote get-url origin` call per cycle — never written to, so it can never conflict with
  `evolve.mjs`'s `promote()` or any other writer of that checkout.
