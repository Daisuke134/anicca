# Behavioral Spec — anicca-agent-economy (Phase 1a)

**feature**: anicca-agent-economy · **mode**: strict · **increment**: gig-board concurrency
hardening + bootstrap-reserve catalog eligibility gate + business.blockrun.ai seller-channel
research spike · **日付**: 2026-07-07

## Scope of this increment (read first)

`specs/SPEC.md` is this feature's design-log SSOT. P0 (self-funded separation), P1 (earn>spend
fail-closed guard), P2.1 (self-host x402 facilitator), and P2.2's core gig-board mechanics (post →
take → deliver → verify_and_pay → gasless payout, poster-auth, per-gigId locking, ERC-8004
lifecycle enforcement) are **already implemented and adversary-verified** — see
`reviews/p2.2/verdict.md` (rounds 1–2) and `evidence/p2.2-security-fixes*.md` (round 3). This spec
does **not** re-specify any of that. It formalizes, in EARS form with testable acceptance criteria,
exactly three NEW deltas so they can go through a fresh Phase 2/3 verification cycle of their own:

- **REQ群A** (REQ-101..103): close the two residual concurrency gaps the round-2 adversary
  documented (lock-staleness theft from a live holder; the shared `state/gigs.json` file racing
  across different gigIds) — codifying the TARGET behavior regardless of whatever the current
  on-disk code already attempts, so a fresh adversary pass has a real spec to check it against.
- **REQ群B** (REQ-201..203): a new bookkeeping-only catalog eligibility gate that hides
  capital-risking earn slots from a broke instance's tool menu until it clears a reserve floor.
- **REQ群C** (REQ-301..302): a research spike (not an implementation) into whether
  `business.blockrun.ai` offers Franklin a seller-side listing path, to compare against the
  self-built P2P gig board as the external-inflow proof for SPEC.md §8 item ④.

## Purity boundary analysis (overview — file/function detail lives in verification-architecture.md)

| Concern | Classification | Why |
|---|---|---|
| Lock staleness decision (`is this lock file abandoned?`) | **Pure core (target)** | A boolean predicate over `(nowMs, mtimeMs, staleMs)` — no I/O once its inputs are supplied. Currently inlined inside `lib/lock.mjs`'s impure `acquire()`; this increment's acceptance criteria are written so this predicate is directly unit-testable (extracted or exercised in isolation), not only provable via real filesystem timing. |
| Lock acquisition/release/heartbeat (`fs.open('wx')`, `fs.stat`, `fs.unlink`, `fs.utimes`, `setInterval`) | **Effectful shell** | Real filesystem + wall-clock side effects; POSIX-atomicity is the actual safety mechanism. |
| Board mutation (`store.mjs`'s `applyPost`/`applyTake`/`applyDeliver`/`applyVerifyAndPay`) | **Pure core (existing, unchanged by this increment)** | Already a pure state-transition module; this increment does not touch it, only the read/lock/write plumbing around it. |
| Board persistence (`lib/persist.mjs`'s `loadState`/`saveState`, `gig.mjs`'s `applyAndSave`) | **Effectful shell** | Full-file read/write; the safety property this increment specifies (REQ-102) is about WHEN this shell code re-reads relative to a concurrent write, which is why it needs its own acceptance criteria even though the mutation logic itself stays pure. |
| Catalog eligibility filter (new, REQ-201/202) | **Pure core (new)** | `filterCatalog(balanceUsdc, allSlotNames, riskTagOf, reserveThresholdUsdc) → string[]` — deterministic set arithmetic over already-fetched inputs, no I/O, directly analogous to the existing `tier.mjs::selectTier`. |
| Registry read + balance fetch + wiring the filtered catalog into the prompt (`runtime/loop/index.mjs`) | **Effectful shell** | `fs.readFile(registry.json)` + RPC balance read + threading the result into `assembleContext`/`buildSystemPrompt`. |
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

---

### REQ-201: Capital-risk catalog restriction below the bootstrap reserve
**EARS**: WHILE an instance's realized liquid balance is below its configured
`BOOTSTRAP_RESERVE_USDC` threshold, THE SYSTEM SHALL exclude capital-risking earn slots (e.g.
`hl_trade`, `token_launch`, and any other slot tagged as capital-risking) from the catalog and
active-slot list surfaced to the model for that wake, presenting only slots that carry no capital
risk to the instance's own treasury (e.g. `economy/gig`, `economy/ubi`, `cook`, `self/*`, `report`,
and any other slot explicitly tagged non-risking).

**Design principle (must hold, verified structurally not just behaviorally)**: this filter is a
deterministic, numeric bookkeeping gate over WHICH options are offered — a risk-guardrail /
treasury-safety layer, analogous to the existing `tier.mjs::selectTier` balance-based model
selection already in this codebase. It MUST NOT encode any preference, ranking, score, or
recommendation among the slots that remain after filtering, and MUST NOT make or bias any judgment
about task content, strategy, or which remaining slot the model "should" pick. Once the eligible
set is computed, slot selection, task parameters, and `ANICCA_ARGS` remain entirely the model's own
decision, exactly as today. This is why the filter is compliant with this project's hard rule that
the model — not hardcoded regex/if-else — makes judgment calls: the code only narrows the
**objective, numeric** option space (a bookkeeping fact: "is realized balance ≥ $X"), never the
**subjective** choice within it.

**Edge Cases**:
- Balance is exactly equal to `BOOTSTRAP_RESERVE_USDC`: defined as "at or above" the threshold, so
  the full catalog is shown (the restriction applies strictly *below* the threshold, not
  inclusive of it).
- `BOOTSTRAP_RESERVE_USDC` is unset or fails to parse as a finite non-negative number: falls back to
  a documented safe default value; the gate is never silently disabled by misconfiguration.
- The balance fetch itself fails or returns a non-finite/negative value (mirrors
  `tier.mjs::selectTier`'s existing NaN/Infinity/negative handling): treated as below-threshold
  (fail-closed / conservative), consistent with the existing tier-selection pattern in this
  codebase.
- A slot that exists in `registry.json` with `status: "live"` but has no explicit risk tag: defaults
  to being treated as capital-risking (excluded while below threshold) until a maintainer explicitly
  tags it as non-risking — fail-closed by default, never fail-open by omission.
- Every currently-live slot happens to be tagged risky (e.g. a misconfiguration): the `sleep`
  meta-tool and any always-available non-earn slot (e.g. `report`, `cook`) remain available; the
  gate must never produce an empty actionable toolset for the model.

**Acceptance Criteria**:
- Given a balance strictly below the threshold, the computed catalog/active-slot list contains only
  slots not tagged capital-risking.
- Given a balance at or above the threshold, the computed catalog/active-slot list is identical to
  the unfiltered live-slot list (no slot is ever removed once above threshold).
- The filtering function takes already-fetched inputs (balance, slot names, risk tags, threshold)
  and returns a plain list with no ordering/score metadata attached.

### REQ-202: Automatic, non-sticky restoration once above the reserve
**EARS**: WHEN an instance's realized liquid balance rises to at or above
`BOOTSTRAP_RESERVE_USDC`, THE SYSTEM SHALL restore the full live catalog on the very next wake, with
no manual reset step and no persisted "still restricted" flag surviving the balance crossing the
threshold.

**Edge Cases**:
- Balance oscillates around the threshold across consecutive wakes (e.g. $4.99 → $5.01 → $4.98):
  the gate is recomputed fresh from the CURRENT wake's balance every time, with no hysteresis or
  sticky memory of a prior wake's restricted state — this is accepted behavior for this increment
  (not a bug), documented explicitly so a future contributor does not "fix" it into stateful
  hysteresis without a new requirement.
- The restored (above-threshold) catalog must be byte-for-byte the same slot set the instance would
  have seen had it never dropped below the threshold (no slot permanently lost due to having been
  filtered once).

**Acceptance Criteria**:
- The filter is a pure function of the CURRENT wake's balance and the current live-slot list; it
  holds no state across wakes.
- A balance transition from below-threshold to at/above-threshold between two consecutive wakes
  results in the very next wake's catalog being the full, unfiltered live-slot list.

### REQ-203: Design-constraint requirement — bookkeeping only, never judgment
**EARS**: WHERE this increment filters the model's available catalog, THE SYSTEM SHALL implement
that filter exclusively as arithmetic over objective, already-known numeric facts (realized
balance, a configured threshold, and a per-slot risk tag that a human/maintainer sets in
`registry.json`, not one the code infers at runtime), and SHALL NOT implement, alongside or instead
of it, any regex/keyword-based classification of task content, any scoring/ranking of the remaining
options, or any steering text that tells the model WHICH of the remaining options to prefer.

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
