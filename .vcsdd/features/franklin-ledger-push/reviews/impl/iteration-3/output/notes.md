# impl-review iteration 3 — fresh-context adversary notes

Reviewed commit: 814a9de8 (worktree `/Users/operator/anicca/.worktrees/ledger-push`).
External test evidence accepted as reported by thinker: 216/217 (the 1 failure is the pre-existing,
previously-reproduced-on-baseline integration.test.mjs PROP-021 ENOTEMPTY /tmp teardown race,
unrelated to this feature); ledger-publish's own 34/34 pass.

## iteration-2 findings disposition (re-verified independently, fresh-context)

- **FIND-001 (money evidence never published)**: PARTIALLY KILLED, REOPENED IN NARROWER FORM. The
  gross bug (only `state/ledger.jsonl` ever read, `earn-ledger.jsonl` never touched at all) is
  genuinely fixed -- `publishLedgerCycle()` now reads both sources and dollar fields
  (`net_usdc`/`earn_usdc`/`cost_usdc`) plus `tx`/`sig` do reach the published `<instance>-earn.jsonl`
  (confirmed live: `runtime/loop/__tests__/ledger-publish.test.mjs:340-343`, a real-git end-to-end
  test that clones the published branch and asserts `net_usdc`). However, the FIX is incomplete
  relative to the feature's own stated purpose: `isProfitable()` (`skills/_shared/lib/ledger.mjs:51-64`),
  the repo's single source of truth for "is this a real, GATE-0 profitable earn," cannot be run
  against the published data at all, because `external`/`confirmed`/`fill_tid` are dropped by
  `projectEarnField()`. See this iteration's FIND-001 (new numbering, same class of bug).
- **FIND-002 (silent gap: lost publish-repo dir + rejection-only recovery)**: KILLED for the specific
  reachable trigger. Walked the crash matrix fresh:
  - Publish-repo directory deleted between cycles -> `ensurePublishRepo()` re-clones + fetches +
    either syncs to origin's real tip or forces a guaranteed-empty orphan state; `reconcileSource()`
    then re-derives `pushedLineCount` from the ACTUAL just-synced destination file, never the marker.
    Source lines are always re-read fresh from the durable `ledgerPath`/`earnLedgerPath` at the top
    of `publishLedgerCycle()`, so nothing is lost -- verified against the real test
    (`ledger-publish.test.mjs:495-533`, real git, asserts all 12 `wake_id`s present exactly once).
  - Genuine push rejection (real divergence) -> fetch + `reset --hard origin/branch` + re-run the same
    reconcile/append/commit body once, then retry the push once. Verified real-git test
    (`ledger-publish.test.mjs:535-567`) that an outside writer's divergent commit is preserved (not
    force-overwritten) and every `wake_id` from both cycles lands exactly once.
  - Destination file manually edited on origin by an outside process (fail-safe under the
    "trust actual line count" model): traced this specifically. If an outside writer touched a
    DIFFERENT file on the same branch (the only realistic scenario given REQ-705's single-writer-
    per-instance/per-branch guarantee, and what the divergence test actually exercises), reconciliation
    is unaffected -- `countLines()` only reads our own destination file. If an outside writer somehow
    appended/edited LINES INSIDE our OWN destination file directly (not exercised by any test, and
    explicitly outside the topology REQ-705 claims to guarantee), the "actual line count = ground
    truth" model would misattribute the count and could silently mis-slice `sourceLines`, but this is
    consistent with the spec's own explicitly-stated scope boundary (REQ-705's single-writer guarantee)
    and I did not find evidence it is reachable in this codebase's actual topology -- not raised as a
    blocking finding, noted here for completeness only.
  - New sub-bug found in the retry path unrelated to FIND-002's original scope: see FIND-002 (this
    iteration) -- `pushed = true` is set unconditionally after the retry's try block regardless of
    whether `git push` actually ran (only called `if (result.pendingLineCount > 0)`).
- **FIND-003 (unrealistic divergence test)**: KILLED. The divergence suite now covers BOTH the
  realistic trigger (publish-repo dir loss, `test:495-533`) AND the defense-in-depth outside-writer
  scenario (`test:535-567`), correctly labeled as such in both the spec and the test file's own
  comments.
- **FIND-004 (hallucinated `scripts/disk-cleaner.sh` citation)**: KILLED. Confirmed
  `skills/self/claude-p-mainloop.sh:7-9,48,55` is a real file with the described pidfile-guard
  ("NOT flock -- macOS has no flock(1) binary") idiom; the citation in both the code comment and the
  spec now points here instead.
- **FIND-005 (no escalation, no reachability probe)**: KILLED. `publishFailureStreak` is tracked,
  reset only on `ensurePublishRepo()` success, returned to the caller, and `index.mjs`'s wiring
  (`index.mjs:362-386`) escalates via the EXISTING `appendHarnessFailure` mechanism at streak>=5 --
  confirmed this call site sits in the effectful shell (the main `while` loop, outside `runOneWake()`),
  so it does not violate the purity boundary map. `checkOriginReachability()` is confirmed invoked
  exactly once, gated on `publishRepoDir/.git` not yet existing (test:648-665).
- **FIND-006 (unbounded clone)**: KILLED. `--depth 1 --single-branch --no-tags` clone + depth-capped
  explicit-refspec fetches confirmed by a real-git test asserting `.git/shallow` persists across a
  second cycle (test:350-365).

## New-risk scan of the rewrite (per task instructions)

- **`{}` placeholder lines**: confirmed these DO get published (committed + pushed) to the public
  branch when a source line is malformed/non-object JSON. This is intentional and necessary --
  REQ-702's own edge-case text documents this as the mechanism that keeps `reconcileSource()`'s
  line-count-based reconciliation 1:1-sound. A malformed source line is a rare/pathological case (a
  torn write, corrupted append); the `{}` line is harmless noise on the branch, not a correctness bug.
  No finding raised for this -- verified as working-as-designed.
- **`reconcileSource` reading the destination file every cycle**: fine on performance (small files,
  shallow clone); this is REQ-709's explicit unconditional-reconciliation design and is not a new risk.
- **Escalation wiring purity**: verified `appendHarnessFailure` call site and `publishLedgerCycle` call
  site both live in `index.mjs`'s effectful main loop, never inside `runOneWake()` or any pure function
  -- no purity-boundary violation.
- **`ensurePublishRepo`'s `checkout -B branch origin/branch` on every cycle**: traced whether this
  discards a prior cycle's THROTTLED (committed-but-not-yet-pushed) local commit. It does discard the
  local git commit object every cycle regardless of throttle state, but NOT the underlying data --
  because `wakeSourceLines`/`earnSourceLines` are always re-read fresh from the durable source ledgers
  (never from a "locally committed" cursor) and `reconcileSource()` re-derives `newLines` from
  post-reset actual state, the same (or a larger, since the source may have grown) batch is
  recommitted from scratch next cycle. No data loss traced; this does mean REQ-704's own prose
  ("local (non-push) commits happen every cycle... independent of this throttle", behavioral-spec.md:
  192-193) is misleading about persistence semantics -- local commits are effectively REPLACED, not
  accumulated, across throttled cycles -- but this is a documentation-precision note, not a blocking
  functional bug, so not raised as a standalone finding.

## Test integrity spot-check

- Divergence test (`FIND-002/FIND-003`, test:495-533) and the outside-writer test (test:535-567): both
  use REAL git against `file://` bare-repo fixtures, assert against a FRESH clone of the published
  branch (not an in-process mock), and check both "no drop" and "no duplicate" -- not tautological.
- Earn-projection tests (test:214-245): real assertions against `JSON.parse(projectEarnLine(...))`
  output; FIND-001 (this iteration) shows what these tests are missing, not that they're fake.
- Leak test (test:369-404): still present post-rewrite, real git, asserts HEAD/status/branch/origin-
  main byte-identical before/after -- confirmed genuine (not simplified/weakened by the rewrite).
- Total test count: 34 `test(...)` blocks counted directly in `ledger-publish.test.mjs`, matching the
  manifest's claimed count.
