# Verification Architecture — franklin-ledger-push (P2)

## Changelog

- **impl-review iter3 fixes: FIND-001..003.** FIND-001a is REWRITTEN below (inverted invariant:
  `external`/`confirmed`/`fill_tid` are now PRESERVED, not dropped) and a new FIND-001d proof
  obligation adds the real-`isProfitable()` round-trip across all three chain paths (EVM/Solana/
  Hyperliquid). FIND-001b is updated for the new `sig` shape check. A new FIND-002d proof obligation
  covers the truthful-`pushed`-flag fix (no push issued in the retry ⇒ `pushed` stays `false`, never
  misreported `true`). See `specs/behavioral-spec.md`'s Changelog for the full per-FIND rationale.
- **impl-review iter1 redesign: FIND-001..005.** Proof obligations below are renumbered/rewritten
  from scratch against the redesigned `ledger-publish.mjs` (dedicated per-instance orphan publish
  clone, field-allowlist projection, push-confirmed cursor, mkdir-atomic same-instance lock,
  divergence recovery). PROP-701..710 in the pre-redesign version of this document no longer apply
  as written; see `specs/behavioral-spec.md`'s own Changelog for the REQ-level mapping.
- **impl-review iter2 fixes: FIND-001..006.** Dual-source publishing (wake + earn/money evidence,
  FIND-001), published-content-as-truth cursor reconciliation replacing the two-cursor
  (`copiedLineCount`/`pushedLineCount`) model (FIND-002), a realistic publish-repo-loss divergence
  test replacing the unrealistic outside-writer-on-an-exclusive-branch trigger (FIND-003), a
  corrected sibling-lock-precedent citation (FIND-004), a `publishFailureStreak` escalation counter
  + one-time reachability probe (FIND-005), and a shallow/depth-capped dedicated clone (FIND-006).
  New PROP rows below cover each fix; see `specs/behavioral-spec.md`'s Changelog for the full
  per-FIND rationale and evidence trail.

## Purity Boundary Map

- **Pure Core** (`runtime/loop/ledger-publish.mjs`, exported, no I/O):
  - `decidePublish({ pendingLineCount, lastPushTs, nowMs, minLines, minIntervalMs })` — throttle
    decision, deterministic truth table. Unchanged by either redesign.
  - `extractRecordId(line, idField)` / `extractWakeId(line)` / `extractEarnRef(line)` — JSON parse +
    field extraction, deterministic, never throws. `extractEarnRef` is FIND-001's new per-source id
    extractor (`wake` field, not `wake_id`, for the earn source).
  - `projectWakeLine(rawLine)` / `projectEarnLine(rawLine)` — FIND-001/003: per-source
    field-allowlist projections (renamed from the single `projectLedgerLine` — TWO distinct
    allowlists now exist since the wake and earn schemas are unrelated). Each parses one raw JSON
    line, returns a JSON string containing ONLY that source's type-checked allowlisted fields
    (REQ-702); returns `null` for malformed/non-object input. Structural parsing of a fixed machine
    format — not judgment (per `~/.claude/rules/building-effective-ai-agents.md`'s hard rule: this is
    a deterministic field-shape check, never a semantic classification).
  - `redactBroaderSecretPatterns(str)` — REQ-706's second redaction layer (base58 64-88 char runs,
    generic 40+ hex runs), applied to the free-text fields both projections allow through.
  - Reused: `redactPrivateKeyPatterns` (`env-filter.mjs`, unmodified, already formally covered by its
    own PROP-018/PROP-020).
- **Effectful Shell** (`runtime/loop/ledger-publish.mjs`, same file, I/O functions):
  - `readMarker`/`writeMarker` — fs read/write of `$ANICCA_HOME/state/.ledger-publish-marker`. FIND-
    002 REWRITE: the two-cursor (`copiedLineCount`/`pushedLineCount`) model is GONE. The marker now
    carries `{ wake: {pushedLineCount}, earn: {pushedLineCount}, lastPushTs, publishFailureStreak }`
    — a pure CACHE, never trusted as ground truth (see `reconcileSource` below).
  - `readLinesOrEmpty`/`appendRawLines`/`countLines` — fs read of a source or destination jsonl file
    (ENOENT → `[]`), fs append, line-count helper. Used both for the durable source ledgers
    (`ledgerPath`/`earnLedgerPath`) and for reading a destination file's ACTUAL current content.
  - `acquireLock`/`releaseLock` — REQ-708: mkdir-atomic lock at `$ANICCA_HOME/state/.ledger-publish-
    <instance>.lock`, pid-staleness reclaim (`process.kill(pid, 0)`), copied from
    `skills/self/claude-p-mainloop.sh`'s pidfile guard — the ONLY real sibling precedent in this repo
    (FIND-004: the previously-cited `scripts/disk-cleaner.sh` does not exist here).
  - `ensureReadme` — one-time `README.md` stub creation in the publish repo.
  - `checkOriginReachability` — FIND-005: one-time, non-fatal `git ls-remote` probe, invoked from
    inside `ensurePublishRepo`'s first-ever-clone branch (stateless — tied to `publishRepoDir/.git`
    not existing yet, never a global mutable flag).
  - `ensurePublishRepo` — REQ-705: idempotent dedicated, SHALLOW (`--depth 1 --single-branch
    --no-tags`, FIND-006) clone + orphan/tracking-branch setup. Every git call here runs with
    `cwd=publishRepoDir`; `repoRoot` is never passed to it. On the tracking path (`checkout -B branch
    origin/branch`) this ALSO syncs the working tree to origin's real tip — the precondition
    `reconcileSource` depends on. On the pre-first-push path it forces a deterministic, guaranteed-
    EMPTY state every call.
  - `reconcileSource` — FIND-002 (the core of this iteration's fix): derives ONE source's
    `pushedLineCount` for THIS cycle directly from the just-synced destination file's ACTUAL line
    count — never the marker. Both directions of drift (cached-too-high → healed down; cached-too-low
    → adopted up) collapse into this single unconditional reconciliation.
  - `appendAndCommit` — projects + appends both sources' new lines (with a `{}` placeholder for a
    malformed source line — REQ-702's 1:1 index-alignment rule that makes `reconcileSource` sound),
    then ONE path-scoped combined `git add`/`commit` covering whichever source(s) had new content.
    Its own try/catch (REQ-703) keeps a commit failure from ever reaching the outermost 'error' catch.
  - `defaultGit` — `child_process.execFileSync` wrapper (injectable via `opts.git`, mirrors
    `evolve.mjs:154-156`'s own `git()` helper).
  - `publishLedgerCycle` — orchestrator; sequences fs + lock + git calls for BOTH sources per
    REQ-701..709; the only exported function actually wired into `index.mjs`. On a push rejection it
    re-runs the SAME reconcile→append→commit body once more after a fetch+hard-reset (no separate
    bespoke `recoverFromDivergence` function anymore — the normal path already IS the recovery
    mechanism under the new published-content-as-truth model).
  - Wiring: `index.mjs`'s `while (!shuttingDown) { await runOneWake(); ... }` loop — one call per
    completed wake, wrapped in an additional try/catch at the call site (defense-in-depth on top of
    `publishLedgerCycle`'s own internal non-throwing contract), now also passing `earnLedgerPath`
    (via the already-imported `defaultEarnLedgerPath(config)`, FIND-001) and inspecting the returned
    `publishFailureStreak` to escalate via the EXISTING `appendHarnessFailure` at 5 consecutive
    failures (FIND-005, `kind: 'ledger_publish_stuck'`). `repoRoot` (the shared checkout) is passed
    through ONLY so `ensurePublishRepo` can resolve `git remote get-url origin` from it — no other
    git verb is ever run against it.

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-701 | `decidePublish`: `pendingLineCount<=0` → never push, any `nowMs`/`lastPushTs` | 1 | true | node:test |
| PROP-702 | `decidePublish`: `pendingLineCount>=minLines(10)` → always push regardless of elapsed time | 1 | true | node:test |
| PROP-703 | `decidePublish`: `pendingLineCount>0` and `nowMs-lastPushTs>=minIntervalMs(15min)` → push | 1 | true | node:test |
| PROP-704 | `decidePublish`: `0<pendingLineCount<10` and elapsed`<15min` → never push (`throttled`) | 1 | true | node:test |
| PROP-705 | `extractWakeId`/`extractEarnRef`: valid JSON with the source's own string id field → returns it verbatim; missing/malformed/non-JSON → `'unknown'`, never throws | 0 | true | node:test |
| PROP-706 | `projectWakeLine`: keeps every REQ-702-allowlisted wake field, drops the model-authored `args` object and any other unknown field | 1 | true | node:test |
| — | `projectWakeLine`: passes through `net_*`/`earn_*`/`cost_*` numeric fields, drops non-numeric values for the same keys | 1 | true | node:test |
| — | `projectWakeLine`: passes through a hash-shaped `tx`/`tx_hash`/`txHash` field, drops a non-hash-shaped value for the same keys | 1 | true | node:test |
| PROP-709 | `projectWakeLine`: two-layer redaction (`redactPrivateKeyPatterns` + `redactBroaderSecretPatterns`) on `result`/`skip_reason` catches a 64-hex `0x...` key, an 88-char base58 Solana-shaped run, AND a bare 40+-hex run; caps output at 200 chars | 1 | true | node:test |
| PROP-710 | `projectWakeLine`/`projectEarnLine`: returns `null` for malformed JSON or a non-object line (dropped, never published raw) | 0 | true | node:test |
| FIND-001a (rewritten, impl-review iter3) | `projectEarnLine`: keeps every REQ-702-allowlisted EARN field, NOW INCLUDING `external`/`confirmed`/`fill_tid` (type/shape-checked, never coerced) — drops ONLY fields truly outside the explicit list. Also asserts a non-boolean `external`/`confirmed` and a non-number/non-string `fill_tid` are still dropped (fail-closed) | 1 | true | node:test |
| FIND-001b (updated, impl-review iter3) | `projectEarnLine`: drops a non-hash-shaped `tx`; drops a `sig` that is the wrong length or contains a non-base58 character (FIND-003 shape check, not a bare length/type check); redacts+caps the free-text `task` field the same way `result`/`skip_reason` are redacted on the wake source | 1 | true | node:test |
| FIND-001c | End-to-end: a real earn-ledger line carrying `net_usdc`/`tx`/`sig` (the actual money-evidence schema, verified live against `record-swap.mjs`) is published, unredacted-by-shape, to `<instance>-earn.jsonl` on a fresh clone of the branch — restoring third-party balance-growth verifiability | 2 | true | node:test (real git, `file://` bare-repo fixture) |
| FIND-001d (new, impl-review iter3, critical) | `projectEarnLine` round-trip through the REAL imported `skills/_shared/lib/ledger.mjs::isProfitable()` (never a re-implementation of its rules): a profitable EVM line (`tx`+`status==='0x1'`), a profitable Solana line (`sig`+`confirmed`), and a profitable Hyperliquid line (`chain`+`fill_tid`+`confirmed`) — all with `external:true`/`net_usdc>0` — each still classify as `isProfitable(published_line) === true` after projection; a line with a wrong-typed `external`/`confirmed`/`fill_tid` has that field dropped, not coerced | 1 | true | node:test (imports the real `isProfitable`) |
| PROP-711 | `ensurePublishRepo` + `publishLedgerCycle` end-to-end: first-ever publish creates a DEDICATED clone on orphan branch `ledger-<instance>` against a real `file://` bare-repo fixture; the shared checkout's `HEAD`/`git status --porcelain` are byte-identical before/after; a fresh clone of the published branch contains ONLY `README.md` + `<instance>-wake.jsonl` + `<instance>-earn.jsonl` (whichever sources had content) | 2 | true | node:test (real git, `file://` bare-repo fixture — mirrors `evolve.test.mjs`'s established real-git-in-tmp-dir precedent) |
| PROP-712 (leak test, FIND-001/002) | A shared checkout seeded with an uncommitted dirty file AND a committed-but-unpushed commit is completely untouched (`HEAD`, `status --porcelain`, current branch, origin's `main` ref all identical before/after) by a publish cycle that DOES successfully push to its own dedicated branch | 2 | true | node:test (real git, `file://` bare-repo fixture) |
| PROP-713 | `acquireLock`: a lock directory pre-seeded with this test process's own live pid causes the cycle to return `reason:'locked'` and create no `publishRepoDir` | 1 | true | node:test |
| PROP-714 | `acquireLock`: a lock directory pre-seeded with an astronomically-unlikely-to-be-alive pid is reclaimed; the cycle proceeds normally and the lock directory is gone again once the cycle returns | 1 | true | node:test |
| FIND-002/003 | **The realistic trigger, replacing PROP-715's old outside-writer test**: cycle 1 has EVERY `push` attempt fail (primary + retry, simulating a network outage — nothing ever reaches origin); the ENTIRE `publishRepoDir` is then deleted between cycles; cycle 2 runs with real git throughout and must still publish every source line exactly once, no drops/dups, proven against a fresh clone | 2 | true | node:test (real git, `file://` bare-repo fixture, publish-repo-loss is the actual reachable trigger in this single-writer-per-branch topology) |
| PROP-715 | Divergence defense-in-depth (still covered even though REQ-705 makes it structurally impossible from a same-topology writer): after a first successful publish, an OUTSIDE clone pushes a divergent commit to the SAME published branch; a second local cycle with new source lines whose push is thereby rejected still ends with `pushed:true`, a fresh clone containing every `wake_id` from both cycles exactly once (no dup/no drop), and the outside commit preserved in history | 2 | true | node:test (real git, `file://` bare-repo fixture) |
| PROP-716 | Non-fatality: a persistently-failing `push` (the primary attempt AND the retry both throw, simulating a network outage rather than a genuine divergence) never throws out of `publishLedgerCycle`; `marker.wake.pushedLineCount` stays at its last-confirmed value for the next cycle to retry; `publishFailureStreak` increments | 1 | true | node:test (hybrid: real git for setup/commit, injected `git` that always throws on `push`) |
| FIND-002d (new, impl-review iter3, major) | Truthful `pushed` flag: the primary `git push` call actually lands on origin but the client observes a failure (phantom success); the retry's post-reset reconcile finds nothing pending, so it issues NO `git push` call — `result.pushed` must be `false` (never misreported `true`) and exactly ONE total `push` call is ever made across the whole cycle | 1 | true | node:test (real git, `file://` bare-repo fixture — a wrapper that actually executes the push then throws) |
| PROP-717 | Non-fatality: `git remote get-url origin` failure and publish-repo `clone` failure each independently resolve to `reason:'setup-failed'` without throwing and without creating the destination file | 1 | true | node:test (injected mock `git`) |
| PROP-718 | REQ-703/707: a commit failure is caught in `appendAndCommit`'s own try/catch (never the generic outer `'error'` reason), `pushedLineCount` is not advanced past it, and the NEXT cycle (real git) recovers cleanly with no duplication | 1 | true | node:test (hybrid git: real for everything except `commit`) |
| FIND-005a | `publishFailureStreak` accumulates across 5 consecutive setup failures (`result.publishFailureStreak === 5`) and resets to `0` the moment the next cycle's setup succeeds | 1 | true | node:test (mock git for the failures, real git for the recovery) |
| FIND-005b | A failing `ls-remote` reachability probe at first-ever setup logs a message containing neither the origin URL's credentials nor any `ghp_`/`gho_`/`github_pat_`-shaped token, never blocks the cycle, and is invoked at most once per dedicated-clone lifetime (not re-run on a second cycle against the same already-cloned `publishRepoDir`) | 1 | true | node:test (hybrid git: real except `ls-remote`, then a call-counting real-git wrapper across 2 cycles) |
| FIND-006 | `ensurePublishRepo`'s clone produces a shallow repo (`.git/shallow` present) that stays shallow (still present) after a second fetch/push cycle | 1 | true | node:test (real git, `file://` bare-repo fixture) |

## Verification Strategy

- **Tier 0**: pure parsing/gating with no meaningful edge-case surface beyond input-domain enumeration
  (`extractWakeId`/`extractEarnRef`, `projectWakeLine`/`projectEarnLine`'s malformed-input branch,
  default-OFF flag resolution) —
  direct example-based `node:test` assertions are sufficient and match this codebase's existing
  convention (no formal-methods tooling — Kani/Hypothesis — is present anywhere in `runtime/loop/`).
- **Tier 1**: the throttle decision (`decidePublish`), the per-source field-allowlist projections
  (`projectWakeLine`/`projectEarnLine`'s per-field type checks), the two-layer redaction, and the lock's
  staleness-reclaim logic get exhaustive boundary-value `node:test` coverage (every `>=`/`<` edge
  named in behavioral-spec.md REQ-704/706/708 gets its own test case) plus injected-failure-mode
  coverage (mock `git` functions that throw at specific call sites) — this is the repo's established
  substitute for property-based testing in this package (no `fast-check`/`hypothesis` dependency
  declared in `runtime/loop/package.json`; introducing one is out of scope for a LEAN feature and
  would itself need its own spec justification).
- **Tier 2**: the structural safety claims that impl-review iteration 1 found were NOT actually
  reachable-scenario-tested (FIND-004) — the leak test, the dedicated-orphan-branch setup, and the
  divergence-recovery flow — are verified against REAL git operating on a throwaway `file://`
  bare-repo fixture (never a mocked git-call-sequence assertion for these three; a mock cannot prove
  "the shared checkout's HEAD is unchanged" or "a real non-fast-forward push is actually rejected
  and actually recovered" the way a real git process against a real (if disposable) remote can).
  This directly follows `evolve.mjs`'s OWN established repo precedent (`skills/earn/lib/__tests__/
  evolve.test.mjs` already does real `git init`/`commit`/`show` in a tmp dir for its own
  money-adjacent auto-commit path) — this feature extends that same precedent one step further (real
  `git clone`/`push`/`fetch`/`reset --hard` against a real bare-repo remote) because FIND-001/002/005
  are specifically about REMOTE-facing behavior a local-tmp-dir-only test cannot exercise.
- **Tier 3**: not applicable — no cryptographic, numeric-precision, or safety-critical money-moving
  logic in this feature (it copies already-written, already-redacted evidence; it never signs a
  transaction or moves funds). The redesign's own "never touch the shared checkout" and "never drop
  a line on divergence" invariants are the closest thing to a safety property this feature has, and
  both are covered at Tier 2 (real-git, reachable-scenario tests) rather than requiring a strong
  formal-methods tool — consistent with `evolve.mjs`'s own precedent for this class of effectful
  git-wrapping code in this repo.
