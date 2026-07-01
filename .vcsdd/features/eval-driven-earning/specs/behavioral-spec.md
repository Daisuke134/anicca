---
feature: eval-driven-earning
phase: 1a
mode: lean
sources:
  - HKUDS/ClawWork (8.2k★) — TrackedProvider real-cost + survival ledger + decide_activity explore/exploit + rubric-judge-with-override
  - benchflow-ai/awesome-evals (608★) — pass@k / pass^k vocabulary, Verifier's Law ("verifiable > judgeable"), calibration-drift
  - garylab/MakeMoneyWithAI — auto-refreshing opportunity radar cron pattern
  - earn-shared-skeleton/specs/behavioral-spec.md (v2) — REQ-B2 per-model rates, REQ-B4 kill-switch, REQ-H1 novelty quota, REQ-F1 self-recover, INV-7 on-chain reward, INV-11 token kill-switch, sprint-2 proactive-loop + menu.json
  - anicca-project/docs/superpowers/specs/2026-06-30-earn-slots-daily-loop-master.md §EVAL-DRIVEN EARNING ARCHITECTURE
integration:
  extends: earn-shared-skeleton
  does_not_replace:
    - Group A self-heal (loop-healthcheck.sh)
    - Group B ROI tracking per-pass (loop-roi.sh) — TrackedProvider improves its measurement precision, not its schema
    - Group C self-improve / Reflexion (loop-improve.py)
    - Group D cross-learn bot2bot
    - Group E adversary-daily
    - REQ-J8 anti-human-touch invariant
    - INV-7 on-chain reward gate
  integrates_at:
    - proactive-loop.sh step 5 ("pick highest ROI") → replaced by decideActivity output
    - loop-roi.sh token_source measurement → improved by TrackedProvider (REQ-S1)
    - loop.disabled kill-switch (REQ-B4) → triggered by isSolvent=False (REQ-S5)
    - menu.json entries (sprint-2 schema) → extended with bandit arm fields (REQ-M1)
    - TRAP-6 sandbox isolation (skeleton) → formalised as curation gate (Group CU)
---

# Behavioral Specification — eval-driven-earning (Phase 1a)

## Purpose

Adds the EVAL / DECISION SPINE on top of the earn-shared-skeleton.  The skeleton already handles
self-heal, ROI tracking, Reflexion self-improve, cross-learn, adversary review, and no-human
escalation.  This feature provides what the skeleton lacks:

1. A **survival ledger** (ClawWork TrackedProvider) that measures real cost vs real income and
   computes `net = income − cost` as the fitness signal for every slot.
2. A formalized **options menu** where each entry carries a live bandit arm (expected USDC/wake).
3. A pure **decideActivity** function that selects exploit vs explore each wake, replacing the
   skeleton's unspecified "pick highest ROI × probability" step 5.
4. A **rubric eval quality gate** that scores a candidate action BEFORE committing tokens,
   anchored to realized USDC via a calibration drift check.
5. A **curation gate** that verifies any new earn skill actually earns before it enters the menu,
   so spawned children bootstrap on vetted tools.
6. A **self-search radar** that discovers new earn opportunities and proposes them through the
   curation gate.

## Integration Points with earn-shared-skeleton

| skeleton symbol | how this feature uses it |
|---|---|
| REQ-B2 per-model rate table | TrackedProvider (REQ-S1) reads SAME rates to compute per-message cost_usdc |
| `~/loops/<slot>/cumulative.json` | survival.json recomputes from `cumulative_token_cost_jpy + cumulative_usdc_earned` |
| `~/loops/<slot>/roi.jsonl` `token_source` field | TrackedProvider promotes this field from "estimated" to "measured" where possible |
| REQ-B4 loop.disabled kill-switch | REQ-S5 writes `loop.disabled` when `isSolvent(ledger) == False` past grace |
| REQ-H1 novelty quota (`ceil(0.1 × max_apply_per_pass)`) | `decideActivity` novelty_quota parameter copies this floor exactly |
| `~/loops/<slot>/menu.json` (sprint-2 schema) | this feature adds bandit arm fields per REQ-M1 without removing existing fields |
| proactive-loop.sh step 5 | replaced: step 5 now calls `decideActivity` and acts on its `pick` |
| TRAP-6 sandbox isolation | curation gate (Group CU) formalises this with adversary PASS requirement |

## New Tracked Quantities

These are files OWNED by this feature (not defined in skeleton):

| path | semantics | writer | reader |
|---|---|---|---|
| `~/loops/<slot>/survival.json` | per-slot survival state; recomputed every wake from cumulative.json | TrackedProvider + survivalLedger.recompute() | decideActivity, isSolvent, REQ-S5 kill-switch check |
| `~/loops/<slot>/calibration.jsonl` | append-only; one row per scored action: `{ts, action_id, rubric_score, realized_usdc, window_ts}` | rubric-judge.py after outcome received | calibrationDrift() |
| `~/loops/<slot>/menu-bandit.jsonl` | append-only bandit arm update log; one row per wake outcome: `{ts, entry_id, realized_usdc, alpha_new, beta_new}` | updateBanditArm() caller (proactive-loop step 7) | bandit reconstruction on crash-restart |
| `~/anicca/state/menu-curation.jsonl` | append-only; skills pending curation review: `{ts, skill_id, source, status: "pending"\|"pass"\|"fail"\|"admitted"}` | curation-gate.sh | curation gate admission check |
| `~/anicca/state/discovery.jsonl` | append-only; discovered opportunities: `{ts, source, url, description, eval_score, proposed_to_curation: bool}` | discovery-radar.sh | curation gate |

### survival.json schema (version 1)

```jsonc
{
  "slot": "<slot>",
  "cost_usdc": <float>,            // cumulative_token_cost_jpy / FX_USDJPY (from cumulative.json + fx.json)
  "income_usdc": <float>,          // cumulative_usdc_earned (from cumulative.json, INV-7 verified)
  "net_usdc": <float>,             // income_usdc - cost_usdc  (= netWorth output)
  "loss_start_ts": <int|null>,     // unix ts when net_usdc first went negative; null if net >= 0
  "last_recomputed_ts": <int>,     // unix ts of most recent recompute
  "wake_count": <int>,             // count of completed wakes (= roi.jsonl row count)
  "schema_version": 1
}
```

### menu.json entry schema — bandit arm fields (added by this feature)

Each entry in `~/loops/<slot>/menu.json` SHALL include these additional fields alongside
the skeleton sprint-2 fields (categories, ROI heuristics, novelty quota):

```jsonc
{
  "id": "<unique entry id, e.g. trading-polymarket>",
  "label": "<human-readable>",
  "expected_usdc_per_wake": <float>,  // posterior mean of Beta(alpha, beta)
  "alpha": <float>,                   // Beta distribution alpha (successes + 1)
  "beta": <float>,                    // Beta distribution beta (failures + 1)
  "attempt_count": <int>,             // total wakes where this entry was picked
  "pass_count": <int>,                // wakes where realized_usdc > 0
  "novelty_tried": <bool>,            // true = has appeared ≥1 time in applied.jsonl
  "cost_estimate_usdc": <float>,      // estimated token cost to run one wake on this arm
  "admitted_at_ts": <int|null>,       // unix ts of curation admission; null = curated before this feature
  "schema_version": 1
}
```

`expected_usdc_per_wake` = `alpha / (alpha + beta)` × `usdc_scale_factor`, where
`usdc_scale_factor` is the 90th-percentile observed `realized_usdc` over the slot's
history (updated each wake; initial value = 1.0 USDC).

---

## EARS-Format Functional Requirements

### Group SS — Survival Ledger

`~/anicca/skills/_shared/eval_spine.py` owns the pure functions in this group.
`~/anicca/skills/_shared/tracked-provider.sh` owns the effectful measurement wrapper.

#### REQ-S1 — TrackedProvider: real per-message token cost

WHEN the proactive-loop invokes a claude (or ClawRouter) LLM call within a slot's wake,
THE SYSTEM SHALL wrap that call in the TrackedProvider which:
(a) extracts ACTUAL `{tokens_in, tokens_out, thinking_tokens}` from the response
    (claude API's usage JSON body, or the session pane footer counter `↓ <N>k tokens`),
    NOT byte-count estimates,
(b) identifies the `model_id` from the call's `--model` flag or ClawRouter header,
(c) REFUSES to record the usage row if `model_id` is absent from the skeleton's
    REQ-B2 per-model rate table — writes `{event: "cost-error", reason: "unknown-model"}`
    to `~/loops/<slot>/events/<pass_id>.jsonl` and delegates escalation to skeleton
    REQ-F1 (`self-recover.sh <slot> unknown-model-cost <model_id>`),
(d) computes `cost_usdc = (tokens_in × rate_input[model_id] + tokens_out × rate_output[model_id]
    + thinking_tokens × rate_output[model_id]) / 1_000_000 / FX_USDJPY`,
    using the REQ-B2 per-model rate table (all rates are USD/Mtok; dividing by FX_USDJPY
    converts to USDC since 1 USDC ≈ 1 USD for this computation),
(e) appends `{ts, model_id, tokens_in, tokens_out, thinking_tokens, cost_usdc}` to
    `~/loops/<slot>/events/<pass_id>.jsonl` as an `event: "cost"` row,
(f) on pane-footer-only fallback (= measurement not available from API response body),
    sets `token_source: "estimated"` in the row and applies the skeleton REQ-B6 penalty.

**Edge Cases:**
- **EDGE-S1a** Claude invoked without `--model` flag: TrackedProvider reads the model from the
  pane footer's model banner ("Model: sonnet") before applying the rate table; on parse failure,
  falls back to "sonnet" (most expensive safe assumption) and sets `token_source: "estimated"`.
- **EDGE-S1b** thinking_tokens absent from response (non-extended-thinking model): recorded as
  0 without error; cost computed from tokens_in + tokens_out only.
- **EDGE-S1c** FX_USDJPY file missing (skeleton fx.json not yet populated): defaults to 150.0
  and logs a warning; does NOT block the cost row.

**Acceptance Criteria:**
- A unit test verifies that TrackedProvider with model_id="sonnet", tokens_in=1000,
  tokens_out=500, thinking_tokens=200, FX=150 produces
  `cost_usdc = (1000×3 + 500×15 + 200×15) / 1_000_000 / 150 ≈ 0.000207`.
- An unknown model_id triggers a REQ-F1 `self-recover.sh` call (verified by subprocess spy),
  does NOT append to events.jsonl, and does NOT silently record cost=0.

---

#### REQ-S2 — Survival state file: schema and write semantics

WHEN a slot's wake completes (= `loop-roi.sh` end-of-pass row has been written),
THE SYSTEM SHALL atomically rewrite `~/loops/<slot>/survival.json` by:
(a) reading `cumulative.json.cumulative_token_cost_jpy` (skeleton-maintained) and
    `cumulative.json.cumulative_usdc_earned` (INV-7 verified),
(b) computing `cost_usdc = cumulative_token_cost_jpy / FX_USDJPY`,
(c) computing `income_usdc = cumulative_usdc_earned`,
(d) setting `loss_start_ts` = existing value if `net_usdc < 0` already, else the current
    unix timestamp if `net_usdc < 0` for the first time, else `null`,
(e) incrementing `wake_count` by 1,
(f) writing to a tmp file and `mv`-renaming (atomic) per skeleton NFR-2.

`survival.json` is recomputed from source (`cumulative.json`) each wake, not
accumulated incrementally, so crash-restart is loss-free.

**Edge Cases:**
- **EDGE-S2a** `cumulative.json` does not exist (slot brand-new, zero wakes): survival.json
  is written with `cost_usdc=0.0`, `income_usdc=0.0`, `net_usdc=0.0`, `loss_start_ts=null`,
  `wake_count=0`.
- **EDGE-S2b** FX converts JPY cost to a cost_usdc that exceeds income_usdc on wake 1 (= first
  wake burned tokens, zero income): `loss_start_ts` is set to the current wake's ts, NOT the
  slot's `first_seen_ts` — bankruptcy grace clock starts from first income deficit, not from
  slot birth.
- **EDGE-S2c** Two proactive-loop ticks overlap (skeleton NFR-3 flock guard prevents concurrent
  execution, but if flock fails): second writer reads the tmp file from the first writer and
  `mv` races — last writer wins; no corruption possible because each recomputes from source.

**Acceptance Criteria:**
- survival.json written with correct schema after every wake (schema validated against
  JSON Schema by `test_survival_schema.py`).
- Crash-simulation test: delete survival.json mid-process, verify it is regenerated identically
  from cumulative.json on next wake.

---

#### REQ-S3 — Pure function: `netWorth`

THE SYSTEM SHALL expose a pure function `netWorth(cost_usdc: float, income_usdc: float) → float`
that returns `income_usdc − cost_usdc`.

**Constraints:**
- `netWorth` is total: defined for all float inputs including negative (overpayment or
  refund edge cases).
- `netWorth` has no side effects, reads no files, makes no system calls.

**Edge Cases:**
- **EDGE-S3a** `cost_usdc = income_usdc = 0.0` → returns 0.0.
- **EDGE-S3b** `income_usdc < 0` (API refund, rare): returns a value < -cost_usdc; this
  is mathematically correct and does NOT trigger isSolvent=False on its own — isSolvent
  gates on net_usdc being PERSISTENTLY negative past grace.

**Acceptance Criteria:**
- `netWorth(5.0, 3.0) == -2.0`
- `netWorth(0.0, 10.0) == 10.0`
- `netWorth(0.0, 0.0) == 0.0`
- Property test (Hypothesis): `netWorth(c, i) == -netWorth(i, c)` for all float pairs.

---

#### REQ-S4 — Pure function: `isSolvent`

THE SYSTEM SHALL expose a pure function
`isSolvent(net_usdc: float, loss_start_ts: Optional[int], grace_window_secs: int, now_ts: int) → bool`
that returns:
- `True` if `net_usdc >= 0` (regardless of other parameters),
- `True` if `net_usdc < 0` AND `loss_start_ts is None` (net just went negative this wake;
  `loss_start_ts` will be set by REQ-S2 after this call — caller passes the PRE-recompute value),
- `True` if `net_usdc < 0` AND `(now_ts - loss_start_ts) < grace_window_secs`,
- `False` if `net_usdc < 0` AND `(now_ts - loss_start_ts) >= grace_window_secs`.

Default `grace_window_secs` SHALL be `7 × 86400` (= 7 days), matching skeleton REQ-B4's
grace window for dimensional consistency.

**Edge Cases:**
- **EDGE-S4a** `grace_window_secs = 0` (testing only): returns False immediately on first
  negative net_usdc — useful for unit tests that need deterministic bankruptcy.
- **EDGE-S4b** `now_ts < loss_start_ts` (clock skew): treats as `elapsed = 0`, returns True.
- **EDGE-S4c** `net_usdc = -0.0` (IEEE float negative zero): treated as `>= 0`, returns True.

**Acceptance Criteria:**
- `isSolvent(-1.0, loss_start=T, grace=7d, now=T+6d) == True`
- `isSolvent(-1.0, loss_start=T, grace=7d, now=T+7d+1) == False`
- `isSolvent(+0.01, ...) == True` (any positive net)
- Property test: `isSolvent(net >= 0, ...) == True` for all non-negative net values.

---

#### REQ-S5 — Bankruptcy signal: bridge to kill-switch

WHEN `isSolvent(ledger.net_usdc, ledger.loss_start_ts, GRACE_WINDOW, now_ts) == False`,
THE SYSTEM SHALL call `self-recover.sh <slot> survival-bankruptcy <net_usdc>` (skeleton REQ-F1)
which in turn calls the skeleton's REQ-B4 kill-switch mechanism (writes `loop.disabled`).

THE SYSTEM SHALL pass the survival bankruptcy signal ONLY from the proactive-loop after
`survival.json` has been recomputed (= end of every wake, after REQ-S2 completes) — never
mid-wake.

THE SYSTEM SHALL NOT duplicate the `loop.disabled` creation logic — it delegates to the
skeleton's existing REQ-B4 mechanism.

**Edge Cases:**
- **EDGE-S5a** Skeleton REQ-B4 already tripped `loop.disabled` (cost-JPY ratio exceeded):
  REQ-S5 still calls self-recover.sh; the handler is idempotent (file already exists, no-op).
- **EDGE-S5b** Bankruptcy signal fires but income arrives in the same wake (earnings.jsonl row
  written after roi.jsonl row): REQ-S2's recompute from cumulative.json naturally includes
  the income row; net_usdc may become positive after recompute → isSolvent = True → no
  kill-switch trip.

**Acceptance Criteria:**
- Integration test: set cost_usdc=10.0, income_usdc=0.0, grace=0 seconds → `loop.disabled`
  is created within the same wake.
- Subprocess spy verifies `self-recover.sh` is called exactly once per bankrupt wake.

---

### Group MN — Options Menu

#### REQ-M1 — Menu entry schema with bandit arm

WHEN `~/loops/<slot>/menu.json` is written or updated, THE SYSTEM SHALL ensure every entry
conforms to the bandit arm schema defined in the Tracked Quantities section above, with these
invariants:
- `alpha >= 1.0` and `beta >= 1.0` always (Beta distribution requires positive parameters;
  initialized to (1, 1) = uniform prior for a new arm),
- `pass_count <= attempt_count`,
- `expected_usdc_per_wake == alpha / (alpha + beta) × usdc_scale_factor` (derived; always
  recomputed from alpha/beta, never stored stale).

Existing skeleton sprint-2 fields (categories, ROI heuristics, novelty quota) SHALL be
preserved verbatim alongside the new bandit arm fields.

**Edge Cases:**
- **EDGE-M1a** `menu.json` does not exist (slot brand-new or pre-sprint-2 migration):
  proactive-loop.sh bootstraps a default menu with one entry per active earn type
  (trading-polymarket, bounty-scan, clip, affiliate, video) with (alpha=1, beta=1) priors.
- **EDGE-M1b** An existing entry missing the bandit arm fields (migrated from sprint-2 without
  bandit): migration step initializes missing fields to (alpha=1, beta=1, attempt=0, pass=0,
  novelty_tried=true since it predates this feature).

**Acceptance Criteria:**
- JSON Schema test validates all entries after each write.
- Property test: `expected_usdc_per_wake` always in `[0, usdc_scale_factor]`.

---

#### REQ-M2 — Bandit arm update after wake outcome

WHEN a wake completes and the slot records a pass outcome `realized_usdc >= 0.0`,
THE SYSTEM SHALL update the chosen entry's bandit arm by:
(a) setting `alpha_new = alpha + realized_usdc / usdc_scale_factor` (Thompson Bayesian update
    — fractional alpha increment proportional to normalized USDC earned; 0.0 income = no alpha
    increment = only beta increment below),
(b) setting `beta_new = beta + (1.0 - realized_usdc / usdc_scale_factor).clip(0, 1)`,
(c) incrementing `attempt_count += 1`, `pass_count += 1 if realized_usdc > 0`,
(d) recomputing `expected_usdc_per_wake = alpha_new / (alpha_new + beta_new) × usdc_scale_factor`,
(e) appending `{ts, entry_id, realized_usdc, alpha_new, beta_new}` to
    `~/loops/<slot>/menu-bandit.jsonl` BEFORE updating menu.json (claim-check against duplicate
    update on crash-restart),
(f) atomically rewriting menu.json (tmp + mv).

`updateBanditArm(arm: BanditArm, realized_usdc: float) → BanditArm` SHALL be a pure function
(no side effects) that implements steps (a)-(d); the caller performs steps (e)-(f).

**Edge Cases:**
- **EDGE-M2a** `realized_usdc > usdc_scale_factor` (exceptional earn): alpha increment is
  capped at 1.0 (the formula `realized_usdc / usdc_scale_factor` exceeds 1.0 → clipped to 1.0
  for both alpha and beta calculations).
- **EDGE-M2b** Wake failed mid-pass (proactive-loop exited non-zero): no bandit update for
  that entry (outcome = unknown ≠ 0); attempt_count is NOT incremented; only wakes with a
  determined outcome update the arm.

**Acceptance Criteria:**
- `updateBanditArm({alpha=1, beta=1}, realized_usdc=0)` → `{alpha=1, beta=2}` (no income = pessimistic).
- `updateBanditArm({alpha=1, beta=1}, realized_usdc=0.5*scale)` → `{alpha=1.5, beta=1.5}`.
- Property test: `expected_usdc_per_wake` after N updates equals observed-mean of realized_usdc
  to within the Bayesian shrinkage bound.

---

### Group DA — Decide Activity

#### REQ-DA1 — Pure function: `decideActivity`

THE SYSTEM SHALL expose a pure function:

```python
decideActivity(
    menu: list[MenuEntry],
    novelty_quota: float,       # fraction of wakes that MUST explore (default 0.1 = skeleton REQ-H1)
    budget: Budget,             # FULL | MEDIUM | LIGHT | MINIMAL (from skeleton quota-tracker.py)
    now_ts: int,
) → ActivityDecision
```

where `ActivityDecision` = `{mode: "exploit" | "explore", pick: MenuEntry | None, reason: str}`.

`decideActivity` reads NO files and makes NO system calls — all inputs are passed as arguments.

**Acceptance Criteria:**
- `decideActivity([...], 0.1, FULL, T)` always returns a single ActivityDecision (never raises).
- Property test: for any valid input, `mode` is exactly one of {"exploit", "explore"}.

---

#### REQ-DA2 — Exploit mode selection (pass^k reliability)

WHEN `decideActivity` selects `mode: "exploit"`, THE SYSTEM SHALL pick the `MenuEntry` with the
highest `expected_usdc_per_wake` among entries where `attempt_count >= K_MIN_EXPLOIT` (default
K_MIN_EXPLOIT = 3, = minimum observations before an arm is considered "proven").

Ties SHALL be broken by lower `beta` value (= less pessimistic failure rate).

Entries whose `admitted_at_ts is None` and `novelty_tried == False` SHALL NOT be eligible for
exploit mode selection — they are explore-only until at least one wake has been attempted.

**Edge Cases:**
- **EDGE-DA2a** No entry has `attempt_count >= K_MIN_EXPLOIT` → mode falls back to explore
  unconditionally (all arms are unproven).
- **EDGE-DA2b** `budget == LIGHT` or `MINIMAL` → exploit filter adds `cost_estimate_usdc <= budget_cap`
  (budget cap: LIGHT = 0.01 USDC/wake, MINIMAL = 0.001 USDC/wake); entries above cap are
  excluded from exploit candidates.

**Acceptance Criteria:**
- Given two entries with expected_usdc_per_wake = 0.5 and 0.3, both with attempt_count >= 3,
  exploit selects the 0.5 entry.
- Given only entries with attempt_count < 3, mode is "explore".

---

#### REQ-DA3 — Explore mode with novelty quota

WHEN `decideActivity` selects `mode: "explore"`, THE SYSTEM SHALL prefer entries where
`novelty_tried == False` (= never appeared in the slot's `applied.jsonl`).

THE SYSTEM SHALL enforce the skeleton REQ-H1 novelty quota: the fraction of wakes selecting
`mode: "explore"` SHALL be at least `novelty_quota` (default 0.1) over any rolling window of
100 wakes, tracked via `~/loops/<slot>/menu-bandit.jsonl` mode field.

IF no `novelty_tried == False` entry exists, THE SYSTEM SHALL select the entry with the
LOWEST `attempt_count` among all entries (= least explored arm).

IF `novelty_quota` floor cannot be met because only exploit-eligible entries remain, THE SYSTEM
SHALL log `{reason: "novelty-floor-unmet"}` to `lessons.jsonl` (same as skeleton REQ-H1) and
fall through to exploit selection.

**Edge Cases:**
- **EDGE-DA3a** Multiple `novelty_tried == False` entries → select the one with lowest
  `cost_estimate_usdc` (minimize explore cost per the budget constraint).
- **EDGE-DA3b** Rolling 100-wake history is all explore (e.g., menu just bootstrapped):
  quota is satisfied; no novelty-floor-unmet log.

**Acceptance Criteria:**
- Given a 10-entry menu where 9 have `novelty_tried=True` and 1 has `novelty_tried=False`,
  explore selects the one with `novelty_tried=False`.
- Quota simulation: after 100 synthetically generated wakes with novelty_quota=0.1, at least
  10 wakes have mode="explore".

---

#### REQ-DA4 — Empty-menu and MINIMAL-budget sentinel

WHEN `menu` is empty OR all entries have `cost_estimate_usdc > budget_cap` for the current
`budget`,
THE SYSTEM SHALL return
`ActivityDecision(mode="explore", pick=None, reason="discover-first")`.

proactive-loop.sh SHALL interpret `pick=None` as a trigger to invoke the self-search radar
(REQ-SR1) instead of taking a normal earn action, then exit the wake without income/cost rows
(radar is a meta-action, not a wake).

**Acceptance Criteria:**
- `decideActivity(menu=[], ...) == ActivityDecision(mode="explore", pick=None, reason="discover-first")`.
- Integration test: proactive-loop with empty menu calls discovery-radar.sh and exits 0.

---

### Group EV — Eval Quality Gate

The eval quality gate is implemented in `~/anicca/skills/_shared/rubric-judge.py`.
The pure functions (`rubricScore`, `calibrationDrift`) live in `eval_spine.py`.
The effectful judge invocation (calling claude to score) lives in `rubric-judge.py`.

Integration with skeleton Group I (REQ-I1/I2): the rubric judge extends the skeleton's
proposal-verify and deliverable-verify loops with the calibration layer and Verifier's Law.
It does NOT replace them.

#### REQ-EV1 — Rubric score calculation

WHEN a candidate action is ready for submission or a deliverable is ready for 納品,
THE SYSTEM SHALL call `rubricScore(candidate: CandidateAction, rubric: Rubric) → RubricResult`
where:
- `rubric` is loaded from `~/loops/<slot>/rubric-config.json` for the action's category,
  falling back to a default rubric if the category is absent,
- each rubric entry is `{dimension: str, weight: float, description: str}` with
  `Σ weights == 1.0` (enforced at load time — mis-configured rubric is a fatal load error,
  not a soft warning),
- the LLM judge scores each dimension on [0.0, 1.0],
- `weighted_score = Σ (score_d × weight_d)` over all dimensions.

`rubricScore` takes pre-computed dimension scores as inputs (the LLM judge call is effectful
and happens BEFORE `rubricScore` is invoked); `rubricScore` is the pure aggregation only.

**Edge Cases:**
- **EDGE-EV1a** No rubric-config.json for this slot (brand-new slot): use the global default
  rubric at `~/anicca/skills/_shared/rubric-default.json` (shipped with the framework).
- **EDGE-EV1b** Rubric weights do not sum to 1.0 (misconfiguration): `rubricScore` raises
  `ValueError("weights must sum to 1.0")` and the action is treated as HARD_FAIL.

**Acceptance Criteria:**
- Given rubric `[{dim="quality", weight=0.7, score=0.8}, {dim="relevance", weight=0.3, score=0.5}]`,
  `rubricScore` returns `weighted_score = 0.71`.
- Property test: `weighted_score` ∈ [0.0, 1.0] for all valid inputs.

---

#### REQ-EV2 — Hard missing-deliverable override (auto-fail)

WHEN the rubric for the action's category declares `deliverable_required: true` AND
the candidate action's `deliverable` field is null or points to a non-existent file,
THE SYSTEM SHALL set `RubricResult.verdict = "HARD_FAIL"` and `weighted_score = 0.0`
regardless of any dimension scores — the missing-deliverable override bypasses the weighted
calculation entirely.

`rubricScore` SHALL accept a `has_deliverable: bool` input and apply this logic purely (no
file-system access inside the function).

**Acceptance Criteria:**
- `rubricScore(has_deliverable=False, rubric_requires_deliverable=True, dim_scores=[1.0, 1.0]) → HARD_FAIL`.
- `rubricScore(has_deliverable=True, rubric_requires_deliverable=True, dim_scores=[0.4, 0.6]) → verdict="PASS" with weighted_score=0.5`.

---

#### REQ-EV3 — Verifiable-check priority ("verifiable > judgeable")

Source: benchflow-ai/awesome-evals Verifier's Law — "a verifiable check is always preferred
over an LLM judge score for the same property."

WHEN a verifiable check exists for the candidate's category (listed in
`~/loops/<slot>/rubric-config.json` under `verifiable_checks: [{check_type, tool, assertion}]`),
THE SYSTEM SHALL run the verifiable check FIRST and use its binary pass/fail as the
overriding verdict BEFORE invoking the LLM judge.

ONLY IF no verifiable check exists or all declared verifiable checks raise `NotApplicable`
SHALL the system fall through to the LLM judge.

A verifiable check is NEVER replaced by an LLM judge result; an LLM judge result NEVER
overrides a verifiable-check failure.

**Examples of verifiable checks:**
- For `trading-polymarket`: verify the CLOB order exists on-chain (`eth_getLogs`); pass = order
  confirmed, fail = order not found.
- For `bounty`: verify the PR is merged and Frantic/Dework receipt exists; pass = verifiable
  payout record, fail = no record.
- For `clip`: verify the platform returned a post_id with status=published; pass = confirmed,
  fail = missing post_id.

**Edge Cases:**
- **EDGE-EV3a** Verifiable check tool errors (network down): treated as `NotApplicable`; fall
  through to judge. Never treated as "verifiable fail".
- **EDGE-EV3b** Verifiable check passes but LLM judge scores low: verifiable result wins; the
  action proceeds. Judge score is recorded to calibration.jsonl for future analysis.

**Acceptance Criteria:**
- Integration test: action with verifiable_check=pass scores PASS even if mock judge returns 0.2.
- Integration test: action with verifiable_check=fail scores HARD_FAIL even if mock judge returns 0.9.

---

#### REQ-EV4 — Calibration record

WHEN an action's outcome is determined (= the platform confirms acceptance/rejection or a USDC
payout receipt arrives per INV-7), THE SYSTEM SHALL append to `~/loops/<slot>/calibration.jsonl`:

```jsonc
{
  "ts": <int>,
  "action_id": "<uuid>",
  "rubric_score": <float>,        // the weighted_score at time of submission
  "realized_usdc": <float>,       // actual USDC earned for this action (INV-7 verified; 0 if rejected)
  "outcome_type": "accepted" | "rejected" | "hard_fail_skip",
  "window_ts": <int>              // ts of the wake when the outcome was received
}
```

This row is the calibration dataset for `calibrationDrift`.

**Edge Cases:**
- **EDGE-EV4a** Action was HARD_FAIL skipped (= REQ-EV2 skipped submission): append row with
  `realized_usdc=0.0`, `outcome_type="hard_fail_skip"` — these are valid data points (the judge
  correctly refused a no-deliverable action).
- **EDGE-EV4b** Action submitted but no outcome after 14 days: append row with
  `realized_usdc=null`, `outcome_type="timeout"` — excluded from calibrationDrift calculation.

**Acceptance Criteria:**
- After 10 completed wakes, calibration.jsonl has ≥ 1 row with `realized_usdc > 0` (assuming
  at least one earn action was accepted).
- Schema validation test: every row conforms to the schema.

---

#### REQ-EV5 — Calibration drift check and recalibration flag

Source: benchflow-ai/awesome-evals criteria-drift detection.

THE SYSTEM SHALL expose a pure function:
`calibrationDrift(scores: list[float], realized_usdc: list[float], window_secs: int, min_pairs: int = 10) → DriftResult`
where `DriftResult = {sufficient_data: bool, pearson_r: float | None, drift_detected: bool, threshold: float}`.

The function computes the Pearson correlation coefficient between `scores` and `realized_usdc`
over the rolling window. `drift_detected = True` when `pearson_r < threshold` (default
threshold = 0.3 — judge scores must correlate at least weakly with actual earnings).

WHEN `drift_detected == True`, proactive-loop.sh SHALL:
(a) append `{ts, reason: "calibration-drift", pearson_r}` to `lessons.jsonl`,
(b) halve the rubric's LLM-judge weighting in `rubric-config.json` for the affected categories
    (force more reliance on verifiable checks),
(c) call `self-recover.sh <slot> calibration-drift "<pearson_r>"` (dispatches to skeleton
    REQ-F1 which routes to the MOTHER queue for rubric weight recalibration — no human contact).

WHEN `sufficient_data == False` (< min_pairs non-null pairs in the window), the function
returns `DriftResult(sufficient_data=False, pearson_r=None, drift_detected=False)` — no flag
is raised on insufficient data.

**Edge Cases:**
- **EDGE-EV5a** All realized_usdc are 0.0 (zero earning period): correlation is undefined
  (zero variance in Y); function returns `pearson_r=None`, `drift_detected=False` (not enough
  signal to judge drift — do not penalize the judge for a zero-earn phase).
- **EDGE-EV5b** Perfect correlation (pearson_r = 1.0): drift_detected=False, no action.
- **EDGE-EV5c** Rubric-config.json write fails (disk full): log warning, do not crash; drift
  flag is still recorded in lessons.jsonl.

**Acceptance Criteria:**
- `calibrationDrift(scores=[0.9,0.8,0.7], realized_usdc=[10,8,7], ...) → pearson_r ≈ 1.0, drift=False`.
- `calibrationDrift(scores=[0.9,0.1,0.5], realized_usdc=[0,10,0], ...) → pearson_r < 0.3, drift=True`.
- `calibrationDrift(scores=[...] len=5, ..., min_pairs=10) → sufficient_data=False`.
- Property test: `calibrationDrift` with all identical scores returns `pearson_r=None` (undefined).

---

### Group CU — Curation Gate

Implemented in `~/anicca/skills/_shared/curation-gate.sh`.

#### REQ-CU1 — Curation trigger on new skill proposal

WHEN a new earn skill/option is proposed (via discovery radar REQ-SR3, cross-learn REQ-D1,
or MOTHER bot2bot REQ-J7), THE SYSTEM SHALL:
(a) append a row `{ts, skill_id, source, status: "pending"}` to `~/anicca/state/menu-curation.jsonl`
    BEFORE doing any further evaluation (claim-check: concurrent proposals for the same skill_id
    with status ∈ {"pending","pass"} are silently ignored),
(b) NOT add the skill to any slot's `menu.json` until `status == "admitted"`.

**Edge Cases:**
- **EDGE-CU1a** Same skill_id proposed twice (from different sources concurrently):
  second proposal sees `status: "pending"` in curation.jsonl → silently ignored.
- **EDGE-CU1b** skill_id is a URL (newly discovered repo): normalize to `sha256(url)[:12]`
  as the dedup key.

---

#### REQ-CU2 — Sandbox paper run

WHEN a skill enters curation (`status: "pending"`), THE SYSTEM SHALL run a sandbox paper run:
(a) clone the skill into `.worktrees/curation-<skill_id>/` with read-only mounts (no wallet
    access, no live platform API keys; all payout API calls are intercepted by a mock that
    returns `{payout_id: null, amount: 0}`),
(b) run the skill for one simulated wake (the strongest available model executes the skill
    as if it were a real wake),
(c) capture exit code, any error output, and the events/<pass_id>.jsonl produced.

The paper run verifies the MECHANISM works (skill runs without crashing, emits valid events)
NOT that it earned USDC (sandbox mocks all payouts).

Completion criterion: exit code 0 AND events.jsonl is valid JSON AND no
`event: "cost-error"` rows.

**Edge Cases:**
- **EDGE-CU2a** Skill requires a network call the sandbox does not intercept: the sandbox
  intercepts ALL outbound HTTP via a `HTTPS_PROXY` pointing to a null-returning stub; skill
  that crashes on 000 response = paper run FAIL.
- **EDGE-CU2b** Paper run times out (> 300 seconds): treated as paper run FAIL.

---

#### REQ-CU3 — Adversary PASS requirement

WHEN the sandbox paper run passes (REQ-CU2), THE SYSTEM SHALL spawn a fresh-context Opus
adversary (same mechanism as skeleton REQ-E4 strategy-mutation seam) with manifest:

```jsonc
{
  "reviewType": "curation-gate",
  "skill_id": "<id>",
  "paper_run_events": "<path to events.jsonl>",
  "skill_source": "<path to SKILL.md>",
  "evaluation_criteria": ["earns via verifiable payout endpoint", "no human-touch surfaces", "no spawn-surface drift", "cost_estimate_usdc plausible"]
}
```

The adversary writes a verdict to `~/anicca/.vcsdd/features/eval-driven-earning/reviews/curation-<skill_id>/output/verdict.json`.

THE SYSTEM SHALL update `menu-curation.jsonl` row to `status: "pass"` IFF `overallVerdict == "PASS"`,
else `status: "fail"` with the adversary's findings.

A `status: "fail"` skill is NOT re-evaluated unless it is re-proposed with a new skill_id
(= modified version with a different sha256).

**Acceptance Criteria:**
- A skill whose SKILL.md contains any `human-touch surface` (skeleton REQ-J8 pattern) receives
  `overallVerdict == "FAIL"`.
- A well-formed skill that passes paper run receives a verdict within 3 adversary rounds.

---

#### REQ-CU4 — Menu admission condition

WHEN `menu-curation.jsonl` row for `skill_id` reaches `status: "pass"`, THE SYSTEM SHALL:
(a) add a new MenuEntry (REQ-M1 schema) to EVERY slot's `menu.json` where the skill applies
    (determined by the skill's `applicable_slots: [...]` field in its SKILL.md frontmatter),
(b) set the entry's bandit arm to uniform prior `(alpha=1, beta=1)`,
(c) set `admitted_at_ts = now_ts`,
(d) update `menu-curation.jsonl` row to `status: "admitted"`.

**Acceptance Criteria:**
- After curation PASS for a `applicable_slots: ["gig", "bounty"]` skill, both
  `~/loops/gig/menu.json` and `~/loops/bounty/menu.json` contain the new entry.
- Menu schema validation passes after admission.

---

### Group SR — Self-Search Radar

Implemented in `~/anicca/skills/_shared/discovery-radar.sh`.

#### REQ-SR1 — Scheduled discovery pass

A launchd plist `ai.anicca.discovery-radar.plist` SHALL invoke
`bash ~/anicca/skills/_shared/discovery-radar.sh` daily at `04:00` local time (offset 30 min
from the adversary-daily.sh slots to avoid resource contention).

Each discovery pass SHALL consume ≤ 10,000 tokens (enforced by `--max-tokens 10000` flag on any
claude invocation within the script; haiku-4-5 is the default model for radar passes).

**Edge Cases:**
- **EDGE-SR1a** Previous radar pass is still running (> 30 min): flock guard (per skeleton
  NFR-3 pattern) silently exits.
- **EDGE-SR1b** Disk free < 500 MB (skeleton HARD 0.26 check): radar pass is skipped; logs
  a warning to `~/.openclaw/logs/discovery-radar.log`.

---

#### REQ-SR2 — Discovery sources and eval scoring

WHEN `discovery-radar.sh` runs, THE SYSTEM SHALL:
(a) query the following sources using firecrawl + gh search (≤ 3 sources per run, rotating):
    - `garylab/MakeMoneyWithAI` GitHub issues with label `agent-earn`,
    - GitHub search `"earn USDC" "agent" language:Python stars:>10` (updated within 30 days),
    - `benchflow-ai/awesome-evals` for new eval patterns applicable to earning tasks,
    - `~/anicca/state/discovery.jsonl` recent entries to avoid re-scanning,
(b) for each new opportunity (= not present in discovery.jsonl by URL dedup):
    - call `rubricScore` with a `"discovery"` category rubric (dimensions: `payout_verifiable`,
      `no_kyc_required`, `agent_doable`, `inventory_not_dry` — each 0.25 weight),
    - append to `~/anicca/state/discovery.jsonl`:
      `{ts, source, url, description, eval_score, proposed_to_curation: false}`.

**Edge Cases:**
- **EDGE-SR2a** All 3 sources return 0 new entries: log `{reason: "discovery-empty"}` to
  `~/.openclaw/logs/discovery-radar.log`; exit 0 (not an error).
- **EDGE-SR2b** firecrawl rate-limited: retry 3× with 30s backoff; on terminal failure, skip
  that source and continue with remaining sources.

**Acceptance Criteria:**
- After one radar pass against live sources, discovery.jsonl contains at least 0 rows (may be
  empty if all sources are dry — not a test failure).
- Schema validation test: every row in discovery.jsonl conforms to the defined schema.

---

#### REQ-SR3 — Curation proposal on high-score discovery

WHEN a discovery entry has `eval_score >= 0.6` (= passes at least 60% of the discovery rubric),
THE SYSTEM SHALL:
(a) call the curation gate trigger (REQ-CU1) with `source = discovery.jsonl:<url>`,
(b) update the discovery.jsonl row to `proposed_to_curation: true`.

Entries with `eval_score < 0.6` are recorded in discovery.jsonl for historical reference
but are NOT proposed to curation.

**Edge Cases:**
- **EDGE-SR3a** eval_score == exactly 0.6 → proposed (≥ is inclusive).
- **EDGE-SR3b** Curation claim-check rejects duplicate (already pending): REQ-CU1 silently
  ignores; discovery.jsonl row remains `proposed_to_curation: true` (first proposal claimed it).

**Acceptance Criteria:**
- Unit test: discovery entry with eval_score=0.6 triggers curation-gate call.
- Unit test: discovery entry with eval_score=0.59 does NOT trigger curation-gate call.

---

## Non-Functional Requirements

- **NFR-ED1** All pure functions (`netWorth`, `isSolvent`, `decideActivity`, `rubricScore`,
  `calibrationDrift`, `updateBanditArm`) SHALL be in `eval_spine.py` with zero imports of
  file/network/subprocess/random modules — verified by AST import scan in tests.

- **NFR-ED2** `decideActivity` SHALL return within 100ms (no I/O; pure computation).

- **NFR-ED3** Rubric judge LLM call SHALL complete within 60s; on timeout it returns a
  conservative `rubric_score = 0.5` (neither pass nor fail — treated as "inconclusive").

- **NFR-ED4** All new state files (survival.json, calibration.jsonl, menu-bandit.jsonl,
  menu-curation.jsonl, discovery.jsonl) use tmp-file + atomic `mv` writes per skeleton NFR-2.

- **NFR-ED5** `discovery-radar.sh` consumes ≤ 10,000 tokens per run (enforced by
  `--max-tokens` flag).

- **NFR-ED6** The curation gate sandbox (REQ-CU2) MUST NOT access the running wallet key
  (`~/.openclaw/.env::FOUNDER_WALLET_KEY`) — verified by sandbox environment variable audit
  before paper run launch.

- **NFR-ED7** `eval_spine.py` SHALL be covered by Hypothesis property tests (≥ 5 properties)
  verifying the pure-function contracts above.

---

## Edge Cases (Cross-Cutting)

- **EDGE-X1** Survival ledger shows net_usdc going positive mid-grace-window: `loss_start_ts`
  is reset to `null` in the next survival.json recompute; the grace window timer restarts from
  zero if net goes negative again.

- **EDGE-X2** decideActivity returns `pick` for an entry whose `admitted_at_ts is None`
  (pre-admission race): proactive-loop.sh checks `admitted_at_ts` before executing the pick;
  if null, re-runs decideActivity with that entry excluded from the menu.

- **EDGE-X3** Calibration.jsonl has > 10,000 rows: calibrationDrift operates only on the
  rolling window (`window_secs`) — it does not scan the entire file; tail-N rows by timestamp.

- **EDGE-X4** rubric-config.json for a category is updated mid-wake (concurrent cron write):
  rubric is loaded ONCE at the start of each wake's eval call (snapshot); mid-wake changes
  do not affect the in-progress evaluation.

- **EDGE-X5** Discovery radar proposes a skill already in the menu (re-discovered): curation
  claim-check sees an existing `status: "admitted"` row and ignores; discovery.jsonl row is
  updated `proposed_to_curation: true` but no new curation run occurs.

---

## Purity Boundary Analysis

| layer | function / module | side-effect surface |
|---|---|---|
| **PURE** | `netWorth`, `isSolvent` | none — trivial arithmetic |
| **PURE** | `decideActivity` | none — reads from in-memory menu + stats |
| **PURE** | `rubricScore` | none — aggregates pre-computed dimension scores |
| **PURE** | `calibrationDrift` | none — statistics over in-memory arrays |
| **PURE** | `updateBanditArm` | none — Beta param update |
| **EFFECTFUL** | TrackedProvider (tracked-provider.sh) | subprocess calls to `claude`/ClawRouter; reads pane footer; appends to events.jsonl |
| **EFFECTFUL** | survivalLedger.recompute() | reads cumulative.json + fx.json; writes survival.json |
| **EFFECTFUL** | rubricJudge.invoke() | LLM call (claude haiku); reads rubric-config.json |
| **EFFECTFUL** | calibrationWriter.append() | appends to calibration.jsonl |
| **EFFECTFUL** | curationGate.run() | sandbox spawn; adversary spawn; file writes to curation.jsonl + reviews/ |
| **EFFECTFUL** | discoveryRadar.scan() | firecrawl HTTP; `gh search`; appends to discovery.jsonl |

The PURE layer forms a fully deterministic, testable core.
The EFFECTFUL shell is a thin wrapper that snapshots state → calls PURE → applies result.

---

## "Done" / Acceptance Definition

**4-D convergence** (lean mode):

| dimension | condition |
|---|---|
| spec | this document + Phase 1b architecture approved by adversary PASS |
| test | unit + property tests for all 6 pure functions GREEN; integration test (losing arm retired, winning arm doubled-down) GREEN; E2E (survival ledger records real cost row + real income row, net computed) GREEN |
| impl | eval_spine.py + tracked-provider.sh + rubric-judge.py + curation-gate.sh + discovery-radar.sh all present and invoked by proactive-loop.sh |
| verification | calibrationDrift check passes (pearson_r >= 0.3) over the first 10 calibration pairs from a real slot run; or insufficient-data flag if < 10 pairs (not a failure — a scheduling concern) |

Lean gate: adversary review ≤ 3 rounds; human spec sign-off optional.
