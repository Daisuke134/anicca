# Life Manager CFO — One Local Hourly Loop Implementation Plan

**Goal:** Install exactly one local `launchd` job that reads real Moneytree data every hour, repairs bounded transient
failures, stores the first daily snapshot or a meaningful same-day correction, and sends at most one Telegram report
per snapshot revision.

**Status:** COMPLETE — one hourly launchd job installed; autonomous real-data successes 2/2.

**Ponytail decision:** Reuse the existing reader, recovery, report builder, revision RPC, delivery dedupe, renderer,
and Telegram transport. Add no agent, service, queue, database, framework, dependency, or cloud runner. The committed
change is exactly one runner plus one focused test. The local plist is runtime configuration, not repository code.

**Soft target:** two sequential minimal changes, each <=2 files: renderer compatibility <=6 production LOC, then
runner <=100 production LOC with focused tests <=180 LOC. If either target is exceeded, cut scope before continuing.

## Operating flow

```mermaid
flowchart TD
    LD[One launchd job\nevery 3600 seconds] --> READ[Real Moneytree Codex read]
    READ --> RECOVER{Bounded recovery}
    RECOVER -->|Recovered| REPORT[Canonical verified report]
    RECOVER -->|Still unavailable| ACTION[One action-required revision\nonly when a prior snapshot exists]
    REPORT --> LATEST{Latest owner/date snapshot}
    LATEST -->|None| FIRST[Append revision 1]
    LATEST -->|Same financial facts| QUIET[Exit 0 without Telegram]
    LATEST -->|Changed facts| CORRECT[Append revision N+1]
    ACTION --> CORRECT
    FIRST --> CLAIM[Durable delivery claim]
    CORRECT --> CLAIM
    CLAIM -->|Already sent| QUIET
    CLAIM -->|Send| TG[Telegram provider]
    TG --> RECEIPT[Positive message_id receipt]
```

## Evidence and decisions

- Local `man launchd.plist`: `StartInterval` starts a job every N seconds; an interval is skipped if the job is still
  running. Use one `StartInterval=3600`, one `RunAtLoad`, and no second calendar trigger.
- Apple, “Scheduling Timed Jobs”:
  https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html
  — “The preferred way to add a timed job is to use launchd.”
- Live audit: `ai.anicca.cfo-daily` is stopped with exit 127; `ai.anicca.life-manager-financial-report` is stopped with
  exit 1 and uses the obsolete five-minute enqueue path. Neither imports the current CFO sender.
- Live read-only audit: the correction RPC, revision-one RPC, and delivery-claim RPC all exist. A fresh real Moneytree
  read matched today's stored asset total; no private amount was printed.

## Review-discovered prerequisite — Luna aligns the existing action renderer

The first fresh review found a real normal-path mismatch: canonical recovery snapshots contain `nextRetryAt` and may
use `provider_outage`, while the existing renderer accepts neither. Appending that correction before rendering would
make the latest revision unreadable. Fix the consumer before resuming the runner; do not reshape or weaken the
canonical persisted snapshot.

**Luna owns only for this prerequisite:**

- Modify `apps/life-call/lib/cfo-telegram.js`
- Modify `apps/life-call/lib/cfo-telegram.test.js`

Write RED using an actual canonical action-required bundle shape. Require both `reconsent` and `provider_outage` with
the exact `nextRetryAt` field to render without a number or stale balance. Unknown action kinds, missing/extra keys,
and an invalid/empty retry timestamp remain fail-closed. Minimum GREEN: extend only the exact action key/kind/value
validation; do not alter report copy, buttons, callbacks, snapshot storage, or other states. Run focused renderer tests,
`npm run test:cfo`, `npm test`, and diff-check. Sol commits this prerequisite separately before runner closure.

Evidence: action compatibility shipped separately as `a89f4c41c` after RED, renderer `20/20`, CFO `254/254`, full
test exit `0`, strict calendar/time validation, <=6 added production lines, and fresh `ship — Spec ✅` review.

## RED-discovered prerequisite — recovered Moneytree coverage remains partial

The resumed runner RED exposed a second existing consumer mismatch. A successful Moneytree reread proves fresh assets
but does not prove liabilities, so the canonical recovery builder correctly emits `state=recovered` with partial
totals and exclusions. The renderer currently treats every recovered snapshot as complete and rejects that truthful
bundle. Do not erase the repair proof or invent liabilities/net worth to satisfy the old renderer.

**Luna owns only for this prerequisite:**

- Modify `apps/life-call/lib/cfo-telegram.js`
- Modify `apps/life-call/lib/cfo-telegram.test.js`

Write RED with the actual canonical recovered partial shape: fresh assets remain visible, liabilities/net worth remain
unknown, exclusions remain present, and the repair-success line is visible. Minimum GREEN: apply complete arithmetic
and no-exclusion rules only to `complete`; apply the existing partial unknown/exclusion rules to both `partial` and
`recovered`; keep recovered repair proof mandatory; use the partial title for truthful recovered coverage. Do not
change copy, builder, storage, buttons, callbacks, or action validation. Production delta <=6 physical lines. Run
renderer tests, `npm run test:cfo`, `npm test`, and diff-check. Sol commits/reviews this prerequisite separately, then
the same Luna resumes the preserved hourly runner RED.

## Task 1 — Luna builds the runner with TDD

**Luna owns only:**

- Create `apps/life-call/scripts/cfo-hourly-local.js`
- Create `apps/life-call/scripts/cfo-hourly-local.test.js`

Luna is not alone in the worktree. Do not revert or modify any other file. Do not edit specs, migrations, launchd
configuration, package metadata, existing CFO modules, or unrelated user changes.

### Required interfaces

- Export `runHourlyCfo(options)` and `main(options)`.
- `options` permits dependency injection for focused tests; production defaults use current modules and `process.env`.
- Required runtime values are `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `LM_UID_SECRET`,
  `LM_TELEGRAM_BOT_TOKEN`, plus owner UID and Telegram chat ID supplied by the local plist.
- Safe stdout is one JSON line containing only status, reporting date, revision, and booleans. Never print balances,
  account references, UID, chat ID, credentials, provider payloads, URLs, thrown messages, or stack traces.

### RED tests

1. A fresh first daily read performs one revision-1 append and one deduped Telegram delivery.
2. A second same-facts hourly read performs no append, passes the existing snapshot once through durable delivery
   dedupe, creates no provider send when already receipted, returns `quiet`, and exits successfully. This also heals a
   crash that persisted the snapshot before claiming delivery.
3. Changed financial facts append exactly revision `N+1`, then deliver that exact revision once.
4. A transient read failure recovered by the existing bounded recovery path sends only the recovered accurate report;
   it never sends the failed attempt.
5. `reconcile` remains retry/nonzero instead of quiet success; unknown delivery status fails closed. Provider/config
   failure returns one fixed redacted failure status and cannot expose sentinel amount/account/secret values.

Run RED:

```bash
node --test scripts/cfo-hourly-local.test.js
```

Expected: missing-module failure.

### Minimum GREEN behavior

1. Capture one clock value and derive the Tokyo owner date.
2. Call the existing `recoverMoneytreeRead`; its read callback calls `readMoneytreeViaCodex` with that same clock.
   Map the reader's closed unavailable error to a transient kind, use the existing bounded waits, and never log the
   failed payload.
3. Resolve the existing daily run identity.
4. Read only the latest snapshot metadata/report for the same UID and reporting date. Validate the returned report
   with the existing renderer before comparing it. Reject a mismatched run/date/revision.
5. If no snapshot exists and recovery succeeded, use `appendCfoDailySnapshot` for revision 1.
6. If the latest verified financial facts are unchanged, pass that exact persisted snapshot/ref through
   `deliverCfoTelegram`. `already_sent` returns `quiet`, `sent` closes a prior snapshot-before-delivery crash, and
   `reconcile` returns `retry`; durable claim/receipt prevents Telegram spam.
7. If facts changed or an existing healthy snapshot becomes action-required, build canonical revision `N+1` with
   `buildCfoDailyReportFromRecovery`, call the already-live `lm_append_cfo_daily_snapshot_revision` through the shared
   redacted RPC helper, and use the returned public ref. The downstream composite FK and delivery validator must keep
   a mismatched receipt fail-closed.
8. Call `deliverCfoTelegram` only with the exact persisted snapshot/revision. Its existing claim/receipt path prevents
   duplicate/new sends on retries.
9. If the first-ever read remains unavailable, return a safe retry status without inventing or sending a balance.
   `main` exits zero only for `sent` or verified `quiet`; `retry` and `failed` are nonzero and cannot count toward the
   two scheduled-success acceptance criterion.

### Verify before handoff

```bash
node --test scripts/cfo-hourly-local.test.js
npm run test:cfo
npm test
git diff --check
```

Require focused GREEN, CFO suite GREEN, full suite exit 0, two changed files, and runner <=100 production LOC. Luna
reports RED evidence, GREEN counts, LOC, and diff only; Luna does not commit, push, install, or send real Telegram.

## Task 2 — Sol reviews, installs, and verifies

1. Fresh Sol review checks only Critical/Important: wrong owner, wrong revision, stale/fabricated money, duplicate
   Telegram, raw private output, unbounded retry, more than one scheduler, and plan/LOC drift. Any fix returns to the
   same Luna.
2. Sol performs a real no-send run with the current Moneytree connection and proves only safe booleans/counts.
3. Sol creates one local plist at
   `/Users/anicca/Library/LaunchAgents/ai.anicca.life-manager-cfo-hourly.plist` with `RunAtLoad=true`,
   `StartInterval=3600`, `ProcessType=Background`, the fixed worktree, and private owner identifiers only in local
   runtime configuration. No secret enters Git.
4. Before bootstrap, Sol boots out both measured broken legacy CFO jobs so exactly one scheduler remains. Their files
   remain recoverable; do not delete them.
5. Bootstrap the new job without a manual kickstart. Confirm `launchctl print`, safe logs, a real Moneytree read,
   snapshot/delivery state, and a positive Telegram receipt when a report is due.
6. Observe two consecutive autonomous launchd starts without manual repair. Both must read real Moneytree data and
   exit 0; an unchanged second run must be quiet. Only then close CFO-1i and Product Stage 7.

## Completion condition

Exactly one local hourly scheduler is loaded. Two consecutive autonomous scheduled real-data runs exit successfully,
the first due revision is durably sent or already receipted, unchanged data creates no Telegram spam, changed data is
append-only and delivered once, and logs contain no private finance data or credentials.

## Live evidence

- Renderer prerequisites shipped separately as `a89f4c41c` and `9c72dc102`: canonical recovery actions render, and
  recovered Moneytree data stays partial rather than inventing liabilities/net worth. Both passed fresh review.
- Luna runner shipped as `65f4e9c12`: focused `8/8`, CFO `254/254`, full test exit `0`, node/diff checks, runner 87
  LOC, tests 164 LOC, and final fresh review `ship — Spec ✅`.
- A real Moneytree no-write/no-send run proved the latest verified report can be rendered and passed through durable
  delivery dedupe with append `0`, provider send `0`, and no private amount output. An earlier recovered-state probe
  reached the blocked append boundary; it was not evidence of a balance change and is not recorded as one.
- Broken `ai.anicca.cfo-daily` (exit 127) and `ai.anicca.life-manager-financial-report` (exit 1) were booted out without
  deleting their plist files. Exactly one `ai.anicca.life-manager-cfo-hourly` job is loaded with interval 3600.
- Autonomous launchd run 1/2: `runs=1`, last exit `0`, safe result `quiet`, revision 1, append false, delivery false,
  stderr 0 bytes. No manual kickstart was used. Product Stage 7 remained active pending run 2/2.
- Autonomous launchd run 2/2: `runs=2`, last exit `0`, safe result `quiet`, revision 1, append false, delivery false,
  stderr 0 bytes. No manual kickstart was used. Durable metadata remained one snapshot, one delivery claim, and one
  positive provider receipt, so unchanged data produced neither a duplicate revision nor Telegram spam. CFO-1i and
  Product Stage 7 are complete.
