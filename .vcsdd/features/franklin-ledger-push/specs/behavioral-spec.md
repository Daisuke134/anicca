# Behavioral Spec — franklin-ledger-push (P2: per-wake ledger auto commit+push)

Mode: **lean**. Source: `docs/loop-engineering/20-implementation-certainty-2026-07-11.md` §D
(anicca-project repo) — "P2 per-wake git push — 認証は生きている、push コードだけ無い". Goal: every
Franklin wake's ledger evidence becomes third-party-verifiable from `github.com/Daisuke134/anicca`
git history alone, without making the wake loop dependent on git/network succeeding.

## Changelog

- **impl-review iter3 fixes: FIND-001..003 (fresh-context adversary, iteration 3).** (1) **FIND-001
  (critical)**: iter2's earn allowlist (REQ-702) dropped `external`/`confirmed`/`fill_tid`, so
  `skills/_shared/lib/ledger.mjs::isProfitable()` — the repo's single source of truth for "is this
  a real, GATE-0 profitable earn" — could never return `true` against any published earn line
  (`external!==true` alone gates the whole classifier false unconditionally; Solana lines
  additionally lost `confirmed`; Hyperliquid lines lost BOTH of their only settlement-proof fields,
  `fill_tid` and `confirmed`). The published branch could show dollar amounts but never let a third
  party run the project's own classifier against them — REQ-702's allowlist is rewritten below to
  include all three, type/shape-checked, never coerced. (2) **FIND-002 (major)**: in the
  push-rejection retry branch, `pushed = true` was set unconditionally after the retry's try block
  even when the post-reset reconcile found nothing pending and NO `git push` was actually re-issued
  — misreporting a push as confirmed (`lastPushTs`/`publishFailureStreak` updated off the false
  signal). Fixed: `pushed` is now only set true immediately after a `git push` call inside the
  retry's own `if (pendingLineCount > 0)` guard. (3) **FIND-003**: `sig` only had a bare
  length/type check, not real shape validation, despite REQ-706 already claiming it gets "the same
  treatment" as `tx`'s hash-shape check. Fixed: `sig` now requires the base58, 64-88-char shape
  `record-swap.mjs` actually writes.
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
- **impl-review iter2 fixes: FIND-001..006 (fresh-context adversary, iteration 2).** (1) **FIND-001
  (critical)**: the iter1 design only ever read `state/ledger.jsonl` (per-wake bookkeeping — no dollar
  amount, no on-chain reference), so the published branch could never actually prove "the
  balance/actions grow" — the money evidence lives EXCLUSIVELY in
  `skills/earn/state/earn-ledger.jsonl`, a file the feature never read. Fixed by publishing BOTH
  sources onto the SAME per-instance branch as two separate files — `<instance>-wake.jsonl` and
  `<instance>-earn.jsonl` — each with its own field allowlist (REQ-702 rewritten below) and its own
  independently-reconciled cursor. (2) **FIND-002 (critical)**: the iter1 recovery only fired on a
  REJECTED push; a publish-repo directory lost/recreated between a local commit and its later push
  produced a CLEAN fast-forward instead, so the recovery never triggered and the marker falsely
  claimed the lost lines were pushed — REQ-709 is rewritten below: the marker's cached
  `pushedLineCount` is NEVER trusted; every cycle reconciles each source's cursor directly against
  the ACTUAL, just-synced destination file's line count. (3) **FIND-003**: the iter1 divergence test
  used an outside writer colliding on the SAME exclusive branch — REQ-705 itself calls this
  "structurally impossible". The suite now proves recovery against the REALISTIC, reachable trigger
  for THIS topology: publish-repo directory loss between cycles. (4) **FIND-004**: the iter1 header
  comment and REQ-708 falsely cited `scripts/disk-cleaner.sh` as an established mkdir-atomic-lock
  precedent — that file does not exist anywhere in this repository. The only real sibling precedent
  is `skills/self/claude-p-mainloop.sh`'s pidfile guard; the fabricated citation is removed from both
  the code and REQ-708 below. (5) **FIND-005**: no escalation path existed for a persistently-broken
  publish pipeline (e.g. a revoked git credential) — REQ-703 now tracks a `publishFailureStreak`,
  escalated by `index.mjs`'s wiring via the EXISTING `appendHarnessFailure` mechanism at 5
  consecutive failures, plus a one-time, non-fatal `git ls-remote` reachability probe at first-ever
  setup. (6) **FIND-006**: the dedicated clone had no `--depth`/`--single-branch` limiting flag,
  fetching the mother repo's full history merely to publish a small side branch — REQ-705 now
  specifies a shallow (`--depth 1 --single-branch --no-tags`) clone with every subsequent fetch also
  depth-capped.

## Purity Boundary Analysis

- **Pure core**: `decidePublish()` (batch/throttle decision — line-count OR time-elapsed),
  `extractWakeId()`/`extractEarnRef()` (parse a source line, pull its own id field), `projectWakeLine()`
  / `projectEarnLine()` (REQ-702's per-source field-allowlist projections — FIND-001: TWO distinct
  allowlists, one per source, since the wake and earn schemas are unrelated — parse one raw source
  line and return only known-safe, type-checked fields; every other field, including the
  model-authored `args` object, is dropped), `redactBroaderSecretPatterns()` (REQ-706's second,
  stricter redaction pass for free-text fields), and reuse of the existing pure
  `redactPrivateKeyPatterns()` (`env-filter.mjs`, unmodified). No I/O, deterministic, directly
  unit-testable.
- **Effectful shell**: `readMarker`/`writeMarker` (fs, cursor state at
  `$ANICCA_HOME/state/.ledger-publish-marker`, now `{ wake: {pushedLineCount}, earn:
  {pushedLineCount}, lastPushTs, publishFailureStreak }` — FIND-001/002), `readLinesOrEmpty`/
  `appendRawLines` (fs, source jsonl → `<publishRepoDir>/<instance>-{wake,earn}.jsonl`),
  `acquireLock`/`releaseLock` (REQ-708, mkdir-atomic same-instance-overlap guard),
  `ensurePublishRepo` (REQ-705, sets up the DEDICATED shallow clone + orphan/tracking branch, FIND-
  002/006), `reconcileSource` (REQ-709 — FIND-002: derives each source's ground-truth
  `pushedLineCount` directly from the just-synced destination file's actual line count, never the
  marker), `checkOriginReachability` (REQ-703 — FIND-005, one-time non-fatal probe at first-ever
  setup), `defaultGit` (child_process `execFileSync`, injectable), and the orchestrator
  `publishLedgerCycle()` which sequences all of the above for BOTH sources every cycle. Wired into
  `index.mjs`'s main wake loop (`while (!shuttingDown) { await runOneWake(); ... }`) — never inside
  `runOneWake()` itself, so it never affects any of `runOneWake`'s own return paths; the wiring also
  inspects the returned `publishFailureStreak` and escalates via the existing `appendHarnessFailure`
  mechanism at 5 consecutive failures (FIND-005).

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

### REQ-702: Dual-source field-allowlist copy + path-scoped local commit into the DEDICATED publish repo
**EARS**: WHEN `LEDGER_PUBLISH_ENABLED="1"` AND either source has lines not yet reconciled as
published (REQ-709) THE SYSTEM SHALL project each new line through that source's explicit field
allowlist and append the projected lines to `<publishRepoDir>/<ANICCA_INSTANCE>-<source>.jsonl`
(inside the DEDICATED clone, REQ-705 — never inside the shared checkout), then commit ONLY the
touched path(s) this cycle (+ the one-time `README.md`), copying `evolve.mjs:154-192`'s idiom:
`git add -- <paths>`, then `git -c user.name=... -c user.email=... commit -m "ledger(<instance>):
wake <id> [+ earn <id>]" -- <paths>`. **FIND-001 (impl-review iter2, critical)**: this feature
publishes BOTH sources onto the SAME branch as two SEPARATE files, each with its own allowlist:
- **wake source** (`state/ledger.jsonl` → `<instance>-wake.jsonl`): `ts`, `wake_id`, `kind`, `slot`,
  `attemptsUsed`, `profitable`, `exit_code`, `sleep_s`, `model`, any `net_*`/`earn_*`/`cost_*`
  numeric field (matches `self-eval.mjs`'s own `net_usdc`/`cost_usdc`/`earn_usdc` convention), any
  `tx`/`tx_hash`/`txHash` field whose value matches a hash shape (`0x[0-9a-fA-F]{6,64}`), and
  `result`/`skip_reason` (REQ-706's two-layer redaction, capped at 200 chars).
- **earn source** (`skills/earn/state/earn-ledger.jsonl` → `<instance>-earn.jsonl`, THE money
  evidence — `ts`/`net_usdc`/`tx`/`sig` never exist in the wake source at all, verified live against
  `skills/_shared/lib/ledger.mjs::deriveLine` and `skills/earn/sol-trade/lib/record-swap.mjs:48-55`):
  `ts`, `wallet` (a public wallet address, not a secret), `source`, `wake` (this source's own id
  field), `earn_usdc`, `cost_usdc`, `net_usdc`, `tx` (EVM tx hash, hash-shape-validated like the wake
  source's `tx` field), `sig` (Solana tx signature — a PUBLIC on-chain reference, shape-validated
  base58/64-88-char, same discipline as `tx`, never routed through free-text redaction), `status`,
  `chain`, `task` (REQ-706's two-layer redaction, capped at 200 chars), and — **impl-review iter3
  FIND-001 (critical)** — `external` (boolean), `confirmed` (boolean), and `fill_tid` (Hyperliquid's
  settlement id: a finite number, or a bounded identifier-shaped string). These three are REQUIRED
  by `skills/_shared/lib/ledger.mjs::isProfitable(line)` (the repo's single source of truth for "is
  this a real, GATE-0 profitable earn": `external===true` AND a chain-correct confirmation —
  `tx`+`status==='0x1'` for EVM, `sig`+`confirmed===true` for Solana, `fill_tid`+`confirmed===true`
  for Hyperliquid) — dropping any of them makes `isProfitable()` unconditionally return `false`
  against the published data regardless of the source line's real profitability, which defeats this
  feature's own stated purpose (third-party-verifiable "the balance grows").
In BOTH allowlists, every other field is DROPPED, fail-closed — this is structural parsing of a
fixed machine format, never judgment. The model-authored `args` object is NEVER published.
**Edge Cases**:
- `publishRepoDir` does not exist yet: created via REQ-705's `ensurePublishRepo`.
- `ANICCA_INSTANCE` unset: falls back to `"clawrouter"` (matches `anicca-daemon.sh:28`'s own default).
- One source has new lines, the other doesn't: only the touched source's file is written/added to
  the commit — a source with zero lines ever published has no file on the branch at all yet.
- Zero new lines on EITHER source: no append, no commit attempted this cycle (`reason:
  'no-new-lines'`).
- A source line that is malformed JSON or not a plain object: the pure `projectWakeLine()`/
  `projectEarnLine()` returns `null` for it, but the ORCHESTRATOR substitutes an empty `{}`
  placeholder line rather than silently dropping it from the position sequence (FIND-002, REQ-709):
  every processed source line ALWAYS produces exactly one destination line, so the destination
  file's actual line count stays a valid 1:1 proxy for "source lines processed", which is what makes
  REQ-709's published-content-as-truth reconciliation sound.
**Acceptance Criteria**:
- After a cycle with N new source lines on a given source, that source's destination file's line
  count increases by exactly N (never fewer, per the placeholder rule above) and each written line's
  content is a strict subset of that source's allowlisted fields.
- The commit message includes `wake <id>` and/or `earn <id>` segments for whichever source(s) had
  new content this cycle, where `<id>` is that source's own id field (`wake_id` for wake, `wake` for
  earn) of the LAST newly-projected line.
- `git commit` is invoked with `-- <touched paths>` (path-scoped — never a bare `git add -A`/`git
  commit -a`), with `cwd=publishRepoDir` (never the shared checkout).
- A fabricated earn-ledger line containing `net_usdc`/`tx`/`sig` results in those exact fields
  appearing, unredacted-by-shape, in the published `<instance>-earn.jsonl` — third-party
  verifiability of "the balance grows" (this feature's stated purpose) is restored (FIND-001).
- **impl-review iter3 FIND-001**: a real profitable earn-ledger line (one where
  `skills/_shared/lib/ledger.mjs::isProfitable(line) === true` BEFORE publishing) still satisfies
  `isProfitable(published_line) === true` AFTER round-tripping through `projectEarnLine` — proven for
  all three chain paths (EVM `tx`+`status`, Solana `sig`+`confirmed`, Hyperliquid `fill_tid`+
  `confirmed`), using the real imported `isProfitable`, never a re-implementation of its rules.

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
  NOT undone (best-effort, evidence stays on disk uncommitted), caught locally in `appendAndCommit`
  (REQ-707); neither source's persisted `pushedLineCount` is advanced past this cycle's reconciled
  actual state, so the NEXT cycle's fresh sync-then-reconcile (REQ-709) never re-appends duplicates.
- `git push` fails (including when the same-cycle re-sync retry ALSO fails, e.g. persistent network
  outage): logged, `pushedLineCount`/`lastPushTs` in the marker are left at their pre-attempt
  (reconciled-actual) values so the next eligible cycle retries both the push and, if needed,
  divergence recovery — no data loss, no duplicate accounting; `publishFailureStreak` increments
  (FIND-005).
- Any unexpected exception anywhere in the cycle (e.g. marker file I/O error): caught by an outermost
  try/catch inside `publishLedgerCycle` itself — the function NEVER throws under any input.
**Acceptance Criteria**:
- With an injected `git` function that throws on `remote`, `clone`, `commit`, or `push` (tested
  independently, including the "push AND recovery both fail" case), `publishLedgerCycle()` resolves
  (never rejects) and the caller sees a non-throwing result object.
- The wiring call site in `index.mjs` additionally wraps the call in try/catch as defense-in-depth
  (belt-and-suspenders — the module contract alone must already hold).

**FIND-005 (impl-review iter2) — consecutive-failure escalation + reachability probe**: the marker
persists a `publishFailureStreak` counter, incremented on a setup failure OR a push-attempt failure
(both the primary attempt and its one re-sync retry), and reset to `0` the moment `ensurePublishRepo`
itself succeeds (proof the auth/clone/fetch/checkout path is healthy this cycle, independent of
whether there was anything new to push). `publishLedgerCycle()` returns this streak to the caller;
`index.mjs`'s wiring escalates via the EXISTING `appendHarnessFailure` mechanism (never a new
writer) once the streak reaches 5 consecutive failures (`kind: 'ledger_publish_stuck'`), so a stuck
pipeline (e.g. a revoked/read-only git credential) surfaces to healthchecks instead of failing
silently on stderr forever. A ONE-TIME, non-fatal `git ls-remote --exit-code <originUrl> HEAD` probe
runs right before the FIRST-EVER dedicated-clone setup and logs clearly (no secrets — the origin URL
for this repo carries no embedded token; auth is via the host-global `gh auth git-credential` helper,
never printed) if it fails; it never blocks the cycle either way.
**Acceptance Criteria**:
- 5 consecutive cycles whose setup fails leave `result.publishFailureStreak === 5`; the next
  successful setup resets it to `0`.
- A failing `ls-remote` probe logs a message containing neither the origin URL's credentials nor any
  `ghp_`/`gho_`/`github_pat_`-shaped token, and the cycle still completes (published/pushed
  normally) despite the probe's own failure.
- The probe is invoked at most once per dedicated-clone lifetime (never re-run once
  `publishRepoDir/.git` already exists).

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
--no-checkout --depth 1 --single-branch --no-tags <originUrl> <publishRepoDir>` (FIND-006, impl-
review iter2: shallow — this clone only ever needs ONE small orphan branch's tip, never the mother
repo's full history across every branch). Then `git fetch --depth 1 --no-tags origin
+refs/heads/ledger-<instance>:refs/remotes/origin/ledger-<instance>` (an EXPLICIT `src:dst` refspec
— this ALWAYS creates/updates the remote-tracking ref regardless of the clone's single-branch
default, which only knows the remote's default HEAD branch, e.g. `main`, not this per-instance
branch; `--depth 1` keeps every subsequent fetch shallow too, never silently deepening/unshallowing
the clone); if that succeeds (a prior publish already exists on origin), `git checkout -B
ledger-<instance> origin/ledger-<instance>` (tracking — this syncs the local working tree to
origin's REAL current tip, which is what makes REQ-709's published-content-as-truth reconciliation
valid); if it fails (first-ever publish for this instance), the system forces a deterministic,
GUARANTEED-EMPTY orphan state on EVERY such call (never trusting locally-lingering
committed-but-never-confirmed content from a prior cycle as truth — FIND-002): `git checkout
--orphan ledger-<instance>` (or a plain `checkout` if already on that branch from a prior not-yet-
pushed cycle) followed by deleting both destination files + `README.md` from the working tree. The
branch contains ONLY `<instance>-wake.jsonl` + `<instance>-earn.jsonl` + a one-time `README.md`
stub — never any file from `repoRoot`.
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
  `README.md` and whichever of `<instance>-wake.jsonl`/`<instance>-earn.jsonl` have ever had content
  — nothing else, ever (FIND-001: both files when both sources have published at least once).
- `repoRoot`'s `git rev-parse HEAD`, `git status --porcelain`, and `git branch --show-current` are
  identical before and after any publish cycle, regardless of outcome.

### REQ-706: Two-layer redaction (security)
**EARS**: WHEN a raw source line's free-text field (`result`/`skip_reason` on the wake source,
`task` on the earn source — FIND-001) is projected (REQ-702) THE SYSTEM SHALL pass it through TWO
redaction layers in sequence — (1) `redactPrivateKeyPatterns()` (the SAME pure filter `index.mjs`
already applies to every line at write time) and (2) `redactBroaderSecretPatterns()` (a NEW,
stricter pass scoped to this feature only: base58 64-88 char runs — the shape of a Solana secret
key — and generic 40+ hex char runs) — then cap the result at 200 chars. Structured allowlisted
fields (`tx`/`tx_hash`/`txHash` on the wake source; `tx`/`sig`/`fill_tid` on the earn source) are
validated by shape/type instead (REQ-702) and are never routed through this free-text redaction
(they are public on-chain/settlement references, not secrets). **impl-review iter3 FIND-003**: `sig`
now gets REAL shape validation — matched against `/^[1-9A-HJ-NP-Za-km-z]{64,88}$/` (base58 alphabet,
64-88 chars — the exact shape `skills/earn/sol-trade/lib/record-swap.mjs` writes, verified live),
the same discipline `tx` already has via `TX_HASH_VALUE`, not a bare `1 <= length <= 200` check as
in the previous revision.
**Edge Cases**:
- A line whose `result` field contains a `0x[0-9a-fA-F]{64}` pattern: redacted to `[REDACTED]` by
  layer 1.
- A line whose `result` field contains a Solana-shaped base58 88-char run: redacted by layer 2
  (layer 1 alone would miss this — it only matches `0x`-prefixed hex).
- A line whose `result` field contains a 40-hex string (e.g. a wallet address): redacted by layer 2
  — a DELIBERATELY stricter bar than `env-filter.mjs`'s own 64-hex-only contract, because this text
  is bound for a PUBLIC git branch rather than staying local.
- A field NOT in REQ-702's allowlist is never redacted because it is never published at all (dropped
  upstream by `projectWakeLine()`/`projectEarnLine()` — redaction is defense-in-depth on top of,
  never instead of, the allowlist).
- **impl-review iter3 FIND-003**: a `sig` value that is the wrong length or contains a character
  outside the base58 alphabet (e.g. `0`, `O`, `I`, `l`) is DROPPED by the allowlist (REQ-702), not
  published verbatim and not redacted — shape validation is fail-closed, matching `tx`'s treatment.
**Acceptance Criteria**:
- Given a fabricated `result` value containing a 64-hex `0x...` pattern, a base58 88-char run, and a
  bare 40+-hex run, none of the three raw substrings appear in the published field; `[REDACTED]`
  does; the field is `<= 200` chars.

### REQ-707: Idempotent commit failure (superseded by REQ-709's published-content-as-truth model)
**EARS**: The iter1 design's separate `copiedLineCount` (local-only, "committed but maybe not
pushed") cursor is REMOVED entirely (impl-review iter2 FIND-002): tracking a local-only cursor
across cycles is exactly the assumption that made a lost/recreated publish-repo directory produce a
silent gap. WHEN `git add`/`git commit` fails for a batch that was already appended to the
destination working file THE SYSTEM SHALL log and treat the cycle as `committed:false` (REQ-703 —
caught in `appendAndCommit`'s own try/catch, never falling through to the generic outermost 'error'
catch), and SHALL NOT advance either source's persisted `pushedLineCount` past that cycle's
RECONCILED `actualPublishedLineCount` (REQ-709) — regardless of whether the uncommitted append is
still sitting in the working tree. The NEXT cycle's `ensurePublishRepo` (REQ-705) resyncs the
dedicated clone to actual origin/guaranteed-empty state before any new work is derived, so the
uncommitted leftover is superseded (never duplicated) rather than needing its own persisted cursor.
**Edge Cases**:
- Commit fails right after a successful append: the destination working file physically contains the
  appended (uncommitted) content, but `pushedLineCount` was NOT advanced for it — the next cycle's
  resync-then-reconcile naturally supersedes it with a freshly-derived, non-duplicated batch.
- Marker write itself fails (disk error): caught by REQ-703's outermost try/catch.
**Acceptance Criteria**:
- Two consecutive `publishLedgerCycle()` calls where the FIRST call's injected `git` throws
  specifically on `commit`: the SECOND call's destination-file content (once actually confirmed
  pushed) contains each source line exactly once — no duplicates, and `reason` is never the generic
  `'error'` for a commit-only failure.
- After a successful push, `marker.<source>.pushedLineCount` equals that source's actual published
  line count for both sources.

### REQ-708: Same-instance overlap lock (mkdir-atomic, pid-staleness reclaim)
**EARS**: WHEN a publish cycle is about to touch the publish repo THE SYSTEM SHALL first acquire an
mkdir-atomic lock at `lockDir` (default `$ANICCA_HOME/state/.ledger-publish-<instance>.lock`),
copying the idiom already established in this repo by `skills/self/claude-p-mainloop.sh`'s pidfile
guard (its own header explicitly documents "NOT flock — macOS has no `flock(1)` binary"; this is the
ONLY real sibling precedent in this repository — impl-review iter2 FIND-004 found the previously-
cited `scripts/disk-cleaner.sh` does not exist anywhere in this repo, and that citation has been
removed from both this spec and the implementation). WHEN the lock is already held by a LIVE process (`pid`
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

### REQ-709: Published-content-as-truth cursor reconciliation (FIND-002, rewritten impl-review iter2)
**EARS**: THE SYSTEM SHALL NEVER trust the marker's cached `pushedLineCount` as ground truth for
either source. EVERY cycle, AFTER `ensurePublishRepo` (REQ-705) syncs the dedicated clone's working
tree to origin's REAL current tip (or to a guaranteed-empty state pre-first-push), THE SYSTEM SHALL
derive that source's `pushedLineCount` for THIS cycle directly from the ACTUAL line count of the
just-synced destination file (`reconcileSource`) — unconditionally. This single reconciliation
simultaneously covers both directions the marker's cache could be wrong: a cached value that was too
HIGH (commits actually lost — e.g. the publish-repo directory was deleted/recreated between cycles,
impl-review iter2 FIND-002's exact reachable trigger) is healed DOWNWARD to the real count; a cached
value that was too LOW (the marker itself was lost/reset while origin already had more content) is
adopted UPWARD to the real count. New source lines (`sourceLines.slice(reconciledPushedLineCount)`)
are re-derived from `ledgerPath`/`earnLedgerPath` (both durable, entirely independent of the
disposable publish-repo clone) EVERY cycle — never from a separately-tracked "locally committed but
not yet pushed" cursor, which is exactly the kind of state that FIND-002 showed cannot be trusted to
survive a lost/recreated publish-repo directory. WHEN a `git push` is rejected (e.g. a genuine
divergence) THE SYSTEM SHALL `git fetch` (the same explicit-refspec, depth-capped form as REQ-705)
then `git reset --hard origin/ledger-<instance>`, then re-run the SAME reconcile→append→commit
sequence once more (which naturally re-derives from the FRESH post-reset actual state, not any
stale local assumption) and, ONLY IF that re-derived state still has a positive pending line count
for either source, retry the push exactly once. **impl-review iter3 FIND-002**: if the re-derived
pending line count is ZERO after the reset (e.g. origin already had this cycle's content — an
ambiguous network failure where the primary push actually landed before the client observed the
failure), NO push call is issued in the retry branch and the cycle's `pushed` result MUST stay
`false` — it is never set true unless a `git push` call was actually (re-)issued and observed to
succeed THIS cycle; `lastPushTs`/`publishFailureStreak` follow the SAME truthful flag. WHEN the
retry's own push call IS issued and ALSO fails THE SYSTEM SHALL
fall through to REQ-703's non-fatality contract (log, return non-throwing, `publishFailureStreak`
incremented) — the persisted `pushedLineCount` for each source is set to that cycle's RECONCILED
`actualPublishedLineCount` (never speculatively advanced past it), so the next cycle re-derives
exactly the same, still-unconfirmed delta from source — no line is ever silently dropped or
double-counted.
**FIND-002's structural precondition**: for "actual destination file line count" to be a valid proxy
for "source lines processed", every processed source line must produce EXACTLY one destination line
— REQ-702's placeholder rule (a `{}` for a malformed/non-object source line, never a drop) is what
makes this 1:1 index alignment hold.
**Edge Cases**:
- The publish-repo directory is lost/recreated entirely between two cycles (FIND-002/FIND-003's
  realistic trigger — never an outside writer on the same exclusive branch, which REQ-705 already
  makes structurally impossible): the next cycle's `ensurePublishRepo` either syncs fresh from
  origin (if a prior cycle's push had already landed) or forces the guaranteed-empty pre-first-push
  state — either way `reconcileSource` reads the REAL actual state and re-derives any genuinely
  unconfirmed source lines from scratch. No gap.
- A genuine divergence (a rejected push mid-cycle): fetch+reset onto origin's tip PRESERVES whatever
  commits are already there (never a force-overwrite of origin) — only the LOCAL working copy is
  reset, then rebuilt on top.
- The origin branch doesn't exist yet at retry time (a pathological first-cycle push failure): the
  retry's own `git fetch` fails too — caught by the SAME outer non-fatal contract (REQ-703), no
  special-casing needed.
- **impl-review iter3 FIND-002**: the primary push throws, but by the time the retry's fetch+reset
  completes, the reconciled pending line count for both sources is zero (origin already has this
  cycle's content). No push call is issued in the retry branch; `result.pushed` is `false` for this
  cycle (never misreported `true`), even though the marker's reconciled `pushedLineCount` correctly
  reflects the now-current actual state via REQ-709's own unconditional reconciliation.
**Acceptance Criteria**:
- Deleting the ENTIRE dedicated publish-repo directory between two cycles (with the source ledger
  file untouched) results in the SECOND cycle publishing every source line exactly once, with no
  drops and no duplicates — proven against REAL git, not a mocked call sequence (impl-review iter2
  FIND-003: this is the actual reachable trigger, replacing the iter1 test's unrealistic
  outside-writer-on-the-same-exclusive-branch scenario).
- Given a first successful publish followed by an OUTSIDE process pushing an unrelated commit to
  `ledger-<instance>` (a genuine divergence, still covered as defense-in-depth even though it cannot
  occur from a same-topology writer), and then a second local cycle with new source lines that
  reaches the push threshold: the second cycle's `pushed` is `true`, a FRESH clone of the branch
  contains every id from BOTH cycles exactly once, and the outside process's commit is still present
  in history (never overwritten).
- `marker.<source>.pushedLineCount` after any cycle equals that source's ACTUAL, currently-confirmed
  published line count — never a value ahead of what a fresh clone of the branch would show.

## Non-Functional Requirements
- **Performance**: a disabled-flag cycle (the default) must add negligible overhead to the wake loop
  (no I/O at all — single env-var string comparison). An enabled cycle with genuinely nothing new to
  publish still performs a lock acquisition + a shallow `git fetch` (REQ-709's published-content-as-
  truth model requires syncing to actual origin state before knowing whether there is new work) —
  accepted cost, kept cheap by REQ-705's shallow/depth-capped clone (FIND-006).
- **Security**: never publishes `daemon.err`, `.env`, wallet files, the model-authored `args` object,
  or any field outside REQ-702's explicit per-source allowlists; free-text fields get REQ-706's
  two-layer redaction; the destination is two instance-scoped files (`<instance>-wake.jsonl`,
  `<instance>-earn.jsonl`) inside a DEDICATED clone, never a directory sweep, never the shared
  checkout.
- **Concurrency**: cross-instance concurrency is structurally impossible (REQ-705 — disjoint
  `publishRepoDir`/branch/`lockDir` per instance); same-instance overlap is guarded by REQ-708's
  mkdir-atomic lock. The shared checkout (`repoRoot`) is touched by AT MOST one read-only `git
  remote get-url origin` call per cycle — never written to, so it can never conflict with
  `evolve.mjs`'s `promote()` or any other writer of that checkout.
- **Verification readiness**: a persistently-broken publish pipeline is observable via
  `publishFailureStreak` (REQ-703/FIND-005), escalated to `harness-failures.jsonl` at 5 consecutive
  failures — never silent-forever on stderr alone.
