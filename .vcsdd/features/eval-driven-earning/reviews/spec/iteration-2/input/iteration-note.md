---
feature: eval-driven-earning
phase: 1c
iteration: 2
builderRole: vcsdd-builder
priorVerdict: FAIL (iteration-1, 13 findings: 6 critical, 4 high, 3 medium)
---

# Spec Revision Note — iteration-2 (post iter-1 FAIL)

All 13 findings from the iteration-1 adversary verdict have been addressed. Summary below.

---

## Critical Fixes (6)

### FIND-001 + FIND-003 — INV-7 dangling reference; contradictory kill-switch

**Root cause:** INV-7 does not exist in the skeleton. REQ-S5 invented a `survival-bankruptcy`
self-recover reason with no Group-J handler and falsely claimed it triggered REQ-B4.

**Fix applied (behavioral-spec.md):**
- All INV-7 references replaced with INV-8 (platform-api-verified settled payout gate,
  which IS defined in the skeleton at earnings.jsonl `platform_api_response_sha256`).
- REQ-S5 rewritten: isSolvent=False now appends an ADVISORY `reason: "survival-insolvent"` row
  to lessons.jsonl ONLY. No `loop.disabled` write. No `self-recover.sh survival-bankruptcy` call.
  No `survival-bankruptcy` Group-J handler invented.
- B4 (inside loop-roi.sh) remains the SOLE kill-switch trigger.
- Relationship between thresholds documented: isSolvent fires at cost > 1× income (advisory,
  lower threshold); B4 fires at cost > 5× income (terminal). Same source data, same FX.
- Integration table updated: "B4 → triggered by isSolvent=False" removed; replaced with
  "survival ledger advisory signal feeds lessons.jsonl; B4 remains sole kill-switch owner".

### FIND-002 — income USDC-only kills JPY-settling earners

**Root cause:** `income_usdc = cumulative_usdc_earned` zeroed every JPY earner permanently.

**Fix applied (behavioral-spec.md):**
- Normalized income to USD: `income_usd = (cumulative_jpy_earned / FX_USDJPY) + cumulative_usdc_earned`.
- All `cost_usdc`/`income_usdc`/`net_usdc` renamed to `cost_usd`/`income_usd`/`net_usd` throughout.
- survival.json schema updated accordingly.
- REQ-S2(c) now converts BOTH currency streams via FX.
- EDGE-S2b (which codified the bug) deleted.
- Mixed-currency acceptance criterion added (¥1500 + 0.5 USDC → income_usd=10.5 at FX=150).

### FIND-004 — cost double-FX (~150× error) and wrong acceptance number

**Root cause:** REQ-S1(d) divided by FX_USDJPY but REQ-B2 rates are ALREADY in USD/Mtok.

**Fix applied (behavioral-spec.md):**
- REQ-S1(d) formula: `cost_usd = (tokens_in × rate_in + tokens_out × rate_out + thinking × rate_out) / 1_000_000`.
  No FX division. Rates are USD/Mtok; dividing by 1e6 yields USD directly.
- Acceptance value corrected: `(1000×3 + 500×15 + 200×15) / 1e6 = 13500 / 1e6 = 0.0135 USD`.
- EDGE-S1c updated (FX irrelevant to REQ-S1; only REQ-S2 converts from JPY).
- REQ-S2(b) retains `cost_usd = cumulative_token_cost_jpy / FX_USDJPY` (skeleton stores in JPY).
- Both paths now consistent: S1 measures per-message USD directly; S2 converts cumulative JPY via FX.

### FIND-005 + FIND-006 — decideActivity pure but needs explore-quota state + randomness

**Root cause:** explore quota requires rolling-100-wake history (file read) and stochastic
draws (random) — both banned inside a pure function.

**Fix applied (behavioral-spec.md):**
- New signature: `decideActivity(menu, bandit_stats, explore_epsilon, budget, config)`.
- `BanditStats = {recent_explore_count: int, total_recent_wakes: int}` — INJECTED by effectful
  shell (reads tail-100 of menu-bandit.jsonl, which now includes a `mode` field per row).
- Decision rule is fully deterministic: `explore_due = recent_explore_count < floor(epsilon × min(total+1, 100))`.
- No RNG, no file reads inside the pure function.
- "Thompson Bayesian" mislabel removed from REQ-M2. Selection is epsilon-greedy (greedy-max on
  posterior mean). Arm update is Beta-distribution posterior update (increments clip to [0,1]).
- PROP-DA4 and PROP-DA4b in verification-architecture.md verify the injected-counter approach.

### FIND-010 — trading-polymarket grandfathered into exploit without curation

**Root cause:** EDGE-M1a bootstrap listed trading-polymarket with admitted_at_ts=null; after
one explore wake novelty_tried flipped true, making it exploit-eligible with real wallet access.

**Fix applied (behavioral-spec.md):**
- trading-polymarket removed from the bootstrap default list entirely.
- EDGE-M1a: bootstrap entries use `(alpha=1, beta=1, admitted_at_ts=null)` and auto-route to
  curation (REQ-CU1) on first pass; exploit-ineligible until curation completes.
- REQ-DA2 updated: entries with `admitted_at_ts is None` are NEVER exploit-eligible (removed
  the `novelty_tried==False` conjunction; null admitted_at_ts blocks exploit permanently).

---

## High Fixes (4)

### FIND-008 — rubricScore has no verifiable_result input; Verifier's Law untied

**Fix applied (behavioral-spec.md + verification-architecture.md):**
- `rubricScore` signature now includes `verifiable_result: Optional[Literal["PASS","FAIL","NOT_APPLICABLE"]] = None`.
- Precedence order codified inside the pure function: verifiable PASS → immediate PASS;
  verifiable FAIL → immediate HARD_FAIL; then deliverable check; then weighted score.
- PROP-EV3 / PROP-EV3f updated to test `rubricScore(...)` directly (Tier 0, not Tier 2),
  replacing the `rubricEval` phantom function.

### FIND-009 — curation sandbox mocks all payouts; "earns via verifiable payout" unverifiable

**Fix applied (behavioral-spec.md):**
- REQ-CU3 now has a two-step process:
  (a) Payout endpoint probe (REAL HTTP call, not mocked): skill must declare `payout_api_check:`
      in SKILL.md frontmatter; curation gate issues a real read-only HTTP request and checks
      `reachable=true` (any response proves the endpoint exists).
  (b) Adversary review with updated evaluation_criteria: "declares a payout_api_check endpoint
      listed in payout-endpoint-allowlist.json AND endpoint probe returned reachable=true".
- Missing `payout_api_check` field → automatic curation FAIL.
- Unreachable endpoint → curation FAIL.

### FIND-007 — signature drift between 1a and 1b

**Fix applied (both files):**
- Canonical signatures defined in behavioral-spec.md (1a) and aligned exactly in
  verification-architecture.md (1b):
  - `rubricScore(..., verifiable_result)` — 5-param form consistent across both.
  - `calibrationDrift(scores, realized_usd, min_pairs=10)` — `window_secs` dropped from 1a
    signature (windowing is caller-side); 1b already had this form.
  - `updateBanditArm(arm, realized_usd, usdc_scale)` — both files now match.
  - `decideActivity(menu, bandit_stats, explore_epsilon, budget, config)` — new form in both.
  - All `realized_usdc` renamed to `realized_usd` for currency consistency.

---

## Medium Fixes (3)

### FIND-011 — alpha cap contradiction (uncapped formula vs capped edge case)

**Fix applied (behavioral-spec.md):**
- REQ-M2(a) rewritten as the canonical formula:
  `increment = clip(realized_usd / usdc_scale_factor, 0.0, 1.0)`.
  `alpha_new = alpha + increment`, `beta_new = beta + (1.0 - increment)`.
- The cap is now the DEFINITION, not an exception. EDGE-M2a rewritten to note it is
  subsumed by the main formula.

### FIND-012 — window_secs in calibrationDrift but no timestamps in signature

**Fix applied (behavioral-spec.md + verification-architecture.md):**
- `window_secs` dropped from `calibrationDrift` pure-function signature.
- EDGE-X3 updated: effectful caller reads calibration.jsonl, filters by `window_ts` field,
  and passes pre-windowed lists to the pure function. Windowing responsibility is CALLER-SIDE.

### FIND-013 — integration test asserts 10/10 exploit, contradicts mandatory explore quota

**Fix applied (verification-architecture.md):**
- Step 2 of the losing-arm-retired test updated: "arm-B selected in AT LEAST 9 of 10 wakes".
- Added assertion: "at least 1 of 10 wakes has mode=='explore' (explore quota floor)".
- bandit_stats updated after each result in the loop, demonstrating the injection mechanism.

---

## Scope preserved

The following skeleton groups are explicitly NOT touched by these fixes:
- Group A self-heal, Group B ROI tracking (loop-roi.sh is the sole loop.disabled owner),
- Group C self-improve, Group D cross-learn, Group E adversary-daily, REQ-J8 anti-human-touch.
- INV-8, INV-11, INV-12, INV-13 unchanged in skeleton.
- REQ-B4 kill-switch predicate unchanged; this spec only adds an advisory layer below it.
