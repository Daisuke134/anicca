# Verification Architecture — anicca-agent-economy (Phase 1b)

**feature**: anicca-agent-economy · **mode**: strict · **increment**: same as
`behavioral-spec.md` (gig-board concurrency hardening / bootstrap-reserve catalog gate /
business.blockrun.ai seller-channel research) · **日付**: 2026-07-07 · **revision**: iteration 4
(Phase 1c adversary review iteration 1 returned FAIL with 6 findings, resolved by iteration 2;
iteration 2 review returned FAIL with 2 CRITICAL findings, FIND-101/FIND-102, resolved by iteration
3; iteration 3 review returned FAIL with 1 HIGH finding, FIND-201 — this revision resolves it; see
`reviews/spec/iteration-1/output/findings/FIND-00{1..6}.json`,
`reviews/spec/iteration-2/output/findings/FIND-10{1,2}.json`, and
`reviews/spec/iteration-3/output/findings/FIND-201.json`)

## Purity Boundary Map (file/function level)

| Layer | Location | Purity | Notes |
|---|---|---|---|
| **Pure Core** | `skills/economy/gig/lib/lock.mjs` — the staleness predicate, target signature `isLockStale(nowMs, mtimeMs, staleMs) → boolean`, currently inlined in `acquire()` as `Date.now() - stat.mtimeMs > staleMs` | PURE (target — extraction is a BINDING acceptance criterion of REQ-101, not just a design aspiration; resolves FIND-004) | Directly unit-testable without touching the filesystem or real wall-clock sleeps (fake `nowMs`/`mtimeMs` injected) **once extracted**. Until the extraction lands, this predicate is only exercised indirectly through `acquire()`'s real-fs/real-timer tests (`skills/economy/gig/__tests__/lock.test.mjs`, all 3 tests currently use real `setTimeout`/`fs.utimes` against a real temp lock file) — that existing test file is Tier 2 integration coverage of the predicate's effect, NOT a Tier 1 pure-function test of the predicate itself. Phase 2 of this increment MUST perform the extraction and add direct Tier-1 unit tests against the exported `isLockStale` function before PROP-101a/b/d may be marked Tier 1 in fact. |
| **Pure Core** | `skills/economy/gig/lib/store.mjs` — `applyPost`/`applyTake`/`applyDeliver`/`applyVerifyAndPay`/`getGig`/`listGigs` | PURE (existing, unchanged) | Not touched by this increment; referenced here only because REQ-102's acceptance criteria depend on `gig.mjs` continuing to call these against a FRESH state object, never a stale one. |
| **Effectful Shell** | `skills/economy/gig/lib/lock.mjs` — `acquire()`/`release()`/`touch()`/`withGigLock()` (`fs.mkdir`, `fs.open('wx')`, `fs.stat`, `fs.unlink`, `fs.utimes`, `setInterval` heartbeat) | EFFECTFUL | Real filesystem + timer side effects; this is where REQ-101's atomicity/heartbeat behavior is actually enforced. `acquire()` calls the extracted `isLockStale` pure predicate instead of re-implementing the comparison inline. |
| **Effectful Shell** | `skills/economy/gig/lib/persist.mjs` — `loadState`/`saveState` | EFFECTFUL | Full-file JSON read/write; REQ-102 is a property of WHEN this is called relative to the shared `"_board"` lock, not of this module's own logic. |
| **Effectful Shell** | `skills/economy/gig/gig.mjs` — `applyAndSave()`, `gigPost`/`gigTake`/`gigDeliver`/`gigVerifyAndPay` | EFFECTFUL (orchestration) | Combines the pure `store.mjs` transitions with lock + persistence + network settle (`lib/escrow.mjs`) + identity check (`lib/identity.mjs`); REQ-101/102's acceptance criteria are properties of THIS module's call ordering. |
| **Pure Core (new)** | new function, e.g. `runtime/loop/catalog-gate.mjs::filterCatalog({ balanceUsdc, allSlotNames, riskTagOf, alwaysAvailableOf, hasOpenRiskPositionOf, reserveThresholdUsdc }) → string[]` | PURE (new) | Directly analogous to the existing `runtime/loop/tier.mjs::selectTier` — no I/O, deterministic, given already-fetched bookkeeping inputs. Takes THREE independent per-slot bookkeeping signals (risk tag, always-available flag, open-position fact), not one — see behavioral-spec.md REQ-201 for why each is a bookkeeping fact, not judgment (resolves FIND-002 and FIND-003). `hasOpenRiskPositionOf` is passed in as an already-RESOLVED, synchronous `(slotName) → boolean` value — `filterCatalog` only ever calls whatever function it is given, so it stays pure and Tier 1 regardless of how expensive the REAL implementation of that function is upstream (see the `index.mjs` row below; resolves FIND-102's purity-classification half). This is where REQ-201/202/203/204's acceptance criteria are enforced and unit-tested. |
| **Effectful Shell** | `runtime/loop/index.mjs` (registry read at ~L100-118, `fetchUsdcBalance` call at ~L190-196, resolving BOTH `hasOpenRiskPositionOf` mechanisms, wiring into `assembleContext`/`buildSystemPrompt`) | EFFECTFUL | Reads `skills/registry.json` from disk (including the per-slot `risk`/`alwaysAvailable` fields — see the classification table in behavioral-spec.md REQ-201), reads balance over RPC, and resolves open-position bookkeeping as TWO DIFFERENT mechanisms, not one (iteration-2's "reads already-fetched position data" claim was true for only one of them — resolves FIND-102): (a) `hasOpenRiskPositionOf('yield')` reads the SAME already-fetched ledger scan that already populates `ctx.positionsSummary` (`recentLedger.slice().reverse().find(l => String(l.source||'').startsWith('yield') && l.tx)`) — genuinely no new I/O, computed unconditionally every wake exactly as it is today; (b) `hasOpenRiskPositionOf('hl_trade')` is a NEW, lazy, effectful Hyperliquid `clearinghouseState`-backed query (reusing the same primitive `skills/earn/hl-trade/hl.py account` already calls), invoked ONLY when `balanceUsdc < BOOTSTRAP_RESERVE_USDC` for the current wake, defaulting to `true` on failure/timeout/unreachability — this is genuinely NEW effectful-shell surface this increment adds, not a reuse of existing data. Both are resolved to plain booleans here, BEFORE the pure `filterCatalog` above is called. |
| **Config data (read, not inferred)** | `skills/registry.json` — a per-slot risk tag (`"risk": "capital"` / `"risk": "safe"`) AND a per-slot `"alwaysAvailable": true` flag (set on `report` and `cook`) | DATA, not code | A maintainer-set fact, not something the runtime infers from task content — this is what keeps REQ-203's "bookkeeping not judgment" constraint true: the classification of a SLOT as risky, or as always-available, is a static, human-reviewed fact; only whether the CURRENT balance clears the threshold, and whether the instance currently holds an open position, are computed at runtime from already-fetched (`yield`) or newly-and-lazily-fetched (`hl_trade`) data. **Phase 2 MUST write an explicit `risk`/`alwaysAvailable` value for all 17 slots currently `status: "live"` in this file (see behavioral-spec.md REQ-201's classification table) — the untagged-defaults-to-risky rule is a forward-compatibility net for future slots, never a substitute for classifying today's slots (resolves FIND-101).** |
| **Prompt string-literal edit** | `runtime/loop/prompt.mjs::buildSystemPrompt` — the existing `## ★COLONY BOOTSTRAP PRIORITY★` block (lines ~89-96 as of 2026-07-07), the "Prefer this over re-yielding surplus" / "it is almost never 'yield again'" ranking phrases, AND — resolves FIND-201 — "the highest-leverage move is to POST" (the `economy/gig` bullet inside `## Your earn tools`, lines ~70-76), plus any other ranking/imperative language found anywhere within the block or the paragraph(s) it references | N/A (hardcoded string literal, not computed) | **Baseline correction (resolves FIND-005): this file's CURRENT baseline is NOT a neutral "you decide" framing.** It already contains an imperative steering block ("your FIRST action this wake MUST be economy/gig ... Do this BEFORE hl_trade / yield / anything else") that predates this increment, AND a separate ranking phrase in the same `economy/gig` bullet ("the highest-leverage move is to POST") that is not textually inside the `★COLONY BOOTSTRAP PRIORITY★` block itself but is functionally identical steering (FIND-201). REQ-204 requires this increment to remove/neutralize ALL of this, generalized to the whole block plus any paragraph it references, precisely because REQ-201/202's new bookkeeping gate is the design-compliant successor to it. Verified structurally (Tier 0: full-file read, not diff-only), never by a runtime assertion. |
| **Not code** | REQ-301/302 research record | N/A | A static markdown artifact produced by a research/investigation process (external repo/site reads); no purity classification applies — verified structurally (Tier 0), not executed. |

## Verification tiers (this feature's convention, consistent with prior anicca-project VCSDD
features, e.g. `clip-post-verify-hardening/specs/verification-architecture.md`)

- **Tier 0**: structural/existence checks — no runtime execution required (a required section
  exists in a document; a data field exists in `registry.json`; a function's return shape has no
  disallowed field; a string-literal block has been removed from a source file). Includes
  design-constraint checks that are verified by reading code, not by running it.
- **Tier 1**: pure-function unit tests — deterministic fixtures, no filesystem/network/real
  wall-clock sleep, fast (milliseconds). For REQ-101's staleness predicate specifically, Tier 1
  status requires the `isLockStale(nowMs, mtimeMs, staleMs)` extraction described in the Purity
  Boundary Map above to have actually landed; a test that only drives the predicate indirectly
  through `acquire()`/`withGigLock()` (real fs, real timers) is Tier 2, not Tier 1, regardless of
  how it is labeled.
- **Tier 2**: integration tests — real module wiring (real `fs`, injected small timing constants,
  concurrent `Promise.all` calls against the real lock/persist/gig modules) plus fresh-context
  adversary review of the disk artifacts (no live network required for this tier).
- **Tier 3**: live, no-mock E2E — real transactions against the live testnet (or, once graduated,
  mainnet) facilitator + ERC-8004 registry, executed the same way the round-1/2 adversary did
  (real concurrent calls, real on-chain reconciliation), per this project's HARD RULE 0.24
  (on-chain-verified only, no paper/simulated claims). **Tier 3 verification for REQ-101/102/103
  MUST be a fresh, independent execution by the Phase 3 adversary itself — it may reference the
  round-3 self-report (`evidence/p2.2-security-fixes-round3.md`) as historical context, but MUST
  NOT accept that self-authored evidence as satisfying this increment's own Tier 3 obligation (see
  Gate section and PROP-103b; resolves FIND-006).**

## Proof Obligations

| ID | REQ | Description | Tier | Required | Tool / Method |
|---|---|---|---|---|---|
| PROP-101a | REQ-101 | A live holder that heartbeats at interval `H` is NEVER stolen from, however long (past any fixed threshold) its critical section legitimately runs | 1 | true | Phase 2 first extracts `isLockStale(nowMs, mtimeMs, staleMs) → boolean` as an exported pure function and rewires `acquire()` to call it (binding REQ-101 acceptance criterion). Tier-1 unit test: call `isLockStale` directly with fixed/injected values proving a heartbeated lock's effective mtime never crosses the staleness window. Additionally, the existing `withGigLock`-driven scenario (inject tiny `staleMs`/`heartbeatMs`, start a long-running `fn()`, attempt a concurrent second acquire mid-run, assert rejection throughout) remains as Tier 2 regression coverage of the integrated behavior. |
| PROP-101b | REQ-101 | A genuinely dead holder's lock (no heartbeat for ≥ `staleMs`) IS reclaimable by exactly one subsequent caller | 1 | true | Tier-1 unit test directly against exported `isLockStale(nowMs, mtimeMs, staleMs)`: fixed `nowMs`/`mtimeMs`/`staleMs` fixtures proving the boolean flips correctly at and past the boundary. Tier 2: create a real lock file, backdate its mtime past `staleMs` (no live heartbeat running), assert exactly one of two concurrent reclaim attempts against the real `acquire()` succeeds. |
| PROP-101c | REQ-101 | Reclaim is atomic — no window where two callers both believe they hold the same key | 1/2 | true | unit test using the real `fs.open('wx')` primitive (not a mock) with two concurrent reclaim attempts on the same backdated lock file; Tier 2 repeats this under `Promise.all` with real fs timing jitter |
| PROP-101d | REQ-101 | Unrelated lock keys never contend with each other | 1 | true | Tier-1 unit test: two different lock keys acquired concurrently both succeed immediately (does not depend on `isLockStale` at all, so remains Tier 1 regardless of the extraction's landing order). |
| PROP-102a | REQ-102 | A slow operation on gig X does not clobber a concurrent, already-succeeded operation on unrelated gig Y | 2 | true | integration test: inject an artificially slow `pay`/settle for gig X's `verify_and_pay`, run it concurrently with a fast `gig_take` on gig Y, assert the FINAL persisted board reflects gig Y's take (not reverted to `'open'`) |
| PROP-102b | REQ-102 | Every write to the shared board file re-reads fresh from disk immediately before mutating, never reusing a snapshot captured before a slow step | 2 | true | integration test: assert the write path's `loadState` call happens AFTER the slow network step completes, not before it (call-order assertion, not just an outcome assertion) |
| PROP-102c | REQ-102 | The shared-file critical section is brief (local read-mutate-write only); the slow network/settle step does not hold the shared-file lock | 2 | true | integration test: assert an unrelated gigId's operation is not blocked for the duration of another gig's slow network step — only for the brief local write window |
| PROP-103a | REQ-103 | Existing round-1/2/3 fund-safety assertions remain green after this increment's lock/persist changes | 1/2 | true | run the full existing suite (`node --test __tests__/*.test.mjs`, dependencies installed) — 0 regressions in previously-passing assertions |
| PROP-103b | REQ-103 | A fresh, INDEPENDENT adversary re-attack of the round-1 fail-open scenarios (self-verify, same-gig double-pay) still fails as designed | 2/3 | true | **fresh-context Sonnet adversary independently re-runs the exact round-1/2 exploit scripts against the CURRENT code itself — its own invocation, its own transaction hashes/timestamps — both via disk review (Tier 2) and, where feasible, against a live/testnet deployment (Tier 3). The adversary MUST NOT accept `evidence/p2.2-security-fixes-round3.md`'s already-completed self-report (written by the same builder earlier the same day) as a substitute for this independent re-execution — that file may be read as background/history only (resolves FIND-006).** Expects rejection in every case. |
| PROP-201a | REQ-201 | `filterCatalog` excludes every slot tagged capital-risking when `balanceUsdc < threshold`, EXCEPT slots covered by the `alwaysAvailableOf` or `hasOpenRiskPositionOf` carve-outs below | 1 | true | unit test: fixed slot list with a mix of risk tags, balance strictly below threshold, `alwaysAvailableOf` and `hasOpenRiskPositionOf` both returning `false` for every slot, assert output excludes exactly the risky-tagged slots |
| PROP-201b | REQ-201 | `filterCatalog` returns the full, unfiltered slot list when `balanceUsdc >= threshold` (boundary: equality counts as "at or above") | 1 | true | unit test: `balanceUsdc === threshold` exactly → full list; `balanceUsdc = threshold + epsilon` → full list |
| PROP-201c | REQ-201 | An unset/non-finite/negative `BOOTSTRAP_RESERVE_USDC` or balance input falls back to the documented safe default (`20`, `Number(process.env.BOOTSTRAP_RESERVE_USDC) \|\| 20`), and the gate is never silently disabled | 1 | true | unit test mirroring `tier.mjs`'s existing NaN/Infinity/negative test pattern (PROP-004 there); additionally assert the literal fallback value resolves to `20` when the env var is unset/unparseable, and assert `20 >= 5` (the `COMPUTE_RESERVE_USDC` default) as a standing invariant check, not just a runtime behavior |
| PROP-201d | REQ-201 | A slot with no explicit risk tag defaults to capital-risking (excluded) while below threshold (subject to the same two carve-outs) | 1 | true | unit test: slot present in the input list with no risk-tag entry, balance below threshold, `alwaysAvailableOf`/`hasOpenRiskPositionOf` both `false`, assert it is excluded |
| PROP-201e | REQ-201 | Slots maintainer-tagged `alwaysAvailable: true` (`report`, `cook`) survive filtering even in a pathological all-risky-tag input; the `sleep` meta-tool is structurally unaffected by this filter entirely | 1 | true | unit test: every live slot (including `report`/`cook`) tagged risky, `alwaysAvailableOf('report')`/`alwaysAvailableOf('cook')` return `true`, balance below threshold — assert `report` and `cook` remain in the output regardless of their risk tag; separately assert (Tier 0 structural read of `prompt.mjs::getToolDefinitions`) that `sleep` is appended unconditionally, independent of `filterCatalog`'s output (resolves FIND-002) |
| PROP-201f | REQ-201 | A capital-risking slot with a currently-open position (`hasOpenRiskPositionOf(slot) === true`) remains available even when balance is below `BOOTSTRAP_RESERVE_USDC`, so an existing exposure can always be closed/withdrawn | 1 | true | unit test at the pure `filterCatalog` level (fake boolean inputs, no real query behind them): `hl_trade` tagged capital-risking, balance below threshold, `hasOpenRiskPositionOf('hl_trade')` returns `true` → assert `hl_trade` remains in the output; a second case with `hasOpenRiskPositionOf('hl_trade')` returning `false` → assert it is excluded. Same for `yield`. This directly proves the FIND-003 deadlock (liquidityDirective instructing a close while the catalog hides the tool to do it) cannot occur AT the pure-filter level; PROP-201h/i below prove the two REAL upstream implementations feeding these booleans are correct. |
| PROP-201g | REQ-201 | Every slot currently `status: "live"` in `skills/registry.json` carries an explicit `risk`/`alwaysAvailable` classification (resolves FIND-101) | 0 | true | structural check: parse `skills/registry.json`, filter to `status === "live"`, assert every one of the 17 live slots has either `risk === "safe"`, `risk === "capital"`, or `alwaysAvailable === true`, matching the exact assignment in behavioral-spec.md REQ-201's classification table. A Phase 3 finding of even one untagged live slot fails this PROP and REQ-201 as a whole. |
| PROP-201h | REQ-201 | `hasOpenRiskPositionOf('yield')`'s REAL implementation is a synchronous read of the exact ledger-scan expression that also produces `ctx.positionsSummary` — no new I/O (resolves FIND-102, yield half) | 1 | true | unit test: fixture `recentLedger` arrays (with/without a matching `source.startsWith('yield') && l.tx` entry) fed directly to the real `hasOpenRiskPositionOf('yield')` implementation (not a stub) — assert it returns `true`/`false` matching the fixture, with zero network/fs calls made during the test (spy/assert no I/O). |
| PROP-201i | REQ-201 | `hasOpenRiskPositionOf('hl_trade')`'s REAL implementation (a) queries lazily — only when `balanceUsdc < BOOTSTRAP_RESERVE_USDC` — and never otherwise; (b) returns `true` on any query failure/timeout/unreachability, not `false` (resolves FIND-102, hl_trade half) | 2 | true | integration test: (a) with `balanceUsdc >= BOOTSTRAP_RESERVE_USDC`, assert the Hyperliquid query function is never invoked for that wake (spy/mock call-count assertion = 0); with `balanceUsdc < BOOTSTRAP_RESERVE_USDC`, assert it IS invoked exactly once; (b) inject a rejecting/throwing/timing-out query implementation and assert `hasOpenRiskPositionOf('hl_trade')` resolves `true` (not `false`, not a thrown error propagating up); (c) inject a resolved query returning a non-empty `open_positions` array → assert `true`; an empty array → assert `false`. |
| PROP-202a | REQ-202 | The filter is a pure function of the CURRENT wake's balance and bookkeeping inputs only — no persisted state across calls | 1 | true | unit test: two successive calls with different balances (below then above threshold) and different `hasOpenRiskPositionOf` results on the SAME process/module state return the correct output for each call independently, with no leakage between calls |
| PROP-202b | REQ-202 | A balance transition from below to at/above threshold between two wakes restores the exact pre-restriction slot set on the very next wake | 1/2 | true | unit test at the pure-function level (PROP-201b already covers the pure case); Tier 2 integration test drives `runtime/loop/index.mjs`'s wiring across two simulated wakes with different fetched balances and asserts `activeSkillSlots`/`skillCatalog` match |
| PROP-203a | REQ-203 | The filter's return type carries no score/rank/preference field | 0 | true | structural/type check: return value is a plain array of strings (or equivalent minimal set), reviewed at Phase 3 |
| PROP-203b | REQ-203 | No prompt text generated by this increment recommends a specific remaining slot | 0 | true | **Phase 3 adversary structural read of the FULL current `runtime/loop/prompt.mjs` (not only this increment's diff — the baseline is NOT neutral "you decide" framing; see the Purity Boundary Map correction above and FIND-005), confirming (a) no NEW steering/ranking text was added by this increment, AND (b) after REQ-204's removal/neutralization, no pre-existing steering block of equivalent strength remains in the file's binding sections. This is deliberately the SAME generalized scope as PROP-204a below (resolves FIND-201) — the two checks are two views of one fact and MUST agree; a PASS here paired with a FAIL on PROP-204a (or vice versa) means one check was scoped too narrowly and both must be redone together.** |
| PROP-204a | REQ-204 | The pre-existing `## ★COLONY BOOTSTRAP PRIORITY★` imperative block, its "Prefer this over re-yielding surplus" / "it is almost never 'yield again'" ranking phrases, "the highest-leverage move is to POST" (resolves FIND-201), and — generalized — ANY other ranking/imperative language anywhere within the block or any paragraph it references, are removed or neutralized from `buildSystemPrompt`'s output | 0 | true | **structural check, generalized scope (resolves FIND-201, not a narrow grep of only the three/four named phrases): Phase 3 adversary reads the FULL `## ★COLONY BOOTSTRAP PRIORITY★` block AND the full text of any paragraph(s) it references or duplicates (e.g. the `economy/gig` bullet inside `## Your earn tools`, `runtime/loop/prompt.mjs` lines ~70-76), and confirms NO ranking/imperative/preference-ordering language of any kind remains in that scope — not merely that the specific phrases named in behavioral-spec.md REQ-204 are gone (those are illustrative minimum examples, not an exhaustive list). The self-labeled "Tips ... advice, NOT rules" section remains out of scope per REQ-204's edge cases. This check MUST reach the SAME PASS/FAIL conclusion as PROP-203b's broader "no pre-existing steering block of equivalent strength remains" check, evaluated against the identical code state — if PROP-204a would report PASS while PROP-203b reports FAIL (or vice versa) for the same file, PROP-204a's check was applied too narrowly (grep-only against named phrases) and MUST be redone at this generalized scope before either PROP may be marked PASS.** |
| PROP-301a | REQ-301 | The research record exists under `evidence/` and contains all five required items (a)-(e) | 0 | true | structural check: file exists, each of (a)-(e) present as a distinct, evidenced section (not a bare unsupported claim) |
| PROP-301b | REQ-301 | Each factual claim in the record cites at least one piece of concrete evidence (file/line, quoted API response, PR state + timestamp, or an explicit "checked X, not found" statement) | 0 | true | Phase 3 adversary spot-checks a sample of claims against the cited evidence (re-fetch the PR/repo state, re-run any quoted command) |
| PROP-302a | REQ-302 | No code/process change in this increment introduces a dependency from the gig-board witness track onto REQ-301's completion | 0 | true | structural review: grep/read for any new gating condition referencing the research record's status in the witness runbook or gig-board code path — must find none |

## Verification Strategy

- **Tier 0** (no runtime execution): REQ-203's structural "no ranking field" check, REQ-204's
  removal/neutralization of the pre-existing prompt steering block, REQ-301/302's research-record
  existence/citation/non-blocking checks, and REQ-201's registry-classification-completeness check
  (PROP-201g: every currently-live `registry.json` slot carries an explicit `risk`/`alwaysAvailable`
  tag — resolves FIND-101).
- **Tier 1** (pure-function unit tests): REQ-101's staleness predicate — **conditional on the
  `isLockStale(nowMs, mtimeMs, staleMs)` extraction landing first** (see REQ-101's binding
  acceptance criterion and the Purity Boundary Map) — and atomic-reclaim behavior in isolation;
  REQ-201/202's `filterCatalog` pure function (exhaustive branch coverage: below / at-boundary /
  above threshold; tagged-risky / tagged-safe / untagged; all-risky pathological case with
  `alwaysAvailable` overrides; capital-risking-with-open-position carve-out, PROP-201f); REQ-201's
  `hasOpenRiskPositionOf('yield')` REAL implementation against ledger fixtures with zero I/O
  (PROP-201h); REQ-103's baseline "existing suite stays green" check at the unit level.
- **Tier 2** (integration, real module wiring + fresh-context adversary disk review): REQ-101's
  `acquire()`/`withGigLock()`-level regression coverage (real fs/timers, now calling the extracted
  `isLockStale` internally rather than an inline comparison), REQ-102's cross-gigId shared-file race
  reproduction (the same technique the round-2/3 adversary already used — artificially slow one
  operation, run it concurrently with a fast unrelated one, assert the final persisted state),
  REQ-103's fresh, INDEPENDENT adversary re-attack of the round-1 exploits against the current code
  (disk review; see PROP-103b), REQ-202's two-wake balance-transition wiring test through
  `index.mjs`, and REQ-201's `hasOpenRiskPositionOf('hl_trade')` REAL implementation — lazy
  invocation gating (never called at/above threshold) and fail-open-on-failure behavior, against an
  injected/mocked Hyperliquid query boundary (PROP-201i; resolves FIND-102).
- **Tier 3** (live, no-mock E2E against real/testnet chain state, HARD RULE 0.24): REQ-103's
  fresh-adversary re-attack extended to a LIVE re-run that the Phase 3 adversary itself executes
  (real concurrent `verify_and_pay` calls against the live facilitator + real on-chain
  reconciliation, its OWN transaction hashes) — matching the exact method the round-1/2 verdict
  already used, but performed independently rather than accepted from the round-3 self-report, so
  this increment's changes are proven not to reopen a real, on-chain fund-drain path — not merely a
  unit-test claim, and not merely a re-read of the builder's own prior evidence file.

## Gate

Phase 3 (adversarial review) must confirm, via fresh-context, disk-only review plus (for PROP-102
and PROP-103) live/testnet re-execution performed by the adversary itself:
(1) REQ-101's heartbeat/atomicity properties hold under a deliberately-induced "live but slow"
scenario, not just a fast happy path, AND the staleness predicate has actually been extracted into
an independently exported, directly-unit-tested pure function (`isLockStale`) — a control-flow read
of `lib/lock.mjs` confirming `acquire()` calls it rather than re-implementing the comparison inline
(resolves FIND-004; a Tier-1 claim with the comparison still inlined must be rejected as not
satisfying REQ-101);
(2) REQ-102's shared-file protection genuinely re-reads fresh state under a single, brief critical
section — a control-flow read of `gig.mjs`'s `applyAndSave`, not a grep for the word "lock";
(3) REQ-103's full existing test suite is genuinely run (dependencies installed) and shows zero
regressions, AND the round-1 exploit scripts are re-attempted **by the adversary itself, live,
producing its own new transaction hashes** — the adversary must not accept
`evidence/p2.2-security-fixes-round3.md`'s prior same-day, same-builder self-report as satisfying
this obligation (resolves FIND-006);
(4) REQ-201/203/204's catalog filter and prompt diff are read end-to-end to confirm: the filter
contains no scoring/ranking/preference logic anywhere in its diff (only threshold comparisons and
set arithmetic over the three bookkeeping signals — risk tag, always-available flag, open-position
fact), the documented `BOOTSTRAP_RESERVE_USDC` default of `20` is the literal fallback value present
in the code (resolves FIND-001), the `alwaysAvailable` mechanism is present and covers exactly
`report`/`cook` (resolves FIND-002), and the pre-existing `## ★COLONY BOOTSTRAP PRIORITY★` steering
block — AND, generalized, ANY other ranking/imperative language anywhere within that block or any
paragraph it references, including but not limited to "the highest-leverage move is to POST" in
the `economy/gig` bullet inside `## Your earn tools` (resolves FIND-201) — has actually been
removed or neutralized from `runtime/loop/prompt.mjs` as REQ-204 requires — reading the FULL file,
not just the diff, since the pre-increment baseline already contained steering text (resolves
FIND-005). PROP-203b and PROP-204a MUST agree on the outcome of this read for the same code state;
a PASS on one paired with a FAIL on the other means the check was scoped too narrowly (e.g. a grep
limited only to the phrases named in REQ-204) and both must be redone at the generalized scope
before the gate can be marked PASS (resolves FIND-201);
(4a) **`skills/registry.json` has an explicit `risk`/`alwaysAvailable` value on all 17 currently-live
slots, matching behavioral-spec.md REQ-201's classification table exactly, with none left to fall
back on the untagged-defaults-to-risky rule (resolves FIND-101; PROP-201g)** — the adversary must
independently re-derive at least a sample of the table's classifications from the referenced slots'
own code/summaries, not merely accept the table's claims at face value;
(4b) **`hasOpenRiskPositionOf` is actually implemented as the two distinct, evidenced mechanisms
REQ-201 specifies, not the single generic "already-fetched data" claim iteration 2 made (resolves
FIND-102)**: a control-flow read confirming (i) the `yield` branch reads the existing ledger scan
with no new I/O (PROP-201h), (ii) the `hl_trade` branch performs a NEW Hyperliquid query that is
invoked ONLY when `balanceUsdc < BOOTSTRAP_RESERVE_USDC` for that wake — never unconditionally — and
(iii) that query's failure/timeout/unreachable path resolves to `true`, not `false` (PROP-201i) —
the adversary must deliberately induce a query failure (e.g. an unreachable endpoint or an injected
rejection) and confirm `hl_trade` remains visible in that case, and that this fail-open direction is
intentional per REQ-201's stated fail-closed/fail-open split, not an accidental omission;
(5) REQ-301's research record is spot-checked against the actual current state of the referenced
GitHub PR/repo and `business.blockrun.ai` surface, not taken at face value.
