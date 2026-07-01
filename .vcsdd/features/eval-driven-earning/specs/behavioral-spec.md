---
feature: eval-driven-earning
phase: 1a
mode: lean
sources:
  - HKUDS/ClawWork (8.2k★) — TrackedProvider real-cost + survival ledger + decide_activity explore/exploit + rubric-judge-with-override
  - benchflow-ai/awesome-evals (608★) — pass@k / pass^k vocabulary, Verifier's Law ("verifiable > judgeable"), calibration-drift
  - garylab/MakeMoneyWithAI — auto-refreshing opportunity radar cron pattern
  - earn-shared-skeleton/specs/behavioral-spec.md (v2) — REQ-B2 per-model rates, REQ-B4 kill-switch, REQ-H1 novelty quota, REQ-F1 self-recover, INV-8 platform-api-verified settled payout gate, INV-11 token kill-switch, sprint-2 proactive-loop + menu.json
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
    - INV-8 platform-api-verified settled payout gate (earnings.jsonl rows require platform_api_response_sha256)
  integrates_at:
    - proactive-loop.sh step 5 ("pick highest ROI") → replaced by decideActivity output
    - loop-roi.sh token_source measurement → improved by TrackedProvider (REQ-S1)
    - loop.disabled kill-switch (REQ-B4, in loop-roi.sh) → survival ledger advisory signal (REQ-S5) feeds lessons.jsonl; B4 remains the SOLE kill-switch trigger
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
| REQ-B2 per-model rate table | TrackedProvider (REQ-S1) reads SAME rates to compute per-message cost_usd |
| `~/loops/<slot>/cumulative.json` | survival.json recomputes from `cumulative_token_cost_jpy` (cost) + `cumulative_jpy_earned` and `cumulative_usdc_earned` (income, both currencies converted to USD via fx.json, INV-8 verified) |
| `~/loops/<slot>/roi.jsonl` `token_source` field | TrackedProvider promotes this field from "estimated" to "measured" where possible |
| REQ-B4 loop.disabled kill-switch | survival ledger (REQ-S5) provides an ADVISORY isSolvent signal to lessons.jsonl; B4 in loop-roi.sh remains the sole owner of loop.disabled |
| REQ-H1 novelty quota (`ceil(0.1 × max_apply_per_pass)`) | `decideActivity` explore_epsilon parameter copies this floor; explore count is INJECTED from menu-bandit.jsonl (not read inside the pure fn) |
| `~/loops/<slot>/menu.json` (sprint-2 schema) | this feature adds bandit arm fields per REQ-M1 without removing existing fields |
| proactive-loop.sh step 5 | replaced: step 5 now calls `decideActivity` and acts on its `pick` |
| TRAP-6 sandbox isolation | curation gate (Group CU) formalises this with adversary PASS requirement |

## New Tracked Quantities

These are files OWNED by this feature (not defined in skeleton):

| path | semantics | writer | reader |
|---|---|---|---|
| `~/loops/<slot>/survival.json` | per-slot survival state; recomputed every wake from cumulative.json | survivalLedger.recompute() | proactive-loop.sh (calls isSolvent advisory check after each wake; logs insolvent advisory to lessons.jsonl) |
| `~/loops/<slot>/calibration.jsonl` | append-only; one row per scored action: `{ts, action_id, rubric_score, realized_usd, window_ts}` | rubric-judge.py after outcome received | calibrationDrift() (caller pre-filters by window_ts before passing lists) |
| `~/loops/<slot>/menu-bandit.jsonl` | append-only bandit arm update log; one row per wake outcome: `{ts, entry_id, mode, realized_usd, alpha_new, beta_new}` (mode field enables explore-count injection) | updateBanditArm() caller (proactive-loop step 7) | bandit reconstruction on crash-restart; shell reads last-100 rows to inject bandit_stats into decideActivity |
| `~/anicca/state/menu-curation.jsonl` | append-only; skills pending curation review: `{ts, skill_id, source, status: "pending"\|"pass"\|"fail"\|"admitted"}` | curation-gate.sh | curation gate admission check |
| `~/anicca/state/discovery.jsonl` | append-only; discovered opportunities: `{ts, source, url, description, eval_score, proposed_to_curation: bool}` | discovery-radar.sh | curation gate |

### survival.json schema (version 1)

```jsonc
{
  "slot": "<slot>",
  "cost_usd": <float>,             // cumulative_token_cost_jpy / FX_USDJPY (from cumulative.json + fx.json)
  "income_usd": <float>,           // Σ(amount_jpy/FX_USDJPY) + Σ(amount_usdc) over INV-8-verified earnings.jsonl rows
  "net_usd": <float>,              // income_usd − cost_usd  (= netWorth output)
  "loss_start_ts": <int|null>,     // unix ts when net_usd first went negative; null if net >= 0
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
(d) computes `cost_usd = (tokens_in × rate_input[model_id] + tokens_out × rate_output[model_id]
    + thinking_tokens × rate_output[model_id]) / 1_000_000`,
    using the REQ-B2 per-model rate table (all rates are in USD/Mtok; dividing by 1_000_000
    yields USD directly — NO FX conversion applied here because the rates are already priced
    in USD; 1 USDC ≈ 1 USD for this computation),
(e) appends `{ts, model_id, tokens_in, tokens_out, thinking_tokens, cost_usd}` to
    `~/loops/<slot>/events/<pass_id>.jsonl` as an `event: "cost"` row,
(f) on pane-footer-only fallback (= measurement not available from API response body),
    sets `token_source: "estimated"` in the row and applies the skeleton REQ-B6 penalty.

**Edge Cases:**
- **EDGE-S1a** Claude invoked without `--model` flag: TrackedProvider reads the model from the
  pane footer's model banner ("Model: sonnet") before applying the rate table; on parse failure,
  falls back to "sonnet" (most expensive safe assumption) and sets `token_source: "estimated"`.
- **EDGE-S1b** thinking_tokens absent from response (non-extended-thinking model): recorded as
  0 without error; cost computed from tokens_in + tokens_out only.
- **EDGE-S1c** FX_USDJPY file missing: REQ-S1(d) does not use FX_USDJPY at all (rates are in
  USD); this edge case is only relevant to REQ-S2's cost_usd conversion from cumulative_token_cost_jpy.

**Acceptance Criteria:**
- A unit test verifies that TrackedProvider with model_id="sonnet", tokens_in=1000,
  tokens_out=500, thinking_tokens=200 produces
  `cost_usd = (1000×3 + 500×15 + 200×15) / 1_000_000 = 13500 / 1_000_000 = 0.0135 USD`
  (no FX division; rates are USD/Mtok already).
- An unknown model_id triggers a REQ-F1 `self-recover.sh` call (verified by subprocess spy),
  does NOT append to events.jsonl, and does NOT silently record cost_usd=0.

---

#### REQ-S2 — Survival state file: schema and write semantics

WHEN a slot's wake completes (= `loop-roi.sh` end-of-pass row has been written),
THE SYSTEM SHALL atomically rewrite `~/loops/<slot>/survival.json` by:
(a) reading `cumulative.json.cumulative_token_cost_jpy` (skeleton-maintained) and reading
    `cumulative.json.cumulative_jpy_earned` + `cumulative.json.cumulative_usdc_earned`
    (both INV-8 verified — each row in earnings.jsonl has a platform_api_response_sha256),
(b) computing `cost_usd = cumulative_token_cost_jpy / FX_USDJPY`
    (FX_USDJPY from fx.json; default 150.0 if file absent),
(c) computing `income_usd = (cumulative_jpy_earned / FX_USDJPY) + cumulative_usdc_earned`
    (normalises BOTH JPY-settling slots such as Coconala/Amazon AND USDC-settling slots
    such as Whop/Algora into a single USD unit; 1 USDC ≈ 1 USD),
(d) computing `net_usd = income_usd − cost_usd`,
(e) setting `loss_start_ts` = existing value if already negative, else the current unix
    timestamp if `net_usd < 0` for the first time this cycle, else `null`,
(f) incrementing `wake_count` by 1,
(g) writing to a tmp file and `mv`-renaming (atomic) per skeleton NFR-2.

`survival.json` is recomputed from source (`cumulative.json`) each wake, not
accumulated incrementally, so crash-restart is loss-free.

**Edge Cases:**
- **EDGE-S2a** `cumulative.json` does not exist (slot brand-new, zero wakes): survival.json
  is written with `cost_usd=0.0`, `income_usd=0.0`, `net_usd=0.0`, `loss_start_ts=null`,
  `wake_count=0`.
- **EDGE-S2b** Two proactive-loop ticks overlap (skeleton NFR-3 flock guard prevents concurrent
  execution, but if flock fails): second writer reads the tmp file from the first writer and
  `mv` races — last writer wins; no corruption possible because each recomputes from source.

**Acceptance Criteria:**
- survival.json written with correct schema after every wake (schema validated against
  JSON Schema by `test_survival_schema.py`).
- Crash-simulation test: delete survival.json mid-process, verify it is regenerated identically
  from cumulative.json on next wake.
- Schema test verifies `income_usd` equals `(jpy_earned / FX) + usdc_earned` for mixed-currency
  cumulative.json fixtures (e.g., ¥1500 Coconala + 0.5 USDC Algora → income_usd = 10.0 + 0.5 = 10.5 at FX=150).

---

#### REQ-S3 — Pure function: `netWorth`

THE SYSTEM SHALL expose a pure function `netWorth(cost_usd: float, income_usd: float) → float`
that returns `income_usd − cost_usd`.

**Constraints:**
- `netWorth` is total: defined for all float inputs including negative (overpayment or
  refund edge cases).
- `netWorth` has no side effects, reads no files, makes no system calls.

**Edge Cases:**
- **EDGE-S3a** `cost_usd = income_usd = 0.0` → returns 0.0.
- **EDGE-S3b** `income_usd < 0` (API refund, rare): returns a value < -cost_usd; this
  is mathematically correct and does NOT trigger isSolvent=False on its own — isSolvent
  gates on net_usd being PERSISTENTLY negative past grace.

**Acceptance Criteria:**
- `netWorth(5.0, 3.0) == -2.0`
- `netWorth(0.0, 10.0) == 10.0`
- `netWorth(0.0, 0.0) == 0.0`
- Property test (Hypothesis): `netWorth(c, i) == -netWorth(i, c)` for all float pairs.

---

#### REQ-S4 — Pure function: `isSolvent`

THE SYSTEM SHALL expose a pure function
`isSolvent(net_usd: float, loss_start_ts: Optional[int], grace_window_secs: int, now_ts: int) → bool`
that returns:
- `True` if `net_usd >= 0` (regardless of other parameters),
- `True` if `net_usd < 0` AND `loss_start_ts is None` (net just went negative this wake;
  `loss_start_ts` will be set by REQ-S2 after this call — caller passes the PRE-recompute value),
- `True` if `net_usd < 0` AND `(now_ts - loss_start_ts) < grace_window_secs`,
- `False` if `net_usd < 0` AND `(now_ts - loss_start_ts) >= grace_window_secs`.

Default `grace_window_secs` SHALL be `7 × 86400` (= 7 days), matching skeleton REQ-B4's
grace window for dimensional consistency.

**Edge Cases:**
- **EDGE-S4a** `grace_window_secs = 0` (testing only): returns False immediately on first
  negative net_usd — useful for unit tests that need deterministic bankruptcy.
- **EDGE-S4b** `now_ts < loss_start_ts` (clock skew): treats as `elapsed = 0`, returns True.
- **EDGE-S4c** `net_usd = -0.0` (IEEE float negative zero): treated as `>= 0`, returns True.

**Acceptance Criteria:**
- `isSolvent(-1.0, loss_start=T, grace=7d, now=T+6d) == True`
- `isSolvent(-1.0, loss_start=T, grace=7d, now=T+7d+1) == False`
- `isSolvent(+0.01, ...) == True` (any positive net)
- Property test: `isSolvent(net >= 0, ...) == True` for all non-negative net values.

---

#### REQ-S5 — Insolvent advisory signal (feeds lessons.jsonl; does NOT own loop.disabled)

WHEN `isSolvent(ledger.net_usd, ledger.loss_start_ts, GRACE_WINDOW, now_ts) == False`
(evaluated by proactive-loop.sh after REQ-S2 survival.json recompute completes),
THE SYSTEM SHALL append to `~/loops/<slot>/lessons.jsonl`:
`{ts, reason: "survival-insolvent", net_usd: <net_usd>, loss_duration_secs: <elapsed>}`
as an ADVISORY signal for Reflexion (Group C) to learn from.

THE SYSTEM SHALL NOT independently write `loop.disabled` or call `self-recover.sh survival-bankruptcy`.
There is NO `survival-bankruptcy` Group-J handler.

The SOLE kill-switch owner is skeleton REQ-B4 (inside `loop-roi.sh`), triggered when
`cumulative_token_cost_jpy > 5 × cumulative_jpy_earned` past the 7-day grace window.
The isSolvent advisory (cost_usd > income_usd, lower threshold) fires earlier and feeds
lessons.jsonl so Reflexion can tighten strategy before B4's harder 5:1 ratio is breached.

**Relationship between isSolvent and REQ-B4 thresholds:**
- isSolvent=False condition: `cost_usd > income_usd` (i.e., cost > 1× income) — advisory.
- REQ-B4 kill condition:     `cost_jpy > 5 × earned_jpy` (i.e., cost > 5× income) — terminal.
- Same source data (cumulative.json), same FX conversion; B4 fires ~5× later than isSolvent.
- Both use the same 7-day grace window anchored to different timestamps:
  B4 uses `first_seen_ts`; isSolvent uses `loss_start_ts` (first wake with negative net_usd).

**Edge Cases:**
- **EDGE-S5a** REQ-B4 kills the slot before isSolvent has reached its grace window: the slot
  is disabled by B4; isSolvent advisory is no longer invoked (loop.disabled skips all wake steps).
- **EDGE-S5b** Income arrives in the same wake that drove net_usd negative: REQ-S2's recompute
  from cumulative.json includes the income row; net_usd may become positive → isSolvent = True
  → no advisory row appended.

**Acceptance Criteria:**
- Integration test: set cost_usd=1.0, income_usd=0.0, loss_start=T, grace=0 → lessons.jsonl
  gains a `reason: "survival-insolvent"` row; `loop.disabled` is NOT created.
- Verify `loop.disabled` is absent after the advisory fires (only REQ-B4 creates it).

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
  (bounty-scan, clip, affiliate, video) with `(alpha=1, beta=1, admitted_at_ts=null)` priors.
  `trading-polymarket` is NOT in the bootstrap default because it is a real-wallet-capital rail
  and MUST enter the menu only after passing Group CU curation with a non-null `admitted_at_ts`
  (REQ-CU4). Bootstrap entries with `admitted_at_ts=null` automatically route to curation
  (REQ-CU1) on first pass; they are NOT exploit-eligible until `admitted_at_ts` is set.
- **EDGE-M1b** An existing entry missing the bandit arm fields (migrated from sprint-2 without
  bandit): migration step initializes missing fields to `(alpha=1, beta=1, attempt=0, pass=0,
  novelty_tried=true, admitted_at_ts=null)` — the null admitted_at_ts forces a curation pass
  for any pre-feature entry whose curation status is unknown.

**Acceptance Criteria:**
- JSON Schema test validates all entries after each write.
- Property test: `expected_usdc_per_wake` always in `[0, usdc_scale_factor]`.

---

#### REQ-M2 — Bandit arm update after wake outcome

WHEN a wake completes and the slot records a pass outcome `realized_usd >= 0.0`,
THE SYSTEM SHALL update the chosen entry's bandit arm by:
(a) computing `increment = clip(realized_usd / usdc_scale_factor, 0.0, 1.0)`
    (Beta-distribution posterior update — fractional increment proportional to normalized USD
    earned, capped at 1.0; this is the standard Beta-Bernoulli update with fractional evidence,
    NOT Thompson sampling — selection uses posterior-mean greedy-max, not posterior sampling),
(b) setting `alpha_new = alpha + increment`,
    `beta_new  = beta  + (1.0 − increment)`,
    (increment ∈ [0,1] ensures alpha and beta each increase by a total of 1.0 per wake,
    so the Beta(alpha,beta) posterior remains well-formed; realized_usd=0 → increment=0
    → alpha unchanged, beta+1 (pessimistic); realized_usd=scale → increment=1 → alpha+1,
    beta unchanged (optimistic)),
(c) incrementing `attempt_count += 1`, `pass_count += 1 if realized_usd > 0`,
(d) recomputing `expected_usd_per_wake = alpha_new / (alpha_new + beta_new) × usdc_scale_factor`,
(e) appending `{ts, entry_id, mode, realized_usd, alpha_new, beta_new}` to
    `~/loops/<slot>/menu-bandit.jsonl` BEFORE updating menu.json (claim-check against duplicate
    update on crash-restart; `mode` field enables explore-count injection for decideActivity),
(f) atomically rewriting menu.json (tmp + mv).

`updateBanditArm(arm: BanditArm, realized_usd: float, usdc_scale: float) → BanditArm` SHALL
be a pure function (no side effects) that implements steps (a)-(d); the caller performs (e)-(f).

**Edge Cases:**
- **EDGE-M2a** `realized_usd > usdc_scale_factor`: `clip(..., 0.0, 1.0)` in step (a)
  caps the increment at 1.0 — this is the CANONICAL definition in step (a), not an exception.
- **EDGE-M2b** Wake failed mid-pass (proactive-loop exited non-zero): no bandit update for
  that entry (outcome = unknown ≠ 0); attempt_count is NOT incremented; only wakes with a
  determined outcome update the arm.

**Acceptance Criteria:**
- `updateBanditArm({alpha=1, beta=1}, realized_usd=0, scale=1.0)` → `{alpha=1, beta=2}` (pessimistic).
- `updateBanditArm({alpha=1, beta=1}, realized_usd=0.5*scale, scale=1.0)` → `{alpha=1.5, beta=1.5}`.
- `updateBanditArm({alpha=1, beta=1}, realized_usd=2.0*scale, scale=1.0)` → `{alpha=2, beta=1}` (capped at increment=1.0).
- Property test: `alpha >= 1.0` and `beta >= 1.0` for any sequence of updates (PROP-M3).

---

### Group DA — Decide Activity

#### REQ-DA1 — Pure function: `decideActivity`

THE SYSTEM SHALL expose a pure function:

```python
decideActivity(
    menu: list[MenuEntry],
    bandit_stats: BanditStats,       # {recent_explore_count: int, total_recent_wakes: int}
                                     # injected by shell from tail-100 of menu-bandit.jsonl;
                                     # pure fn never reads files
    explore_epsilon: float,          # quota fraction (default 0.1 = skeleton REQ-H1 floor)
    budget: Budget,                  # FULL | MEDIUM | LIGHT | MINIMAL
    config: DecideConfig,            # {k_min_exploit: int, budget_caps: dict[Budget, float]}
) → ActivityDecision
```

where `ActivityDecision` = `{mode: "exploit" | "explore", pick: MenuEntry | None, reason: str}`
and `BanditStats = {recent_explore_count: int, total_recent_wakes: int}`.

`decideActivity` reads NO files and makes NO system calls — all inputs are passed as arguments.
The I/O shell is responsible for reading menu-bandit.jsonl, computing `bandit_stats`, and passing
it in. The explore/exploit decision rule is therefore deterministic given the inputs.

**Explore/exploit decision rule (deterministic, no RNG):**
1. If `menu` is empty → return sentinel (REQ-DA4).
2. Compute `explore_due = bandit_stats.recent_explore_count < floor(explore_epsilon × min(bandit_stats.total_recent_wakes + 1, 100))`.
3. If `explore_due` → select explore (quota not yet met for this rolling window).
4. If no entry has `attempt_count >= config.k_min_exploit` → select explore (all arms unproven).
5. Otherwise → select exploit (greedy-max on `expected_usd_per_wake` among eligible arms).

**Acceptance Criteria:**
- `decideActivity([...], BanditStats(0,0), 0.1, FULL, config)` always returns a single ActivityDecision (never raises).
- Property test: for any valid input, `mode` is exactly one of {"exploit", "explore"}.

---

#### REQ-DA2 — Exploit mode selection (pass^k reliability)

WHEN `decideActivity` selects `mode: "exploit"`, THE SYSTEM SHALL pick the `MenuEntry` with the
highest `expected_usd_per_wake` among entries where:
- `attempt_count >= config.k_min_exploit` (default K_MIN_EXPLOIT = 3, = minimum observations
  before an arm is considered "proven"), AND
- `admitted_at_ts is NOT None` (curation admission REQUIRED; entries with null `admitted_at_ts`
  are NEVER eligible for exploit regardless of attempt_count or novelty_tried status).

Ties SHALL be broken by lower `beta` value (= less pessimistic failure rate).

**Edge Cases:**
- **EDGE-DA2a** No entry has `attempt_count >= K_MIN_EXPLOIT` → mode falls back to explore
  unconditionally (all arms are unproven).
- **EDGE-DA2b** `budget == LIGHT` or `MINIMAL` → exploit filter adds `cost_estimate_usd <= budget_cap`
  (budget cap: LIGHT = 0.01 USD/wake, MINIMAL = 0.001 USD/wake); entries above cap are
  excluded from exploit candidates.

**Acceptance Criteria:**
- Given two entries with expected_usd_per_wake = 0.5 and 0.3, both with attempt_count >= 3 and
  admitted_at_ts set, exploit selects the 0.5 entry.
- Given only entries with attempt_count < 3, mode is "explore".
- Given an entry with attempt_count >= 3 but admitted_at_ts=None, it is NOT exploit-eligible
  (mode is "explore").

---

#### REQ-DA3 — Explore mode with novelty quota

WHEN `decideActivity` selects `mode: "explore"`, THE SYSTEM SHALL prefer entries where
`novelty_tried == False` (= never appeared in the slot's `applied.jsonl`).

The skeleton REQ-H1 novelty quota (at least `explore_epsilon` fraction of wakes must be explore)
is ENFORCED by the deterministic `explore_due` check in REQ-DA1's decision rule, using
`bandit_stats.recent_explore_count` INJECTED by the shell (not read inside the pure fn).

IF no `novelty_tried == False` entry exists, THE SYSTEM SHALL select the entry with the
LOWEST `attempt_count` among all entries (= least explored arm).

IF the quota cannot be met because only exploit-eligible entries remain, THE SYSTEM
SHALL log `{reason: "novelty-floor-unmet"}` to `lessons.jsonl` (same as skeleton REQ-H1) and
fall through to exploit selection.

**Edge Cases:**
- **EDGE-DA3a** Multiple `novelty_tried == False` entries → select the one with lowest
  `cost_estimate_usd` (minimize explore cost per the budget constraint).
- **EDGE-DA3b** `bandit_stats.total_recent_wakes == 0` (first wake ever): `explore_due = True`
  (0 < floor(0.1 × 1) = 0 is False; quota = 0 explores in 1 wake → explore_due=False only if
  total_recent_wakes+1 rounds to 0 explores — use ceiling for safety: at least 1 explore per 10).

**Acceptance Criteria:**
- Given a 10-entry menu where 9 have `novelty_tried=True` and 1 has `novelty_tried=False`,
  explore selects the one with `novelty_tried=False`.
- Quota simulation: given bandit_stats={recent_explore_count=0, total_recent_wakes=9},
  explore_epsilon=0.1, decideActivity returns mode="explore" (quota not met: 0 < floor(0.1×10)=1).

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
THE SYSTEM SHALL call the pure function:

```python
rubricScore(
    dimension_scores: dict[str, float],     # pre-computed LLM judge scores per dimension
    weights: dict[str, float],              # from rubric-config.json; must sum to 1.0
    has_deliverable: bool,                  # effectful shell checks file existence, passes result in
    deliverable_required: bool,             # from rubric-config.json category config
    verifiable_result: Optional[Literal["PASS", "FAIL", "NOT_APPLICABLE"]] = None,
                                            # set by effectful shell BEFORE calling rubricScore;
                                            # implements Verifier's Law (REQ-EV3) inside pure fn
) → RubricResult
```

where `RubricResult = {verdict: "PASS" | "HARD_FAIL", weighted_score: float, override_reason: str | None}`.

**Precedence order (applied inside the pure function in this order):**
1. If `verifiable_result == "PASS"` → return `RubricResult(verdict="PASS", weighted_score=1.0, override_reason="verifiable-check")` immediately.
2. If `verifiable_result == "FAIL"` → return `RubricResult(verdict="HARD_FAIL", weighted_score=0.0, override_reason="verifiable-check")` immediately.
3. If `deliverable_required and not has_deliverable` → return `RubricResult(verdict="HARD_FAIL", weighted_score=0.0, override_reason="missing-deliverable")` immediately.
4. If `sum(weights.values()) != 1.0` → raise `ValueError("weights must sum to 1.0")`.
5. Compute `weighted_score = Σ (dimension_scores[d] × weights[d])`.
   Return `RubricResult(verdict="PASS" if weighted_score >= 0.5 else "HARD_FAIL", weighted_score=weighted_score, override_reason=None)`.

The LLM judge call (effectful) happens BEFORE `rubricScore` is invoked; `rubricScore` is the
pure aggregation and override logic only. No file I/O inside the function.

**Edge Cases:**
- **EDGE-EV1a** No rubric-config.json for this slot (brand-new slot): effectful caller loads the
  global default rubric at `~/anicca/skills/_shared/rubric-default.json` and passes weights in.
- **EDGE-EV1b** `verifiable_result == "NOT_APPLICABLE"` (no verifiable check configured for
  this category): fall through to deliverable check then weighted score.

**Acceptance Criteria:**
- Given `dimension_scores={"quality":0.8,"relevance":0.5}`, `weights={"quality":0.7,"relevance":0.3}`,
  `has_deliverable=True`, `deliverable_required=False`, `verifiable_result=None`:
  `rubricScore` returns `weighted_score = 0.71`.
- `rubricScore(..., verifiable_result="PASS")` → verdict="PASS" regardless of dimension_scores.
- `rubricScore(..., verifiable_result="FAIL")` → verdict="HARD_FAIL" regardless of dimension_scores.
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
- Integration test: `rubricScore(..., verifiable_result="PASS", dimension_scores={"q":0.1})` → verdict="PASS".
- Integration test: `rubricScore(..., verifiable_result="FAIL", dimension_scores={"q":0.9})` → verdict="HARD_FAIL".

---

#### REQ-EV4 — Calibration record

WHEN an action's outcome is determined (= the platform confirms acceptance/rejection or a payout
receipt arrives per INV-8 verification), THE SYSTEM SHALL append to `~/loops/<slot>/calibration.jsonl`:

```jsonc
{
  "ts": <int>,
  "action_id": "<uuid>",
  "rubric_score": <float>,        // the weighted_score at time of submission
  "realized_usd": <float>,        // actual USD earned (INV-8 verified; JPY converted via FX; 0 if rejected)
  "outcome_type": "accepted" | "rejected" | "hard_fail_skip",
  "window_ts": <int>              // ts of the wake when the outcome was received
}
```

This row is the calibration dataset for `calibrationDrift`. `realized_usd` is normalized from
both JPY and USDC payouts using the same FX logic as REQ-S2(c).

**Edge Cases:**
- **EDGE-EV4a** Action was HARD_FAIL skipped (= REQ-EV2 or verifiable_result="FAIL" skipped
  submission): append row with `realized_usd=0.0`, `outcome_type="hard_fail_skip"` — valid data.
- **EDGE-EV4b** Action submitted but no outcome after 14 days: append row with
  `realized_usd=null`, `outcome_type="timeout"` — excluded from calibrationDrift calculation.

**Acceptance Criteria:**
- After 10 completed wakes, calibration.jsonl has ≥ 1 row with `realized_usd > 0` (assuming
  at least one earn action was accepted).
- Schema validation test: every row conforms to the schema.

---

#### REQ-EV5 — Calibration drift check and recalibration flag

Source: benchflow-ai/awesome-evals criteria-drift detection.

THE SYSTEM SHALL expose a pure function:
`calibrationDrift(scores: list[float], realized_usd: list[float], min_pairs: int = 10) → DriftResult`
where `DriftResult = {sufficient_data: bool, pearson_r: float | None, drift_detected: bool, threshold: float}`.

`window_secs` is NOT a parameter of this pure function. The effectful caller reads
`calibration.jsonl`, filters rows by timestamp (tail by `window_ts` field), extracts only
`rubric_score` and `realized_usd` values into two lists, and passes those pre-windowed lists
to `calibrationDrift`. Windowing responsibility is CALLER-SIDE (see EDGE-X3 below).

The function computes the Pearson correlation coefficient between `scores` and `realized_usd`.
`drift_detected = True` when `pearson_r < threshold` (default threshold = 0.3 — judge scores
must correlate at least weakly with actual earnings in USD).

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
- **EDGE-EV5a** All realized_usd are 0.0 (zero earning period): correlation is undefined
  (zero variance in Y); function returns `pearson_r=None`, `drift_detected=False` (not enough
  signal to judge drift — do not penalize the judge for a zero-earn phase).
- **EDGE-EV5b** Perfect correlation (pearson_r = 1.0): drift_detected=False, no action.
- **EDGE-EV5c** Rubric-config.json write fails (disk full): log warning, do not crash; drift
  flag is still recorded in lessons.jsonl.

**Acceptance Criteria:**
- `calibrationDrift(scores=[0.9,0.8,0.7], realized_usd=[10,8,7]) → pearson_r ≈ 1.0, drift=False`.
- `calibrationDrift(scores=[0.9,0.1,0.5], realized_usd=[0,10,0]) → pearson_r < 0.3, drift=True`.
- `calibrationDrift(scores=[...] len=5, min_pairs=10) → sufficient_data=False`.
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

WHEN the sandbox paper run passes (REQ-CU2), THE SYSTEM SHALL:

**(a) Payout endpoint probe (REAL verification, not mocked):**
Parse the skill's SKILL.md for a `payout_api_check:` frontmatter field specifying a read-only
endpoint (e.g., `GET /api/v1/sales/test` on the platform). Issue that request with test-mode
or stub credentials (a real HTTP call, not the sandbox mock). If the endpoint returns an HTTP
response (any status code including 401/404) the rail EXISTS; if it raises a connection error
the rail is UNREACHABLE. An unreachable payout endpoint is a curation FAIL (the skill cannot
earn via it). If `payout_api_check` is absent from SKILL.md, the curation gate FAILS with
`reason: "missing-payout_api_check"` (all skills MUST declare their settlement endpoint).

**(b) Adversary review:**
THE SYSTEM SHALL spawn a fresh-context Opus adversary with manifest:

```jsonc
{
  "reviewType": "curation-gate",
  "skill_id": "<id>",
  "paper_run_events": "<path to events.jsonl>",
  "endpoint_probe_result": {"url": "<declared endpoint>", "http_status": <int or null>, "reachable": <bool>},
  "skill_source": "<path to SKILL.md>",
  "evaluation_criteria": [
    "declares a payout_api_check endpoint listed in payout-endpoint-allowlist.json for its platform",
    "payout endpoint probe returned reachable=true (HTTP response received)",
    "no human-touch surfaces (REQ-J8 pattern)",
    "no spawn-surface drift",
    "cost_estimate_usd plausible for declared skill runtime"
  ]
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
- A skill missing `payout_api_check` in SKILL.md receives `overallVerdict == "FAIL"` (missing endpoint declaration).
- A well-formed skill whose endpoint probe returns `reachable=true` and passes paper run
  receives a verdict within 3 adversary rounds.

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
  `os`, `subprocess`, `pathlib`, `requests`, `urllib`, `random`, or `time` modules —
  verified by AST import scan in `test_eval_spine_no_io.py`. The `bandit_stats` injection
  pattern ensures `decideActivity` needs no file I/O to enforce the explore quota.

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

- **EDGE-X1** Survival ledger shows net_usd going positive mid-grace-window: `loss_start_ts`
  is reset to `null` in the next survival.json recompute; the grace window timer restarts from
  zero if net goes negative again.

- **EDGE-X2** decideActivity returns `pick` for an entry whose `admitted_at_ts is None`
  (pre-admission race): proactive-loop.sh checks `admitted_at_ts` before executing the pick;
  if null, re-runs decideActivity with that entry excluded from the menu — this should not
  happen because REQ-DA2 makes admitted_at_ts=None entries ineligible for exploit, and REQ-DA1
  only passes admitted entries to the exploit path; but the shell guard is a defensive backstop.

- **EDGE-X3** calibration.jsonl has > 10,000 rows: the effectful caller reads calibration.jsonl,
  filters rows by `window_ts` field (default: last 30 days), extracts `rubric_score` and
  `realized_usd` into two lists, and passes ONLY those pre-windowed lists to `calibrationDrift`.
  The pure function receives pre-filtered lists and has no window_secs parameter; it operates
  only on the data it is given.

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
| **PURE** | `netWorth(cost_usd, income_usd)` | none — trivial arithmetic |
| **PURE** | `isSolvent(net_usd, loss_start_ts, grace_window_secs, now_ts)` | none — boolean predicate on numeric inputs |
| **PURE** | `decideActivity(menu, bandit_stats, explore_epsilon, budget, config)` | none — bandit_stats injected by shell; no file reads |
| **PURE** | `rubricScore(dimension_scores, weights, has_deliverable, deliverable_required, verifiable_result)` | none — aggregates pre-computed scores; Verifier's Law applied by precedence |
| **PURE** | `calibrationDrift(scores, realized_usd, min_pairs)` | none — statistics over pre-windowed in-memory arrays |
| **PURE** | `updateBanditArm(arm, realized_usd, usdc_scale)` | none — Beta-distribution posterior update; returns new arm |
| **EFFECTFUL** | TrackedProvider (tracked-provider.sh) | subprocess calls to `claude`/ClawRouter; reads pane footer; appends to events.jsonl |
| **EFFECTFUL** | survivalLedger.recompute() | reads cumulative.json + fx.json; writes survival.json atomically |
| **EFFECTFUL** | rubricJudge.invoke() | LLM call; reads rubric-config.json; runs verifiable check tool; passes results to rubricScore |
| **EFFECTFUL** | calibrationWriter.append() | reads calibration.jsonl (windowed); appends row; passes pre-filtered lists to calibrationDrift |
| **EFFECTFUL** | curationGate.run() | sandbox spawn; payout endpoint probe (real HTTP); adversary spawn; writes menu-curation.jsonl + reviews/ |
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
