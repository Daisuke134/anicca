# Verification Architecture — anicca-agent-economy (Phase 1b)

**feature**: anicca-agent-economy · **mode**: strict · **increment**: same as
`behavioral-spec.md` (gig-board concurrency hardening / bootstrap-reserve catalog gate /
business.blockrun.ai seller-channel research) · **日付**: 2026-07-07

## Purity Boundary Map (file/function level)

| Layer | Location | Purity | Notes |
|---|---|---|---|
| **Pure Core** | `skills/economy/gig/lib/lock.mjs` — the staleness predicate (target: an isolable `(nowMs, mtimeMs, staleMs) → boolean` check, currently inlined in `acquire()`) | PURE | Must be directly unit-testable without touching the filesystem or real wall-clock sleeps (fake `nowMs`/`mtimeMs` injected). |
| **Pure Core** | `skills/economy/gig/lib/store.mjs` — `applyPost`/`applyTake`/`applyDeliver`/`applyVerifyAndPay`/`getGig`/`listGigs` | PURE (existing, unchanged) | Not touched by this increment; referenced here only because REQ-102's acceptance criteria depend on `gig.mjs` continuing to call these against a FRESH state object, never a stale one. |
| **Effectful Shell** | `skills/economy/gig/lib/lock.mjs` — `acquire()`/`release()`/`touch()`/`withGigLock()` (`fs.mkdir`, `fs.open('wx')`, `fs.stat`, `fs.unlink`, `fs.utimes`, `setInterval` heartbeat) | EFFECTFUL | Real filesystem + timer side effects; this is where REQ-101's atomicity/heartbeat behavior is actually enforced. |
| **Effectful Shell** | `skills/economy/gig/lib/persist.mjs` — `loadState`/`saveState` | EFFECTFUL | Full-file JSON read/write; REQ-102 is a property of WHEN this is called relative to the shared `"_board"` lock, not of this module's own logic. |
| **Effectful Shell** | `skills/economy/gig/gig.mjs` — `applyAndSave()`, `gigPost`/`gigTake`/`gigDeliver`/`gigVerifyAndPay` | EFFECTFUL (orchestration) | Combines the pure `store.mjs` transitions with lock + persistence + network settle (`lib/escrow.mjs`) + identity check (`lib/identity.mjs`); REQ-101/102's acceptance criteria are properties of THIS module's call ordering. |
| **Pure Core (new)** | new function, e.g. `runtime/loop/catalog-gate.mjs::filterCatalog(balanceUsdc, allSlotNames, riskTagOf, reserveThresholdUsdc) → string[]` | PURE (new) | Directly analogous to the existing `runtime/loop/tier.mjs::selectTier` — no I/O, deterministic, given already-fetched inputs. This is where REQ-201/202/203's acceptance criteria are enforced and unit-tested. |
| **Effectful Shell** | `runtime/loop/index.mjs` (registry read at ~L100-118, `fetchUsdcBalance` call at ~L190-196, wiring into `assembleContext`/`buildSystemPrompt`) | EFFECTFUL | Reads `skills/registry.json` from disk, reads balance over RPC, and threads the pure filter's output into the prompt; this increment adds one filtering step here, using the new pure function above. |
| **Config data (read, not inferred)** | `skills/registry.json` — a per-slot risk tag (e.g. `"risk": "capital"` / `"risk": "safe"`) | DATA, not code | A maintainer-set fact, not something the runtime infers from task content — this is what keeps REQ-203's "bookkeeping not judgment" constraint true: the classification of a SLOT as risky is a static, human-reviewed fact; only whether the CURRENT balance clears the threshold is computed at runtime. |
| **Not code** | REQ-301/302 research record | N/A | A static markdown artifact produced by a research/investigation process (external repo/site reads); no purity classification applies — verified structurally (Tier 0), not executed. |

## Verification tiers (this feature's convention, consistent with prior anicca-project VCSDD
features, e.g. `clip-post-verify-hardening/specs/verification-architecture.md`)

- **Tier 0**: structural/existence checks — no runtime execution required (a required section
  exists in a document; a data field exists in `registry.json`; a function's return shape has no
  disallowed field). Includes design-constraint checks that are verified by reading code, not by
  running it.
- **Tier 1**: pure-function unit tests — deterministic fixtures, no filesystem/network/real
  wall-clock sleep, fast (milliseconds).
- **Tier 2**: integration tests — real module wiring (real `fs`, injected small timing constants,
  concurrent `Promise.all` calls against the real lock/persist/gig modules) plus fresh-context
  adversary review of the disk artifacts (no live network required for this tier).
- **Tier 3**: live, no-mock E2E — real transactions against the live testnet (or, once graduated,
  mainnet) facilitator + ERC-8004 registry, executed the same way the round-1/2 adversary did
  (real concurrent calls, real on-chain reconciliation), per this project's HARD RULE 0.24
  (on-chain-verified only, no paper/simulated claims).

## Proof Obligations

| ID | REQ | Description | Tier | Required | Tool / Method |
|---|---|---|---|---|---|
| PROP-101a | REQ-101 | A live holder that heartbeats at interval `H` is NEVER stolen from, however long (past any fixed threshold) its critical section legitimately runs | 1 | true | unit test: inject tiny `staleMs`/`heartbeatMs`, start a long-running `fn()` inside `withGigLock`, attempt a concurrent second acquire on the same key mid-run, assert rejection throughout |
| PROP-101b | REQ-101 | A genuinely dead holder's lock (no heartbeat for ≥ `staleMs`) IS reclaimable by exactly one subsequent caller | 1 | true | unit test: create a lock file, backdate its mtime past `staleMs` (no live heartbeat running), assert exactly one of two concurrent reclaim attempts succeeds |
| PROP-101c | REQ-101 | Reclaim is atomic — no window where two callers both believe they hold the same key | 1/2 | true | unit test using the real `fs.open('wx')` primitive (not a mock) with two concurrent reclaim attempts on the same backdated lock file; Tier 2 repeats this under `Promise.all` with real fs timing jitter |
| PROP-101d | REQ-101 | Unrelated lock keys never contend with each other | 1 | true | unit test: two different lock keys acquired concurrently both succeed immediately |
| PROP-102a | REQ-102 | A slow operation on gig X does not clobber a concurrent, already-succeeded operation on unrelated gig Y | 2 | true | integration test: inject an artificially slow `pay`/settle for gig X's `verify_and_pay`, run it concurrently with a fast `gig_take` on gig Y, assert the FINAL persisted board reflects gig Y's take (not reverted to `'open'`) |
| PROP-102b | REQ-102 | Every write to the shared board file re-reads fresh from disk immediately before mutating, never reusing a snapshot captured before a slow step | 2 | true | integration test: assert the write path's `loadState` call happens AFTER the slow network step completes, not before it (call-order assertion, not just an outcome assertion) |
| PROP-102c | REQ-102 | The shared-file critical section is brief (local read-mutate-write only); the slow network/settle step does not hold the shared-file lock | 2 | true | integration test: assert an unrelated gigId's operation is not blocked for the duration of another gig's slow network step — only for the brief local write window |
| PROP-103a | REQ-103 | Existing round-1/2/3 fund-safety assertions remain green after this increment's lock/persist changes | 1/2 | true | run the full existing suite (`node --test __tests__/*.test.mjs`, dependencies installed) — 0 regressions in previously-passing assertions |
| PROP-103b | REQ-103 | A fresh adversary re-attack of the round-1 fail-open scenarios (self-verify, same-gig double-pay) still fails as designed | 2/3 | true | fresh-context Sonnet adversary re-runs the exact round-1/2 exploit scripts against the current code (disk review) and, where feasible, against a live/testnet deployment; expects rejection in every case |
| PROP-201a | REQ-201 | `filterCatalog` excludes every slot tagged capital-risking when `balanceUsdc < threshold` | 1 | true | unit test: fixed slot list with a mix of risk tags, balance strictly below threshold, assert output excludes exactly the risky-tagged slots |
| PROP-201b | REQ-201 | `filterCatalog` returns the full, unfiltered slot list when `balanceUsdc >= threshold` (boundary: equality counts as "at or above") | 1 | true | unit test: `balanceUsdc === threshold` exactly → full list; `balanceUsdc = threshold + epsilon` → full list |
| PROP-201c | REQ-201 | An unset/non-finite/negative threshold or balance input falls back to a safe, fail-closed default (gate never silently disabled) | 1 | true | unit test mirroring `tier.mjs`'s existing NaN/Infinity/negative test pattern (PROP-004 there) |
| PROP-201d | REQ-201 | A slot with no explicit risk tag defaults to capital-risking (excluded) while below threshold | 1 | true | unit test: slot present in the input list with no risk-tag entry, balance below threshold, assert it is excluded |
| PROP-201e | REQ-201 | The filter never returns an empty actionable set — meta/always-available slots survive filtering even in a pathological all-risky-tag input | 1 | true | unit test: every live slot tagged risky, balance below threshold, assert the designated always-available slot(s) remain in the output |
| PROP-202a | REQ-202 | The filter is a pure function of the CURRENT wake's balance only — no persisted state across calls | 1 | true | unit test: two successive calls with different balances (below then above threshold) on the SAME process/module state return the correct output for each call independently, with no leakage between calls |
| PROP-202b | REQ-202 | A balance transition from below to at/above threshold between two wakes restores the exact pre-restriction slot set on the very next wake | 1/2 | true | unit test at the pure-function level (PROP-201b already covers the pure case); Tier 2 integration test drives `runtime/loop/index.mjs`'s wiring across two simulated wakes with different fetched balances and asserts `activeSkillSlots`/`skillCatalog` match |
| PROP-203a | REQ-203 | The filter's return type carries no score/rank/preference field | 0 | true | structural/type check: return value is a plain array of strings (or equivalent minimal set), reviewed at Phase 3 |
| PROP-203b | REQ-203 | No prompt text generated by this increment recommends a specific remaining slot | 0 | true | Phase 3 adversary structural read of the diff to `runtime/loop/prompt.mjs` (if touched) confirming no added steering/ranking text, only the already-existing "you decide" framing |
| PROP-301a | REQ-301 | The research record exists under `evidence/` and contains all five required items (a)-(e) | 0 | true | structural check: file exists, each of (a)-(e) present as a distinct, evidenced section (not a bare unsupported claim) |
| PROP-301b | REQ-301 | Each factual claim in the record cites at least one piece of concrete evidence (file/line, quoted API response, PR state + timestamp, or an explicit "checked X, not found" statement) | 0 | true | Phase 3 adversary spot-checks a sample of claims against the cited evidence (re-fetch the PR/repo state, re-run any quoted command) |
| PROP-302a | REQ-302 | No code/process change in this increment introduces a dependency from the gig-board witness track onto REQ-301's completion | 0 | true | structural review: grep/read for any new gating condition referencing the research record's status in the witness runbook or gig-board code path — must find none |

## Verification Strategy

- **Tier 0** (no runtime execution): REQ-203's structural "no ranking field" check, REQ-301/302's
  research-record existence/citation/non-blocking checks.
- **Tier 1** (pure-function unit tests): REQ-101's staleness predicate and atomic-reclaim behavior
  in isolation, REQ-201/202's `filterCatalog` pure function (exhaustive branch coverage: below /
  at-boundary / above threshold; tagged-risky / tagged-safe / untagged; all-risky pathological
  case), REQ-103's baseline "existing suite stays green" check at the unit level.
- **Tier 2** (integration, real module wiring + fresh-context adversary disk review): REQ-102's
  cross-gigId shared-file race reproduction (the same technique the round-2/3 adversary already
  used — artificially slow one operation, run it concurrently with a fast unrelated one, assert the
  final persisted state), REQ-103's fresh adversary re-attack of the round-1 exploits against the
  current code, REQ-202's two-wake balance-transition wiring test through `index.mjs`.
- **Tier 3** (live, no-mock E2E against real/testnet chain state, HARD RULE 0.24): REQ-103's
  fresh-adversary re-attack extended to a LIVE re-run (real concurrent `verify_and_pay` calls
  against the live facilitator + real on-chain reconciliation), matching the exact method the
  round-1/2 verdict already used, so this increment's changes are proven not to reopen a real,
  on-chain fund-drain path — not merely a unit-test claim.

## Gate

Phase 3 (adversarial review) must confirm, via fresh-context, disk-only review plus (for PROP-102
and PROP-103) live/testnet re-execution: (1) REQ-101's heartbeat/atomicity properties hold under a
deliberately-induced "live but slow" scenario, not just a fast happy path; (2) REQ-102's shared-file
protection genuinely re-reads fresh state under a single, brief critical section — a control-flow
read of `gig.mjs`'s `applyAndSave`, not a grep for the word "lock"; (3) REQ-103's full existing test
suite is genuinely run (dependencies installed) and shows zero regressions, and the round-1 exploit
scripts are re-attempted live and still fail; (4) REQ-201/203's catalog filter is read end-to-end to
confirm it contains no scoring/ranking/preference logic anywhere in its diff, only a threshold
comparison and a set difference; (5) REQ-301's research record is spot-checked against the actual
current state of the referenced GitHub PR/repo and `business.blockrun.ai` surface, not taken at face
value.
