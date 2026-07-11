# Behavioral Spec — franklin-ledger-push (P2: per-wake ledger auto commit+push)

Mode: **lean**. Source: `docs/loop-engineering/20-implementation-certainty-2026-07-11.md` §D
(anicca-project repo) — "P2 per-wake git push — 認証は生きている、push コードだけ無い". Goal: every
Franklin wake's ledger evidence becomes third-party-verifiable from `github.com/Daisuke134/anicca`
git history alone, without making the wake loop dependent on git/network succeeding.

## Purity Boundary Analysis

- **Pure core**: `decidePublish()` (batch/throttle decision — line-count OR time-elapsed), `extractWakeId()`
  (parse a JSON ledger line, pull `wake_id`), reuse of the existing pure `redactPrivateKeyPatterns()`
  (`env-filter.mjs`, unmodified). No I/O, deterministic, directly unit-testable.
- **Effectful shell**: `readMarker`/`writeMarker` (fs, throttle/cursor state at
  `$ANICCA_HOME/state/.ledger-publish-marker`), `readSourceLinesRaw`/`appendRawLines` (fs, source
  `ledger.jsonl` → repo-tracked `state/franklin-ledger/<instance>.jsonl`), `defaultGit` (child_process
  `execFileSync`, injectable), and the orchestrator `publishLedgerCycle()` which sequences all of the
  above. Wired into `index.mjs`'s main wake loop (`while (!shuttingDown) { await runOneWake(); ... }`)
  — never inside `runOneWake()` itself, so it never affects any of `runOneWake`'s own return paths.

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

### REQ-702: Copy + path-scoped commit when enabled
**EARS**: WHEN `LEDGER_PUBLISH_ENABLED="1"` AND the source `ledger.jsonl` has lines not yet copied
THE SYSTEM SHALL append those lines (redacted) to `state/franklin-ledger/<ANICCA_INSTANCE>.jsonl`
inside the `~/anicca` repo working tree and commit ONLY that path, copying `evolve.mjs:154-192`'s
idiom exactly: `git add -- <path>`, then
`git -c user.name=... -c user.email=... commit -m "ledger(<instance>): wake <wake_id>" -- <path>`.
**Edge Cases**:
- Repo-tracked destination directory does not exist yet: created (`fs.mkdir(..., {recursive:true})`),
  matching `ledger.mjs:22`'s own pattern.
- `ANICCA_INSTANCE` unset: falls back to `"clawrouter"` (matches `anicca-daemon.sh:28`'s own default).
- Zero new source lines: no append, no commit attempted this cycle (`reason: 'no-new-lines'` when
  there is also no push-pending backlog).
**Acceptance Criteria**:
- After a cycle with N new source lines, the destination file's line count grows by exactly N and its
  content matches the (redacted) source lines verbatim.
- The commit message matches `ledger(<instance>): wake <wake_id>` where `<wake_id>` is the `wake_id`
  field of the LAST newly-copied line.
- `git commit` is invoked with `-- <destPath>` (path-scoped — never a bare `git add -A`/`git commit -a`).

### REQ-703: Best-effort non-fatality
**EARS**: WHEN any git operation (`fetch`, `merge`, `add`, `commit`, `push`) fails for any reason
(offline, merge conflict, lock file, non-zero exit) THE SYSTEM SHALL log exactly one line to stderr
describing the failure and SHALL NOT throw — the wake loop's own `while` loop and every future wake
continue unaffected.
**Edge Cases**:
- `git fetch`/`merge --ff-only` fails (REQ-705's sync step): the entire cycle is skipped non-fatally;
  no destination-file append, no marker mutation.
- `git commit` fails AFTER the destination file was already appended (e.g. lock file): the append is
  NOT undone (best-effort, evidence stays on disk uncommitted) but the marker's `copiedLineCount` is
  still advanced past those lines (REQ-707) so the SAME source lines are never re-appended on retry.
- `git push` fails: logged, `pendingLinesSincePush`/`lastPushTs` in the marker are left unchanged so
  the next eligible cycle retries the push (no data loss, no duplicate accounting).
- Any unexpected exception anywhwere in the cycle (e.g. marker file I/O error): caught by an outermost
  try/catch inside `publishLedgerCycle` itself — the function NEVER throws under any input.
**Acceptance Criteria**:
- With an injected `git` function that throws on `fetch`, `commit`, or `push` (tested independently),
  `publishLedgerCycle()` resolves (never rejects) and the caller sees a non-throwing result object.
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

### REQ-705: Sync before commit
**EARS**: WHEN there are new source lines to publish THE SYSTEM SHALL run `git fetch origin main`
then `git merge --ff-only origin/main` BEFORE any `git add`/`git commit` for the cycle; WHEN that sync
fails THE SYSTEM SHALL skip the entire cycle (no append, no commit, no marker mutation) and rely on
the next wake to retry from scratch.
**Edge Cases**:
- Local branch already up to date: `merge --ff-only` is a no-op fast-forward (still executed, keeps
  behavior uniform and testable).
- Non-fast-forward-able divergence (e.g. someone else committed to the SAME destination file
  upstream): `merge --ff-only` fails → cycle skipped this wake, retried next wake after the situation
  potentially resolves.
**Acceptance Criteria**:
- With an injected `git` that throws specifically on the `merge` call, no destination-file write
  occurs and the marker is untouched.

### REQ-706: Redaction pass-through (security)
**EARS**: WHEN copying a source ledger line into the repo-tracked destination file THE SYSTEM SHALL
pass it through `redactPrivateKeyPatterns()` (the SAME pure filter `index.mjs` already applies to
every line at write time — verified: every `safeAppend(LEDGER_PATH, ...)` call site in `index.mjs`
either builds from known-safe structured fields only, or passes free-text through
`redactPrivateKeyPatterns` first) as a defense-in-depth second pass — never publish `daemon.err` or
any file other than `ledger.jsonl` lines.
**Edge Cases**:
- A line that (hypothetically, contrary to the write-time invariant) still contains a
  `0x[0-9a-fA-F]{64}` pattern: redacted to `[REDACTED]` before it ever reaches the repo-tracked file
  or `git add`.
- A line containing a 40-hex wallet address (not a private key): left untouched (matches
  `env-filter.mjs`'s own `PRIVKEY_PATTERN` contract — addresses are not secrets).
**Acceptance Criteria**:
- Given a fabricated ledger line containing a 64-hex `0x...` pattern, the corresponding line written
  to the destination file has that pattern replaced with `[REDACTED]`.

### REQ-707: Idempotent cursor advance
**EARS**: WHEN new source lines are appended to the destination file THE SYSTEM SHALL persist the
advanced `copiedLineCount` in the marker file BEFORE attempting `git commit` for that batch, so that
a subsequent cycle (regardless of whether THIS cycle's commit succeeded or failed) never re-reads and
re-appends the same source lines into the destination file.
**Edge Cases**:
- Commit fails right after a successful append+marker-write: next cycle's `readSourceLinesRaw` slice
  starts strictly after the already-copied lines — no duplicate append.
- Marker write itself fails (disk error): caught by REQ-703's outermost try/catch; the cycle is a
  no-op for accounting purposes (an acceptable, documented, non-money-critical risk — evidence
  duplication if it ever recurs is harmless for third-party verifiability, never silently lost).
**Acceptance Criteria**:
- Two consecutive `publishLedgerCycle()` calls where the FIRST call's injected `git` throws on
  `commit`: the SECOND call's destination-file content contains each source line exactly once (no
  duplicates), because its `newLines` slice starts from the already-advanced cursor.

## Non-Functional Requirements
- **Performance**: a disabled-flag cycle (the default) must add negligible overhead to the wake loop
  (no I/O at all — single env-var string comparison).
- **Security**: never publishes `daemon.err`, `.env`, wallet files, or anything outside
  `ledger.jsonl`'s own already-redacted lines; the destination path is a single instance-scoped file
  under `state/franklin-ledger/`, never a directory sweep.
- **Concurrency**: the wake loop is single-process/single-flight (`while (!shuttingDown)`), so no two
  `publishLedgerCycle()` invocations for the SAME instance ever run concurrently; no locking needed
  within this feature's scope.
