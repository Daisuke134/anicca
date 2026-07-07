# Behavioral Spec — anicca-agent-economy (Phase 1a)

**feature**: anicca-agent-economy · **mode**: strict · **increment**: gig-board concurrency
hardening + bootstrap-reserve catalog eligibility gate + business.blockrun.ai seller-channel
research spike · **日付**: 2026-07-07 · **revision**: iteration 4 (Phase 1c adversary review
iteration 1 returned FAIL with 6 findings, FIND-001..FIND-006, resolved by iteration 2; iteration 2
review returned FAIL with 2 CRITICAL findings, FIND-101/FIND-102, resolved by iteration 3; iteration
3 review returned FAIL with 1 HIGH finding, FIND-201 — this revision resolves it; see
`reviews/spec/iteration-1/output/findings/FIND-00{1..6}.json`,
`reviews/spec/iteration-2/output/findings/FIND-10{1,2}.json`, and
`reviews/spec/iteration-3/output/findings/FIND-201.json` for the original findings)

## Scope of this increment (read first)

`specs/SPEC.md` is this feature's design-log SSOT. P0 (self-funded separation), P1 (earn>spend
fail-closed guard), P2.1 (self-host x402 facilitator), and P2.2's core gig-board mechanics (post →
take → deliver → verify_and_pay → gasless payout, poster-auth, per-gigId locking, ERC-8004
lifecycle enforcement) are **already implemented and adversary-verified** — see
`reviews/p2.2/verdict.md` (rounds 1–2) and `evidence/p2.2-security-fixes*.md` (round 3). This spec
does **not** re-specify any of that. It formalizes, in EARS form with testable acceptance criteria,
exactly three NEW delta groups (REQ群A/B/C, 9 requirements total) so they can go through a fresh
Phase 2/3 verification cycle of their own:

- **REQ群A** (REQ-101..103): close the two residual concurrency gaps the round-2 adversary
  documented (lock-staleness theft from a live holder; the shared `state/gigs.json` file racing
  across different gigIds) — codifying the TARGET behavior regardless of whatever the current
  on-disk code already attempts, so a fresh adversary pass has a real spec to check it against.
- **REQ群B** (REQ-201..204): a new bookkeeping-only catalog eligibility gate that hides
  capital-risking earn slots from a broke instance's tool menu until it clears a reserve floor,
  plus retiring the pre-existing prompt-level steering hack that gate makes obsolete.
- **REQ群C** (REQ-301..302): a research spike (not an implementation) into whether
  `business.blockrun.ai` offers Franklin a seller-side listing path, to compare against the
  self-built P2P gig board as the external-inflow proof for SPEC.md §8 item ④.

## Purity boundary analysis (overview — file/function detail lives in verification-architecture.md)

| Concern | Classification | Why |
|---|---|---|
| Lock staleness decision (`is this lock file abandoned?`) | **Pure core (target)** | A boolean predicate over `(nowMs, mtimeMs, staleMs)` — no I/O once its inputs are supplied. Currently inlined inside `lib/lock.mjs`'s impure `acquire()`. REQ-101's acceptance criteria now make extracting this into an independently exported pure function (`isLockStale(nowMs, mtimeMs, staleMs) → boolean`) a **binding** requirement, not an optional nicety — see REQ-101's acceptance criteria below and FIND-004. |
| Lock acquisition/release/heartbeat (`fs.open('wx')`, `fs.stat`, `fs.unlink`, `fs.utimes`, `setInterval`) | **Effectful shell** | Real filesystem + wall-clock side effects; POSIX-atomicity is the actual safety mechanism. `acquire()` calls the extracted pure predicate rather than re-implementing the comparison inline. |
| Board mutation (`store.mjs`'s `applyPost`/`applyTake`/`applyDeliver`/`applyVerifyAndPay`) | **Pure core (existing, unchanged by this increment)** | Already a pure state-transition module; this increment does not touch it, only the read/lock/write plumbing around it. |
| Board persistence (`lib/persist.mjs`'s `loadState`/`saveState`, `gig.mjs`'s `applyAndSave`) | **Effectful shell** | Full-file read/write; the safety property this increment specifies (REQ-102) is about WHEN this shell code re-reads relative to a concurrent write, which is why it needs its own acceptance criteria even though the mutation logic itself stays pure. |
| Catalog eligibility filter (new, REQ-201/202) | **Pure core (new)** | `filterCatalog({ balanceUsdc, allSlotNames, riskTagOf, alwaysAvailableOf, hasOpenRiskPositionOf, reserveThresholdUsdc }) → string[]` — deterministic set arithmetic over already-fetched bookkeeping inputs, no I/O, directly analogous to the existing `tier.mjs::selectTier`. Three independent per-slot bookkeeping signals feed it (risk tag, always-available flag, open-position fact) — see REQ-201's design principle for why none of these three are "judgment." |
| Registry read + balance fetch + open-position bookkeeping + wiring the filtered catalog into the prompt (`runtime/loop/index.mjs`) | **Effectful shell** | `fs.readFile(registry.json)` + RPC balance read + threading the result into `assembleContext`/`buildSystemPrompt`. Open-position bookkeeping is now TWO different things, not one: (a) `hasOpenRiskPositionOf('yield')` reuses the already-fetched ledger scan that also populates `ctx.positionsSummary` — genuinely no new I/O; (b) `hasOpenRiskPositionOf('hl_trade')` is a NEW, lazy Hyperliquid position query, invoked only when `balanceUsdc < BOOTSTRAP_RESERVE_USDC` — this is new I/O this increment introduces, not a reuse of existing data (corrects the iteration-2 mischaracterization; resolves FIND-102). Both are resolved to plain booleans in `index.mjs` BEFORE `filterCatalog` is called, so `filterCatalog` itself stays pure. |
| Prompt steering-text retirement (REQ-204) | **Effectful-shell-adjacent, string-literal edit** | `runtime/loop/prompt.mjs::buildSystemPrompt`'s existing `## ★COLONY BOOTSTRAP PRIORITY★` string block is hardcoded prompt text, not computed; removing/neutralizing it is a diff to a string literal, verified structurally (Tier 0), not a runtime behavior with its own unit test. |
| business.blockrun.ai / Franklin PR research (REQ-301/302) | **Not code — investigation activity** | Firecrawl/`gh` reads of an external repo/site; its only artifact is a static markdown research record, not an executable path. Classified separately from the pure/effectful split above. |

---

## Requirements

### REQ-101: Lock staleness reflects liveness, not elapsed time
**EARS**: WHILE a lock holder is still actively executing its critical section, THE SYSTEM SHALL
NOT allow any other caller to acquire the same lock key, regardless of how much wall-clock time has
elapsed since the lock was created.

**Edge Cases**:
- A live holder's settle legitimately runs past any single fixed wall-clock threshold (e.g. a
  facilitator retry sequence exceeding 60s under network congestion): the lock MUST still not be
  stolen from it.
- The holder process crashes (killed, no clean release) mid-critical-section: the lock MUST
  eventually become reclaimable by a subsequent caller within a bounded, documented maximum wait —
  it must never wedge the board forever.
- Two separate callers detect the same lock as reclaimable at the same instant and both attempt to
  reclaim it: exactly one MUST win (the reclaim step itself must be atomic — no window where both
  successfully proceed).
- The staleness signal (the lock file's mtime) is manipulated or skewed (e.g. clock jump, manual
  `utimes`): this is a documented trust boundary of a single-machine filesystem lock, not something
  this requirement is expected to defend against — call this out explicitly rather than silently
  assuming it away.

**Acceptance Criteria**:
- **BINDING (structural, not optional)**: the staleness decision MUST be extracted into an
  independently exported, pure function with signature `isLockStale(nowMs, mtimeMs, staleMs) →
  boolean` (co-located in `skills/economy/gig/lib/lock.mjs` or a sibling pure module), and
  `acquire()` MUST call this exported function rather than re-implementing the
  `Date.now() - stat.mtimeMs > staleMs` comparison inline. This extraction is itself part of what
  "done" means for REQ-101 — a fresh Phase 3 adversary that finds the comparison still inlined
  (not independently exported/importable) MUST treat REQ-101 as NOT satisfied, regardless of
  whether the integration-level behavior happens to work. This resolves FIND-004: it makes the
  Tier-1 "pure function" classification in verification-architecture.md true of the actual code,
  not just an aspiration.
- A lock whose holder refreshes its own liveness signal at a bounded interval `H` is never
  reclaimable by another caller for as long as that holder keeps refreshing it, independent of total
  elapsed time.
- A lock with no liveness signal for at least a configured staleness duration IS reclaimable by
  exactly one subsequent caller (a second simultaneous attempt at reclaim fails).
- Reclaim uses an atomic filesystem primitive (e.g. exclusive create), never a
  check-then-act pair with a window between the check and the act.
- Both the staleness duration and the liveness-refresh interval are configurable (injectable),
  with production defaults maintaining a wide safety margin over the worst realistic
  legitimate-critical-section duration, and tests able to use small values so they run in
  milliseconds.

### REQ-102: The shared board file is protected across different gigIds
**EARS**: WHEN two operations that mutate DIFFERENT gigIds' records are in flight concurrently, THE
SYSTEM SHALL persist the outcomes of both operations without either one's write reverting or
losing the other's already-applied change.

**Edge Cases**:
- Gig X's slow `verify_and_pay` (holding a full-board snapshot captured before a slow network
  settle) races against gig Y's fast `take` on an unrelated, uncontended gigId: gig Y's take must
  survive in the final persisted board even though gig X's write completes later.
- Three or more concurrent operations across three or more distinct gigIds land in overlapping
  windows: every operation that returned `{ok:true}` to its caller must be reflected in the final
  persisted state.
- Two operations targeting the SAME gigId occur concurrently: this is already covered by REQ-101's
  per-gigId lock and MUST continue to be rejected/serialized as today — this requirement is
  additive (protects the cross-gigId case), not a replacement for the per-gigId lock.

**Acceptance Criteria**:
- The final on-disk board state reflects the effects of every operation that returned success to
  its caller; no successful `{ok:true}` result is ever silently undone by a later, unrelated write.
- Every write to the shared board file re-reads the board fresh from disk immediately before
  applying its mutation (never reuses an in-memory snapshot captured before a slow, concurrent
  step), and that read-mutate-write sequence for the shared file is itself an exclusive critical
  section shared by ALL gig operations (not just per-gigId ones).
- The (possibly slow) network/settle step for one gigId does not hold the shared-file lock for its
  own duration — only the brief local read-mutate-write portion does — so unrelated gigIds' writes
  are not needlessly serialized behind a slow network call.

### REQ-103: No regression of existing fund-safety invariants
**EARS**: WHILE implementing REQ-101 and REQ-102, THE SYSTEM SHALL continue to reject: (a) a
`verify_and_pay` call from any caller who is not the gig's poster; (b) a second payout for a gig
that has already been paid; (c) a payout to a taker whose ERC-8004 identity is no longer valid at
payout time.

**Edge Cases**:
- The full existing automated test suite for `skills/economy/gig/` (currently `store.test.mjs`,
  `decide.test.mjs`, `lock.test.mjs`, `gig.test.mjs`, `ensure-agent-id.test.mjs`) must remain green
  after this increment's changes, with no reduction in the number of passing assertions attributable
  to this increment's own edits (a pre-existing environment gap — `gig.test.mjs` /
  `ensure-agent-id.test.mjs` requiring `npm install` for the `viem` dependency in a fresh checkout —
  is a setup issue, not a code regression, and must be resolved by installing dependencies before
  claiming green, not by weakening the test).
- A new concurrency-focused test added for REQ-101/102 must not stub away or bypass the
  poster-authentication or ERC-8004 re-verification checks already proven in rounds 1–2 — the new
  test exercises the LOCKING behavior on top of those checks remaining fully active.
- Fixing REQ-101/102 must not reintroduce the original round-1 fail-opens (any caller self-verifying
  a gig; two concurrent `verify_and_pay(true)` calls on the SAME gig both succeeding).

**Acceptance Criteria**:
- `node --test __tests__/*.test.mjs` (with dependencies installed) exits 0 after this increment's
  changes, with the pre-existing round-1/2/3 security assertions unchanged in behavior.
- A fresh adversary re-attack (live, on real or testnet transactions) of the round-1 fail-open
  scenarios (self-verify, double-pay on one gig) still fails as designed (i.e., the attack is still
  rejected) after this increment's changes.
- **BINDING (resolves FIND-006)**: this re-attack MUST be independently executed by the Phase 3
  adversary itself (its own script invocation, its own transaction hashes, its own timestamps)
  against the current code. The Phase 3 adversary MUST NOT treat the round-3 self-report already
  on file (`evidence/p2.2-security-fixes-round3.md`, authored by the same builder earlier the same
  day) as satisfying this criterion by itself — a builder's own prior self-report is evidence of
  history, not a substitute for the fresh, independent re-verification this requirement demands.

---

### REQ-201: Capital-risk catalog restriction below the bootstrap reserve
**EARS**: WHILE an instance's realized liquid balance is below its configured
`BOOTSTRAP_RESERVE_USDC` threshold, THE SYSTEM SHALL exclude capital-risking earn slots (e.g.
`hl_trade`, `token_launch`, and any other slot tagged as capital-risking) from the catalog and
active-slot list surfaced to the model for that wake, presenting only slots that carry no capital
risk to the instance's own treasury (e.g. `economy/gig`, `economy/ubi`, `cook`, `self/*`, `report`,
and any other slot explicitly tagged non-risking) — **except** where REQ-201's open-position
carve-out below applies.

**`BOOTSTRAP_RESERVE_USDC` vs. the existing `COMPUTE_RESERVE_USDC` — two different latitudes on
the same balance (resolves FIND-001 + FIND-003's threshold-relationship half)**: this increment
introduces `BOOTSTRAP_RESERVE_USDC` as a **new, independent** env var, deliberately distinct from
the already-existing `COMPUTE_RESERVE_USDC` (`runtime/loop/context.mjs:39`, default `5`, which
drives `liquidity.mjs::liquidityDirective`'s "replenish first, do not deploy more into positions"
steer). The two thresholds answer two different questions over the identical balance read:
- `COMPUTE_RESERVE_USDC` (existing, default `5`): "does this instance have enough liquid USDC to
  keep paying for its own inference and not go dark?" — a **survival / gas buffer**. Below it, the
  instance is told to replenish, but its full tool catalog remains visible (it may need `hl_trade`
  or `yield` precisely to replenish).
- `BOOTSTRAP_RESERVE_USDC` (new): "has this instance cleared enough of a cushion that it is safe to
  let it take on NEW capital risk (open a fresh leveraged position, launch a new token)?" — a
  **capital-risk graduation floor**, strictly a higher bar than mere survival.
- **Invariant**: `BOOTSTRAP_RESERVE_USDC`'s documented default (`20`) MUST always be **strictly
  greater than or equal to** `COMPUTE_RESERVE_USDC`'s own documented default (`5`). The two env
  vars remain independently configurable per-instance (an operator MAY set either one), but their
  DEFAULTS must preserve this ordering so a freshly-deployed instance with no env overrides is never
  in the self-contradictory state of being "eligible to risk capital" while still below its own
  compute/gas survival floor.
- Default value, spelled out (resolves FIND-001): `BOOTSTRAP_RESERVE_USDC` defaults to **`20`**
  (i.e. `Number(process.env.BOOTSTRAP_RESERVE_USDC) || 20`), mirroring the exact
  `Number(process.env.X) || N` fallback idiom already used for `COMPUTE_RESERVE_USDC` in
  `runtime/loop/context.mjs:39`. This is the literal value a Phase 3 builder MUST hardcode as the
  fallback — it is no longer left for Phase 3 to invent.

**Registry classification for every currently-live slot — BINDING Phase 2 acceptance criterion
(resolves FIND-101)**: iteration 1's adversary found that a literal, criteria-satisfying
implementation of the "untagged live slot defaults to capital-risking" rule below would, TODAY,
exclude `economy/gig`, `economy/ubi`, every `self/*` slot, and more from a broke instance's
catalog — because not one of the 17 slots currently `status: "live"` in `skills/registry.json`
carries any `risk` field yet. That would break this feature's own headline bootstrap scenario (a
broke instance using `economy/gig` to earn with $0 capital) the moment this gate ships. This
increment closes that gap by making explicit classification of today's registry a REQUIRED part of
Phase 2, not an optional follow-up:

| Slot | Classification | Why (grounded in the slot's own current code/summary) |
|---|---|---|
| `report` | `alwaysAvailable: true` | non-earn per-wake telemetry/report utility; touches no capital |
| `cook` | `alwaysAvailable: true` | web-search exploration only (surfaces candidate URLs); touches no capital |
| `self/spawn` | `risk: "safe"` | its own decision core (`lib/spawn-decision.js`) already gates real provisioning on the PARENT being profitable — reading/considering this slot while broke cannot itself put a broke instance's treasury at risk |
| `self/spawn-child` | `risk: "safe"` | explicitly read-only per its own header comment: "PREPARATION ONLY ... Never executes a swap/mint/send/deployment-create itself" |
| `self/issue-dev` | `risk: "safe"` | files a GitHub Issue from the instance's own logs; touches no funds |
| `self/coordinate` | `risk: "safe"` | bot2bot info-sharing via GitHub issue post/poll; touches no funds |
| `economy/gig` | `risk: "safe"` | this feature's own headline scenario: `take` earns with $0 capital; `post` is already internally gated ("run.sh gates eligibility" per its own registry summary) on the poster already holding idle USDC above its own reserve |
| `economy/ubi` | `risk: "safe"` | `contribute()`/`distributeAI()` are fail-closed no-ops ("no profit/below threshold/would breach reserve") by the skill's own code — cannot deplete a broke instance's treasury |
| `x402_sell` | `risk: "safe"` | its own registry summary: "THE recurring **$0-capital** earner"; runs/advertises a server, deploys no funds |
| `earn/clip` | `risk: "safe"` | posts a pre-produced captioned clip via browser automation; deploys no funds |
| `earn/clip-producer` | `risk: "safe"` | deterministic local media pipeline (download/whisper/crop/caption); deploys no funds |
| `earn/video` | `risk: "safe"` | faceless-video creation/posting pipeline; deploys no funds |
| `yield` | `risk: "capital"` — **carve-out applies**, see below | deposits real capital into a DeFi vault (Aave v3/Beefy) — genuine smart-contract exposure; `execute-yield.mjs` already self-gates new deposits to surplus above `COMPUTE_RESERVE_USDC` and WITHDRAWS below it, so the withdraw side must remain visible below `BOOTSTRAP_RESERVE_USDC` too |
| `hl_trade` | `risk: "capital"` — **carve-out applies**, see below | leveraged perp trading (`hl.py open`) — the canonical capital-risking example named in REQ-201's own EARS clause |
| `token_launch` | `risk: "capital"`, no carve-out | launching/managing a speculative token — the other capital-risking example named in REQ-201's own EARS clause; no distinct catalog-gated "close" action is described for it |
| `earn/sol-trade` | `risk: "capital"`, no carve-out | the Franklin-Trading CLI trades the instance's own Solana bankroll end-to-end within one self-contained run; no separate catalog-gated close action exists for the gate to preserve |
| `earn/polymarket-trade` | `risk: "capital"`, no carve-out | the Polymarket agent trades the instance's own wallet end-to-end within one self-contained run; same reasoning as `earn/sol-trade` |

(`earn`, `earn/audit`, `earn/_probe` are `status: "declared"`, not `"live"` — `liveSlotNames()`
already excludes them from the catalog entirely, so they need no risk classification for this gate
to be safe; they are omitted from the table above for that reason, not because they are unclassified.)

This table is the concrete Phase 2 work item: Phase 2 MUST write these exact `risk`/`alwaysAvailable`
fields into `skills/registry.json` for all 17 currently-live slots as part of landing REQ-201/202,
before the eligibility gate goes live. See Acceptance Criteria below for the binding form of this
requirement.

**Design principle (must hold, verified structurally not just behaviorally)**: this filter is a
deterministic, numeric bookkeeping gate over WHICH options are offered — a risk-guardrail /
treasury-safety layer, analogous to the existing `tier.mjs::selectTier` balance-based model
selection already in this codebase. It MUST NOT encode any preference, ranking, score, or
recommendation among the slots that remain after filtering, and MUST NOT make or bias any judgment
about task content, strategy, or which remaining slot the model "should" pick. Once the eligible
set is computed, slot selection, task parameters, and `ANICCA_ARGS` remain entirely the model's own
decision, exactly as today. This is why the filter is compliant with this project's hard rule that
the model — not hardcoded regex/if-else — makes judgment calls: the code only narrows the
**objective, numeric/bookkeeping** option space (three independent bookkeeping facts: "is realized
balance ≥ $X", "is this slot maintainer-tagged capital-risking", "does the instance currently hold
an open position that needs THIS slot to close/withdraw"), never the **subjective** choice within
it. None of these three facts are inferred from task content or natural-language judgment — all
three are read directly off already-fetched bookkeeping state (`registry.json` fields and current
position data), exactly like `riskTagOf` already was in iteration 1.

**Open-position carve-out — resolves the hl_trade close-position deadlock (FIND-003), with its
exact data source(s) and failure mode now specified per-mechanism (resolves FIND-102)**: excluding
a capital-risking slot below the reserve threshold applies **only to using that slot to take ON NEW
risk** (e.g. `hl_trade` called to `open` a fresh position, `token_launch` called to launch a new
token). It does **NOT** apply when the instance needs that same slot to **close or withdraw an
already-existing position** it currently holds (this increment evidences this need for exactly
`hl_trade` and `yield` — see the classification table above; `token_launch`/`earn/sol-trade`/
`earn/polymarket-trade` have no distinct catalog-gated close action and so get no carve-out).
Concretely: `filterCatalog` takes an additional bookkeeping input, `hasOpenRiskPositionOf(slotName)
→ boolean` — a plain, already-RESOLVED synchronous boolean per slot that `runtime/loop/index.mjs`
computes BEFORE calling `filterCatalog` (exactly like `balanceUsdc` itself is fetched async and then
passed in as a plain number) — so `filterCatalog` remains pure and untouched by anything below; only
`index.mjs`'s construction of the real `hasOpenRiskPositionOf` values changes. This is a bookkeeping
fact, not a judgment: it does not decide whether the model SHOULD close the position, or infer
intent from any text — it only reports whether an existing position row exists.

Iteration 1/2 claimed a single, generic mechanism ("read directly off the instance's already-fetched
position data... the same underlying bookkeeping that populates `ctx.positionsSummary` today") for
ALL carved-out slots. FIND-102 showed this was only true for ONE of them. This increment therefore
specifies TWO distinct, concrete, independently-verified mechanisms:

- **`hasOpenRiskPositionOf('yield')` — genuinely already-fetched, no new I/O.** `index.mjs` already
  computes, every wake, unconditionally: `recentLedger.slice().reverse().find(l =>
  String(l.source||'').startsWith('yield') && l.tx)` (this is the exact expression that populates
  `ctx.positionsSummary` today). `hasOpenRiskPositionOf('yield')` is simply `true` when that `find`
  call returns a match, `false` otherwise — no new fetch, no new cost, no change to when this data is
  computed. This is the one part of the original claim that was always literally true.
- **`hasOpenRiskPositionOf('hl_trade')` — a NEW, lazy, dedicated query; the original claim was FALSE
  for this slot.** `ctx.positionsSummary` structurally excludes `hl_trade`: every `hl_trade` ledger
  record is written with `source: 'hl-trade'` (`skills/earn/run.sh`), which does not match the
  `startsWith('yield')` filter above — there is no existing already-fetched signal for `hl_trade`'s
  position state anywhere in the wake loop today (FIND-102's own evidence). This increment adds a new
  query: `index.mjs` invokes the SAME Hyperliquid `clearinghouseState`-backed primitive
  `skills/earn/hl-trade/hl.py account` already uses in production (`hl.py`'s `open_positions` array,
  derived from `info.user_state(address).assetPositions` filtered to nonzero `szi`, `hl.py:64-73`) —
  either by invoking `hl.py account` as a subprocess the same way `skills/earn/run.sh` already does,
  or an equivalent direct call to the same Hyperliquid info endpoint — and treats a non-empty
  `open_positions` array as `true`. **Lazy, not every-wake**: this query fires ONLY when
  `balanceUsdc < BOOTSTRAP_RESERVE_USDC` for the current wake — when the balance is at/above
  threshold, `filterCatalog` never needs `hasOpenRiskPositionOf` for any capital-risking slot at all
  (PROP-201b: the full, unfiltered list is returned), so the query is simply never made in that case.
  This bounds the new network cost to exactly the wakes where the answer is decision-relevant.

**Fail-open default for `hasOpenRiskPositionOf('hl_trade')`'s new query — deliberately the OPPOSITE
direction from this same requirement's own "fail-closed by default" rule for balance/config/
untagged-slot failures (see the edge case below), and here is why that reversal is correct**: if the
lazy Hyperliquid query fails, times out, or the HL API is unreachable, `hasOpenRiskPositionOf(
'hl_trade')` returns **`true`** — it assumes a position MAY be open and keeps `hl_trade` visible —
rather than `false`. Every OTHER fail-closed default in this requirement (unset/unparseable
threshold, failed balance fetch, an untagged slot) fails toward EXCLUDING a slot, because wrongly
excluding a slot the instance didn't actually need is a small, bounded harm (it just can't open new
risk for one wake). Failing THIS ONE flag toward `false` instead would recreate the exact FIND-003
deadlock: an instance below its own reserve, holding a real leveraged position, told by
`liquidityDirective` to close it, would have `hl_trade` hidden by a transient network hiccup with no
way to carry out the instruction it was just given — an unbounded, high-cost failure (a real
leveraged position stuck open indefinitely) versus fail-open's bounded, low-cost failure (`hl_trade`
stays visible for one extra wake despite no real open position; the model still decides whether to
act on it — nothing forces a trade). This is not an inconsistency with REQ-203's general
fail-closed posture; it is the SAME "minimize worst-case harm" principle correctly applied to a
failure mode whose worst case runs in the opposite direction from every other failure this
requirement handles.

When `hasOpenRiskPositionOf(slot)` is `true` (by either mechanism above), that slot remains in the
filtered catalog even while the balance is below `BOOTSTRAP_RESERVE_USDC`, specifically so
`runtime/loop/liquidity.mjs`'s existing `liquidityDirective` steer (which, below
`COMPUTE_RESERVE_USDC`, instructs the model to "CLOSE a profitable HL position ... or withdraw idle
yield") is never given an instruction it has been structurally denied the tool to carry out. Without
this carve-out, an instance below BOTH thresholds while holding an open `hl_trade` or `yield`
position would be told to close/withdraw it and simultaneously have that slot removed from its
catalog — a real functional deadlock trapping possibly-losing exposure with no way to close it. With
the carve-out, the deadlock cannot occur: being below the bootstrap reserve only ever blocks OPENING
new capital-risking exposure, never closing existing exposure.

**Edge Cases**:
- Balance is exactly equal to `BOOTSTRAP_RESERVE_USDC`: defined as "at or above" the threshold, so
  the full catalog is shown (the restriction applies strictly *below* the threshold, not
  inclusive of it).
- `BOOTSTRAP_RESERVE_USDC` is unset or fails to parse as a finite non-negative number: falls back to
  the documented default of `20` (see above); the gate is never silently disabled by
  misconfiguration.
- The balance fetch itself fails or returns a non-finite/negative value (mirrors
  `tier.mjs::selectTier`'s existing NaN/Infinity/negative handling): treated as below-threshold
  (fail-closed / conservative), consistent with the existing tier-selection pattern in this
  codebase.
- A slot that exists in `registry.json` with `status: "live"` but has no explicit risk tag: defaults
  to being treated as capital-risking (excluded while below threshold, subject to the open-position
  carve-out above) until a maintainer explicitly tags it as non-risking — fail-closed by default,
  never fail-open by omission. **This default is a forward-compatibility safety net for slots added
  AFTER this increment ships — it is NOT a mechanism this increment currently relies on for any
  slot that is live today (resolves FIND-101).** The classification table above assigns an explicit
  `risk` or `alwaysAvailable` tag to all 17 slots that are `status: "live"` in `registry.json` as of
  this spec's writing, so at ship time zero live slots are untagged and this fallback path is never
  actually exercised against the current registry. A future slot added later WITHOUT a risk tag does
  fall back to this conservative default — that is the rule's entire and only purpose.
- **Every currently-live slot happens to be tagged risky (e.g. a total misconfiguration) — resolves
  FIND-002**: a SECOND, independent bookkeeping signal — `alwaysAvailableOf(slotName) → boolean`,
  read from a new `alwaysAvailable: true` field a maintainer sets directly on specific slots in
  `registry.json` — overrides the risk tag entirely for those specific slots, regardless of what
  the (possibly misconfigured) risk tag says. The slots this increment marks `alwaysAvailable:
  true` are exactly `report` and `cook` (the two named in this edge case), because they are the
  designated non-earn, zero-capital-risk utility slots this gate is not meant to ever be able to
  hide. The `sleep` meta-tool is a separate case: it is not a `registry.json` catalog entry at all
  — it is unconditionally appended by `runtime/loop/prompt.mjs`'s `getToolDefinitions` regardless
  of `activeSkillSlots`/`skillCatalog` content, so it is already structurally immune to this
  filter and needs no new mechanism to remain available. Precedence when
  `alwaysAvailableOf(slot)` is `true`: the slot is included in the filtered output UNCONDITIONALLY,
  before the risk-tag check is even consulted — the gate must never produce an empty actionable
  toolset for the model.

**Acceptance Criteria**:
- Given a balance strictly below the threshold, the computed catalog/active-slot list contains only
  slots that are either (a) not tagged capital-risking, (b) tagged `alwaysAvailable: true`, or (c)
  tagged capital-risking but currently holding an open position per `hasOpenRiskPositionOf`.
- Given a balance at or above the threshold, the computed catalog/active-slot list is identical to
  the unfiltered live-slot list (no slot is ever removed once above threshold).
- The filtering function's signature is `filterCatalog({ balanceUsdc, allSlotNames, riskTagOf,
  alwaysAvailableOf, hasOpenRiskPositionOf, reserveThresholdUsdc }) → string[]` — it takes only
  already-fetched bookkeeping inputs and returns a plain list with no ordering/score metadata
  attached.
- **BINDING (resolves FIND-101)**: as part of THIS increment's Phase 2 implementation (not deferred
  to a later increment), every slot currently `status: "live"` in `registry.json` (the 17 slots
  listed in the classification table above) MUST be given an explicit `"risk": "safe"` or `"risk":
  "capital"` field, OR an `"alwaysAvailable": true` field, in `registry.json` itself, matching the
  table's assignment. A Phase 3 adversary that finds any currently-live slot still untagged after
  this increment ships MUST treat REQ-201 as NOT satisfied.
- **BINDING (resolves FIND-102)**: `hasOpenRiskPositionOf('yield')` MUST be implemented as a
  synchronous read of the same already-fetched ledger scan `index.mjs` already performs for
  `ctx.positionsSummary` (no new I/O, no new query). `hasOpenRiskPositionOf('hl_trade')` MUST be
  implemented as the lazy, threshold-gated Hyperliquid position query described above — invoked only
  when `balanceUsdc < BOOTSTRAP_RESERVE_USDC` for the current wake, never on every wake — and MUST
  default to `true` (not `false`) on any failure, timeout, or unreachability of that query. Every
  other slot's `hasOpenRiskPositionOf` (any slot other than `yield`/`hl_trade`) returns `false`
  unconditionally — no carve-out mechanism is specified or required for them.

### REQ-202: Automatic, non-sticky restoration once above the reserve
**EARS**: WHEN an instance's realized liquid balance rises to at or above
`BOOTSTRAP_RESERVE_USDC`, THE SYSTEM SHALL restore the full live catalog on the very next wake, with
no manual reset step and no persisted "still restricted" flag surviving the balance crossing the
threshold.

**Edge Cases**:
- Balance oscillates around the threshold across consecutive wakes (e.g. $19.99 → $20.01 → $19.98):
  the gate is recomputed fresh from the CURRENT wake's balance every time, with no hysteresis or
  sticky memory of a prior wake's restricted state — this is accepted behavior for this increment
  (not a bug), documented explicitly so a future contributor does not "fix" it into stateful
  hysteresis without a new requirement.
- The restored (above-threshold) catalog must be byte-for-byte the same slot set the instance would
  have seen had it never dropped below the threshold (no slot permanently lost due to having been
  filtered once).

**Acceptance Criteria**:
- The filter is a pure function of the CURRENT wake's balance, the current live-slot list, and the
  current wake's bookkeeping inputs (risk tags, always-available flags, open-position facts); it
  holds no state across wakes.
- A balance transition from below-threshold to at/above-threshold between two consecutive wakes
  results in the very next wake's catalog being the full, unfiltered live-slot list.

### REQ-203: Design-constraint requirement — bookkeeping only, never judgment
**EARS**: WHERE this increment filters the model's available catalog, THE SYSTEM SHALL implement
that filter exclusively as arithmetic over objective, already-known bookkeeping facts (realized
balance, a configured threshold, a per-slot risk tag that a human/maintainer sets in
`registry.json`, a per-slot `alwaysAvailable` flag a maintainer sets in `registry.json`, and a
per-slot open-position fact — for `yield`, read from the already-fetched ledger bookkeeping that
also populates `ctx.positionsSummary`; for `hl_trade`, read from a new, lazy, threshold-gated
Hyperliquid position query fired only when `balanceUsdc < BOOTSTRAP_RESERVE_USDC` (see REQ-201's
open-position carve-out) — none inferred by the
code at runtime from task content), and SHALL NOT implement, alongside or instead of it, any
regex/keyword-based classification of task content, any scoring/ranking of the remaining options,
or any steering text that tells the model WHICH of the remaining options to prefer.

**Edge Cases**:
- A future change that adds slot-ordering-by-expected-value, a "recommended slot" field, or any
  similar preference signal on top of this gate would violate this requirement and must be rejected
  in code review, even if well-intentioned.
- This requirement is not independently unit-testable in the normal sense (it is a constraint on
  what the implementation must NOT contain); it is verified via structural code review (grep/read
  for scoring or ordering logic) at Phase 3, not via a runtime assertion.

**Acceptance Criteria**:
- The filter function's return type is a plain set/list of slot names with no attached score, rank,
  or preference weight.
- No prompt text generated by this increment tells the model which of the remaining, eligible slots
  it "should" choose.

### REQ-204: Retire the pre-existing prompt-level steering block once the eligibility gate lands
**EARS**: WHEN this increment's REQ-201/202 eligibility gate is implemented and wired into the wake
loop, THE SYSTEM SHALL remove or neutralize the pre-existing `## ★COLONY BOOTSTRAP PRIORITY★`
steering block, together with ANY ranking/imperative language found anywhere within that block or
within any paragraph it references or duplicates (e.g. the `economy/gig` bullet inside the `## Your
earn tools` section) that tells the model WHICH slot to prefer over the others — including, at
minimum, "Prefer this over re-yielding surplus", the "MINDSET: ... it is almost never 'yield
again'" framing, and "the highest-leverage move is to POST" (resolves FIND-201) — from
`runtime/loop/prompt.mjs`'s `buildSystemPrompt`.

**Why this requirement exists (resolves FIND-005)**: `runtime/loop/prompt.mjs` as it exists on
disk TODAY is **not** a neutral "you decide" baseline — it already contains a forceful, imperative
steering block: *"your FIRST action this wake MUST be economy/gig ... Do this BEFORE hl_trade /
yield / anything else"*, plus *"Prefer this over re-yielding surplus"* and *"it is almost never
'yield again'"*. Per SPEC.md §9.6, this prompt-level text was itself the FIRST (and, per the
project's own hard rule against hardcoded steering, non-compliant) attempt to solve "the model
doesn't reliably pick `economy/gig`." REQ-201/202's objective, bookkeeping-only eligibility gate is
the design-compliant SUCCESSOR to that prompt-hack: once the gate can structurally narrow the
option space by balance, the prompt no longer needs to (and, per REQ-203's own principle, must
not) also tell the model which remaining option to prefer. Leaving both mechanisms in place
simultaneously after this increment ships would mean REQ-203's "no steering text" principle is
false of the codebase in the very increment that establishes it. **This applies wherever the
ranking language physically sits, not only inside the block's own literal string boundaries
(resolves FIND-201)**: a ranking phrase one paragraph away from the block — e.g. the `economy/gig`
bullet inside the `## Your earn tools` section, which as of this spec's writing also states "the
highest-leverage move is to POST", five lines before the already-named "Prefer this over
re-yielding surplus" in the exact same bullet — is functionally identical steering and would leave
REQ-203's principle just as false if left in place.

**Edge Cases**:
- The `## Tips from a senior who has run these (advice, NOT rules — adapt, do not copy blindly)`
  section is explicitly out of scope for removal — it is already self-labeled as non-binding advice
  rather than an imperative instruction.
- **The named phrases above are a MINIMUM, not an exhaustive or exclusive list (resolves
  FIND-201)**: REQ-204's actual scope is every ranking/imperative phrase found anywhere within the
  `## ★COLONY BOOTSTRAP PRIORITY★` block itself, and anywhere within any paragraph that block
  references or duplicates (e.g. the `economy/gig` bullet inside the `## Your earn tools` section).
  As of this spec's writing that bullet contains a fourth such phrase not previously named — "the
  highest-leverage move is to POST" — sitting five lines before "Prefer this over re-yielding
  surplus" in that same bullet. A future spec revision or Phase 3 finding that surfaces yet another
  unnamed ranking/imperative phrase within this same scope does NOT require a new requirement or a
  spec amendment before it must be removed — REQ-204 already covers it under this generalized
  criterion; only the illustrative list of named examples may need updating for clarity.
- If retiring this block is deferred to a later increment for any reason, that deferral MUST be
  explicitly flagged in this increment's own completion evidence as a KNOWN, temporary violation of
  REQ-203 — never silently treated as if REQ-203 were already fully satisfied.

**Acceptance Criteria**:
- The diff landed by this increment removes or neutralizes, AT LEAST, the `## ★COLONY BOOTSTRAP
  PRIORITY★` block's imperative "MUST" / "Do this BEFORE X" language, the "Prefer this over
  re-yielding surplus" / "it is almost never 'yield again'" ranking phrases, and "the
  highest-leverage move is to POST" (the `economy/gig` bullet inside `## Your earn tools`) from
  `buildSystemPrompt`'s output — these named phrases are illustrative minimum examples, not the
  full scope (see the generalized criterion below).
- **GENERALIZED, BINDING criterion (resolves FIND-201)**: the diff removes or neutralizes ANY
  ranking/imperative/preference-ordering language — any text that scores, ranks, or tells the model
  WHICH of the remaining slots to prefer over the others — found anywhere within the `## ★COLONY
  BOOTSTRAP PRIORITY★` block itself, or anywhere within any paragraph that block references or
  duplicates (including, but not limited to, the `economy/gig` bullet inside `## Your earn tools`).
  The named phrases above are the minimum known instances at spec-writing time, not an exhaustive
  or exclusive list. A Phase 3 adversary that finds ANY slot-preference-ranking phrase of
  equivalent strength still present anywhere in this scope — named in this spec or not — MUST treat
  REQ-204 as NOT satisfied.
- A Phase 3 adversary reading the FULL current file (not only this increment's diff) confirms no
  equivalent-strength imperative steering/ranking text remains anywhere in the file's binding
  (non-"tips", non-"advice") sections. This criterion, the generalized criterion above, and
  PROP-203b / PROP-204a in verification-architecture.md MUST always reach the same PASS/FAIL
  conclusion for the same code state — a discrepancy between them indicates one of the checks was
  applied too narrowly and must be redone at the scope described here.

---

### REQ-301: business.blockrun.ai seller-listing feasibility research record
**EARS**: WHEN the investigation into whether Franklin can list a skill/gig for sale on
`business.blockrun.ai` (BlockRun's own hosted marketplace, distinct from the P2P gig board this
feature builds) is complete, THE SYSTEM SHALL produce a written research record, committed under
`.vcsdd/features/anicca-agent-economy/evidence/`, that states:
(a) whether a seller/listing API or code path exists for Franklin to offer work FOR SALE to this
marketplace's existing buyers (as distinct from `BlockRunAI/Franklin` PR#83's buyer-side
`agent_talent` tool, which makes Franklin a BUYER on that marketplace, not a seller);
(b) the fee/take-rate structure, if discovered;
(c) which side — the marketplace or Franklin itself — holds the Coinbase CDP dependency observed in
PR#83, and whether that dependency would touch Franklin's own wallet/KYC surface (a human-zero risk
check);
(d) a rough implementation-effort estimate (e.g. a small number of size/complexity buckets) if a
viable path exists;
(e) an explicit recommendation — pursue / deprioritize / blocked-by-X — compared against the
self-built P2P gig board's own external-inflow requirement (SPEC.md §8 item ④, "Bindu/x402-sell
外部向け").

**Edge Cases**:
- No seller-side API or code path exists at all at research time: this MUST be recorded as a
  definitive negative finding (not left as "unknown" or silently postponed), together with the
  concrete evidence checked (repo search terms used, files/docs read, any public API surface
  inspected) so the negative claim is falsifiable/re-checkable later.
- A seller-listing path is found but REQUIRES a marketplace-side Coinbase CDP account or KYC step
  that would need to be created/held by a human: this MUST be flagged as human-zero-violating in
  the recommendation (marked "blocked", not "adopt"), even if the path is otherwise technically
  straightforward.
- The upstream repo/PR state changes before or during this research (open-source repo — PR#83 or
  related PRs may be merged, closed, or superseded): the record MUST note the observed PR/branch
  state AT THE TIME OF WRITING with a timestamp, not assume the state is permanent.

**Acceptance Criteria**:
- The research record file exists under `evidence/` and contains all five items (a)–(e) above,
  each with at least one concrete piece of evidence (a quoted line, a file path, an API response, or
  an explicit "not found, here is what I checked" statement) — no item may be left as a bare
  assertion with no supporting evidence.
- The record's recommendation item (e) explicitly compares this channel's readiness against the
  self-built gig board's current witness status (SPEC.md §9.6), so the finding is directly usable
  for prioritizing the next increment.

### REQ-302: Research spike does not gate the parallel witness track
**EARS**: WHILE the REQ-301 research is in progress, THE SYSTEM SHALL NOT pause, block, or make a
precondition of the self-built P2P gig board's witness effort (SPEC.md §9.6, observing automaton and
Franklin autonomously transacting) on the completion of this research — the two tracks proceed
independently, and REQ-301's output is used only to inform the relative PRIORITY of a possible
future increment, not to unblock or gate any currently in-flight work.

**Edge Cases**:
- If the research concludes a seller-listing path is fast and low-effort, that MAY justify
  reprioritizing a future sprint toward it, but this requirement itself creates no new
  implementation obligation beyond producing the REQ-301 record — it does not, by itself, authorize
  or require starting the `business.blockrun.ai` integration work.

**Acceptance Criteria**:
- No change proposed by this increment introduces a dependency (code, gate, or sequencing rule)
  from the gig-board witness effort onto the completion of REQ-301's research record.
