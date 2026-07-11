# Verification Architecture — franklin-ledger-push (P2)

## Changelog

- **impl-review iter1 redesign: FIND-001..005.** Proof obligations below are renumbered/rewritten
  from scratch against the redesigned `ledger-publish.mjs` (dedicated per-instance orphan publish
  clone, field-allowlist projection, push-confirmed cursor, mkdir-atomic same-instance lock,
  divergence recovery). PROP-701..710 in the pre-redesign version of this document no longer apply
  as written; see `specs/behavioral-spec.md`'s own Changelog for the REQ-level mapping.

## Purity Boundary Map

- **Pure Core** (`runtime/loop/ledger-publish.mjs`, exported, no I/O):
  - `decidePublish({ pendingLineCount, lastPushTs, nowMs, minLines, minIntervalMs })` — throttle
    decision, deterministic truth table. Unchanged by the redesign.
  - `extractWakeId(line)` — JSON parse + field extraction, deterministic, never throws. Unchanged.
  - `projectLedgerLine(rawLine)` — FIND-003: field-allowlist projection. Parses one raw JSON line,
    returns a JSON string containing ONLY the type-checked allowlisted fields (REQ-702's list);
    returns `null` for malformed/non-object input. Structural parsing of a fixed machine format —
    not judgment (per `~/.claude/rules/building-effective-ai-agents.md`'s hard rule: this is a
    deterministic field-shape check, never a semantic classification).
  - `redactBroaderSecretPatterns(str)` — REQ-706's second redaction layer (base58 64-88 char runs,
    generic 40+ hex runs), applied only to the free-text fields `projectLedgerLine()` allows through.
  - Reused: `redactPrivateKeyPatterns` (`env-filter.mjs`, unmodified, already formally covered by its
    own PROP-018/PROP-020).
- **Effectful Shell** (`runtime/loop/ledger-publish.mjs`, same file, I/O functions):
  - `readMarker`/`writeMarker` — fs read/write of `$ANICCA_HOME/state/.ledger-publish-marker`, now
    carrying two cursors (`copiedLineCount`, `pushedLineCount`) plus `pendingLinesSincePush`/
    `lastPushTs`.
  - `readSourceLinesRaw`/`appendRawLines` — fs read of source `ledger.jsonl`, fs append to
    `<publishRepoDir>/<instance>.jsonl`.
  - `acquireLock`/`releaseLock` — REQ-708: mkdir-atomic lock at `$ANICCA_HOME/state/.ledger-publish-
    <instance>.lock`, pid-staleness reclaim (`process.kill(pid, 0)`), copied from
    `skills/self/claude-p-mainloop.sh` (pidfile) + `scripts/disk-cleaner.sh` (mkdir-atomic lock) —
    the established idiom for "no `flock(1)` on macOS" already live in this repo.
  - `ensureReadme` — one-time `README.md` stub creation in the publish repo.
  - `ensurePublishRepo` — REQ-705: idempotent dedicated-clone + orphan/tracking-branch setup. Every
    git call here runs with `cwd=publishRepoDir`; `repoRoot` is never passed to it.
  - `recoverFromDivergence` — REQ-709: fetch + hard-reset + re-project-from-`pushedLineCount` +
    recommit + retry-push-once, on a rejected push.
  - `defaultGit` — `child_process.execFileSync` wrapper (injectable via `opts.git`, mirrors
    `evolve.mjs:154-156`'s own `git()` helper).
  - `publishLedgerCycle` — orchestrator; sequences fs + lock + git calls per REQ-701..709; the only
    exported function actually wired into `index.mjs`.
  - Wiring: `index.mjs`'s `while (!shuttingDown) { await runOneWake(); ... }` loop — one call per
    completed wake, wrapped in an additional try/catch at the call site (defense-in-depth on top of
    `publishLedgerCycle`'s own internal non-throwing contract). `repoRoot` (the shared checkout) is
    passed through ONLY so `ensurePublishRepo` can resolve `git remote get-url origin` from it — no
    other git verb is ever run against it.

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-701 | `decidePublish`: `pendingLineCount<=0` → never push, any `nowMs`/`lastPushTs` | 1 | true | node:test |
| PROP-702 | `decidePublish`: `pendingLineCount>=minLines(10)` → always push regardless of elapsed time | 1 | true | node:test |
| PROP-703 | `decidePublish`: `pendingLineCount>0` and `nowMs-lastPushTs>=minIntervalMs(15min)` → push | 1 | true | node:test |
| PROP-704 | `decidePublish`: `0<pendingLineCount<10` and elapsed`<15min` → never push (`throttled`) | 1 | true | node:test |
| PROP-705 | `extractWakeId`: valid JSON with string `wake_id` → returns it verbatim; missing/malformed/non-JSON → `'unknown'`, never throws | 0 | true | node:test |
| PROP-706 | `projectLedgerLine`: keeps every REQ-702-allowlisted field, drops the model-authored `args` object and any other unknown field | 1 | true | node:test |
| PROP-707 | `projectLedgerLine`: passes through `net_*`/`earn_*`/`cost_*` numeric fields, drops non-numeric values for the same keys | 1 | true | node:test |
| PROP-708 | `projectLedgerLine`: passes through a hash-shaped `tx`/`tx_hash`/`txHash` field, drops a non-hash-shaped value for the same keys | 1 | true | node:test |
| PROP-709 | `projectLedgerLine`: two-layer redaction (`redactPrivateKeyPatterns` + `redactBroaderSecretPatterns`) on `result`/`skip_reason` catches a 64-hex `0x...` key, an 88-char base58 Solana-shaped run, AND a bare 40+-hex run; caps output at 200 chars | 1 | true | node:test |
| PROP-710 | `projectLedgerLine`: returns `null` for malformed JSON or a non-object line (dropped, never published raw) | 0 | true | node:test |
| PROP-711 | `ensurePublishRepo` + `publishLedgerCycle` end-to-end: first-ever publish creates a DEDICATED clone on orphan branch `ledger-<instance>` against a real `file://` bare-repo fixture; the shared checkout's `HEAD`/`git status --porcelain` are byte-identical before/after; a fresh clone of the published branch contains ONLY `README.md` + `<instance>.jsonl` | 2 | true | node:test (real git, `file://` bare-repo fixture — mirrors `evolve.test.mjs`'s established real-git-in-tmp-dir precedent) |
| PROP-712 (leak test, FIND-001/002) | A shared checkout seeded with an uncommitted dirty file AND a committed-but-unpushed commit is completely untouched (`HEAD`, `status --porcelain`, current branch, origin's `main` ref all identical before/after) by a publish cycle that DOES successfully push to its own dedicated branch | 2 | true | node:test (real git, `file://` bare-repo fixture) |
| PROP-713 | `acquireLock`: a lock directory pre-seeded with this test process's own live pid causes the cycle to return `reason:'locked'` and create no `publishRepoDir` | 1 | true | node:test |
| PROP-714 | `acquireLock`: a lock directory pre-seeded with an astronomically-unlikely-to-be-alive pid is reclaimed; the cycle proceeds normally and the lock directory is gone again once the cycle returns | 1 | true | node:test |
| PROP-715 | `recoverFromDivergence` end-to-end: after a first successful publish, an OUTSIDE clone pushes a divergent commit to the SAME published branch; a second local cycle with new source lines whose push is thereby rejected still ends with `pushed:true`, a fresh clone containing every `wake_id` from both cycles exactly once (no dup/no drop), and the outside commit preserved in history | 2 | true | node:test (real git, `file://` bare-repo fixture, simulates the real divergence scenario, not a mocked git call sequence) |
| PROP-716 | Non-fatality: a persistently-failing `push` (the primary attempt AND the recovery's own retry both throw, simulating a network outage rather than a genuine divergence) never throws out of `publishLedgerCycle`; `marker.pendingLinesSincePush` stays `>0` and `marker.pushedLineCount` stays at its last-confirmed value for the next cycle to retry | 1 | true | node:test (hybrid: real git for setup/commit, injected `git` that always throws on `push`) |
| PROP-717 | Non-fatality: `git remote get-url origin` failure and publish-repo `clone` failure each independently resolve to `reason:'setup-failed'` without throwing and without creating the destination file | 1 | true | node:test (injected mock `git`) |
| PROP-718 | Idempotent cursor: two consecutive `publishLedgerCycle()` calls where the FIRST call's injected `git` throws specifically on `commit` — the SECOND call's destination-file content contains the source line exactly once, and reports `reason:'no-new-lines'` (the cursor already advanced past it in cycle 1) | 1 | true | node:test (hybrid git: real for everything except `commit`) |

## Verification Strategy

- **Tier 0**: pure parsing/gating with no meaningful edge-case surface beyond input-domain enumeration
  (`extractWakeId`, `projectLedgerLine`'s malformed-input branch, default-OFF flag resolution) —
  direct example-based `node:test` assertions are sufficient and match this codebase's existing
  convention (no formal-methods tooling — Kani/Hypothesis — is present anywhere in `runtime/loop/`).
- **Tier 1**: the throttle decision (`decidePublish`), the field-allowlist projection
  (`projectLedgerLine`'s per-field type checks), the two-layer redaction, and the lock's
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
