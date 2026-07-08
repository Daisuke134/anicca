# Purity Boundary Audit

## Feature: claude-p-ceo-loop | Phase: 5 | Date: 2026-07-08

## Declared Boundaries

Per `specs/verification-architecture.md`'s purity boundary map (lines 26-71) and
`specs/behavioral-spec.md`'s Ground truth section:

- **Tier 1 (pure, no I/O)**: `allocator.py` — `derive_roster`, `sum_earn_by_currency`,
  `convert_to_usd`, `realized_profit_usd`, `company_score`, `build_verification_row`,
  `capital_increase_within_realized_profit`, `fleet_increase_allowed`, `should_scale_down`,
  `build_lesson_row`, `bootstrap_registry_if_missing` (read-only path-existence check aside),
  `validate_allocation_ranges`, `build_next_registry`, `should_snapshot`, `restore_from_rollback`,
  `should_rollback`, `update_miss_count`, `next_cooldown_weeks_remaining`, `is_ceo_weekly_due`,
  `validate_escalation_schema`, `build_ceo_report_args`, `build_evidence_pointer`. `bandit.py` —
  `cold_start_state`, `select_scores`, `update_arm`, `compute_reward`. `budget.py` — `build_cost_event`,
  `monthly_spend_by_loop`, `weekly_spend_by_loop`, `budget_for_loop`, `filter_budget_compliant_loops`,
  `alert_key`, `should_fire_alert`, `budget_snapshot_for_registry`.
- **Tier 2/3 (I/O boundary)**: `allocator.write_registry_atomic` (THE single `loop-registry.json` write
  point, INV-CEO-2), `budget.record_cost_event`/`record_alert_fired`/`warn_if_budgets_missing`/
  `load_cost_events`/`load_fired_alert_keys`, `bandit.save_state`/`load_state`,
  `BudgetPacer.save`/`load` (a stateful dataclass by design, matching Mahoraga's own shape — declared
  acceptable in Ground truth, not a purity violation), and all of `run_pass.py`'s own orchestration
  (`_read_json`/`_write_json_atomic`/`_append_jsonl_atomic`/`_send_mail_best_effort`).
- **Data-source boundary (Ground truth section, REQ-CEO-001..004)**: the CEO is declared to READ (never
  write) `cadence.py`'s `cadence_met`/`streak`, `cadence-contracts.json`, each loop's real production
  ledger via `weekly_report.py` (`-weekly.jsonl`, `combined_score`/`beats_previous_week`) and
  `ledger_metrics.py::score_from_rows`'s existing fallback chain, `loop-scale/guardrails.py`'s
  3-condition gates, and `clip-promote-status.mjs::clipPromoteStatus` for clip-promote specifically —
  explicitly NOT re-implementing any of this reading/scoring logic ("車輪の再発明禁止").
- **INV-CEO-1** (currency-conversion single path): every `_usd`/`_usdc` parameter/field must be the
  output of `allocator.realized_profit_usd()`, never a raw native-currency amount.
- **INV-CEO-2** (execution-order + single-write): every WEEKLY-pass side effect has an explicit slot in
  REQ-CEO-058's steps ①-⑫; `loop-registry.json` is written at most once per pass, by
  `build_next_registry()` alone, via three independent local return values
  (`budget_snapshot_by_loop`/`rollback_restore`/`allocation_decisions`) with no shared mutable
  accumulator.

## Observed Boundaries

- **Tier 1 pure functions — CONFIRMED clean.** Every function listed above was either exercised
  directly by this Phase 5 session's `adversarial_boundary_probe.py` (25 new assertions) or by the
  re-run 168-assertion shipped Tier1 suite, with zero observed file I/O, zero observed mutation of
  input arguments (e.g. `build_next_registry` builds a fresh `dict(existing_loop)` per loop rather than
  mutating `existing_registry` in place — confirmed by reading `allocator.py:190-209`; `sum_earn_by_currency`/`bandit.update_arm` likewise return new values without mutating their inputs, consistent
  with this repo's own `coding-style.md` immutability rule).
- **Tier 2/3 I/O boundary — CONFIRMED isolated.** `grep -n "open(" ceo/*.py` shows every file-write call
  site lives inside one of the explicitly-named I/O helper functions (`write_registry_atomic`,
  `record_cost_event`, `record_alert_fired`, `warn_if_budgets_missing`, `bandit.save_state`,
  `BudgetPacer.save`) or inside `run_pass.py`'s own `_write_json_atomic`/`_append_jsonl_atomic` — none
  of the Tier1 pure functions above contain an `open(...)` call.
- **INV-CEO-2 — CONFIRMED.** `run_pass.py`'s WEEKLY sequence (lines 138-426) follows the declared
  ①-⑫ step numbering in inline comments matching REQ-CEO-058 exactly; `budget_snapshot_by_loop`,
  `rollback_restore`, and `allocation_decisions` are three independently-scoped local variables (no
  shared accumulator dict — `grep -rn "registry_updates" ceo/*.py` → 0 matches), passed as named
  arguments into `allocator.build_next_registry(...)` exactly once (step 9), which is itself the sole
  `open(..., "w")`/`os.replace` call site for `loop-registry.json` across the entire `ceo/` tree.
- **INV-CEO-1 — CONFIRMED at the call-site level.** Every `_usd`/`_usdc` consumer traced in
  `run_pass.py` (`compute_reward`'s `realized_earn_usdc` at line 166-167, `capital_increase_within_realized_profit`'s 3rd argument at line 265/286-288, `company_score` at line 200, the escalation's
  `weekly_realized_profit_usd` at line 265/324) all reuse the SAME `loop_realized_profit =
  allocator.realized_profit_usd(per_loop_entries.get(loop, []), fx_config)` value computed once per
  loop — no independent/duplicate currency-conversion call site was found anywhere in `ceo/*.py`.
- **Data-source boundary — MAJOR DRIFT, see Finding P1 below.** This is the single most significant
  purity/boundary finding of this Phase 5 pass.

### Finding P1 (BLOCKING) — the declared data-source boundary is not the observed data-source boundary
The purity boundary map's own Tier2 column for REQ-CEO-002 explicitly says the integration test must
confirm "roster全loop分について実`-weekly.jsonl`/実ledgerを読み...実ledgerのrowを
`sum_earn_by_currency`に通し" — i.e. the REAL per-loop ledger files (`~/.cloak/affiliate-metrics.jsonl`,
`~/gig/gig-funnel.jsonl`+`~/gig/earnings.jsonl`, `~/.cloak/earn-video-metrics-*.jsonl`, etc., per
behavioral-spec's own Ground truth mapping) are supposed to cross the read boundary into
`sum_earn_by_currency()`.

**Observed**: `run_pass.py:161` instead reads `os.path.join(state_dir, f"{loop}-earn-ledger.jsonl")` —
a file path inside the CEO's OWN new state directory (`~/.anicca-founder/state/`), using a naming
convention that matches NOTHING any existing loop CLI, evaluator, or ledger writer produces. Static
confirmation: `grep -rn "weekly_compare\|import weekly_report\|from weekly_report\|evaluate_stage1\|clip-promote-status\|clipPromoteStatus" ceo/*.py` → 0 matches; `grep -rn "import cadence\|from cadence"
ceo/*.py` → 0 matches (only `loop-scale/guardrails.py` is genuinely imported and reused, confirmed by
the shipped `test_guardrail_reuse.py`, 2/2 green). Dynamic confirmation: every live subprocess run of
`run_pass.py` in this session (11 `CEO_AGENT_DECISIONS_JSON` scenarios plus the RC≠0 founder-loop
re-check) produced `"company_score": 0.0` and every roster loop's `realized_profit_usd` came out `0.0`,
because the fabricated `{loop}-earn-ledger.jsonl` file never exists for any real loop.

This is a boundary-crossing defect, not a purity violation in the narrower sense (no impure code was
found inside a function declared pure) — the pure functions themselves (`sum_earn_by_currency`,
`realized_profit_usd`, `company_score`, `compute_reward`, `capital_increase_within_realized_profit`,
`should_scale_down`) are all correctly implemented and behave exactly as specified on the inputs they
are given. The defect is that **the wrong data crosses the Tier2→Tier1 boundary**: the declared
production ledger paths never reach these pure functions at all in the current implementation, so the
entire self-verification/bandit-reward/capital-gate/scale-down machinery operates on structurally-empty
inputs in any real deployment. Full detail and blast-radius analysis: `verification-report.md` Finding
F1.

### Secondary observation (INFO, not a purity violation)
`bandit.py`'s `ThompsonSamplingRouter` class exists and is correctly self-contained (stateful bookkeeping
IS its state, matching Mahoraga's own shape, declared acceptable) but `run_pass.py` never imports or
instantiates it — only the LinUCB-style pure-function path (`cold_start_state`/`select_scores`/
`update_arm`) is exercised in the actual WEEKLY pass. This does not violate any declared purity boundary
(the class's own internal Tier1/Tier2 split — `update()` bookkeeping vs `save_state`/`load_state` I/O —
is correctly maintained where it IS used, i.e. nowhere yet), it is simply dead/unwired code relative to
REQ-CEO-010's "config で linucb/thompson を選択可能" clause.

## Summary
- No hidden side effects were found inside any function declared pure (Tier 1) — every pure function
  audited (23 functions across `allocator.py`/`bandit.py`/`budget.py`) was either directly executed with
  adversarial inputs in this session or re-confirmed via the shipped 168-assertion suite, with zero
  file I/O and zero input-mutation observed.
- INV-CEO-1 (single currency-conversion path) and INV-CEO-2 (single `loop-registry.json` write point,
  no shared-mutable accumulator) both hold exactly as declared — confirmed by direct grep of every
  `open(...)`/`_usd`/`_usdc` call site in `ceo/*.py`, not merely by reading the spec's own claims.
- **1 BLOCKING boundary-crossing defect (Finding P1)**: the declared data-source boundary for
  REQ-CEO-002(b)/(c)/REQ-CEO-004 (each loop's real production ledger, read via `weekly_report.py`/
  `ledger_metrics.py`/`clip-promote-status.mjs`) is not what the implementation actually reads;
  `run_pass.py` reads a fabricated, unwritten file path instead. This must be fixed (either by wiring
  the real reader, or by re-specifying and implementing an actual writer for the CEO's own ledger
  convention) before this feature can be considered to satisfy its own Ground-truth data-source
  contract in production. Recommended as a required follow-up before Phase 6 convergence — Phase 6
  should not treat PROP-CEO-013/020's Tier2/3 columns as satisfied by the current wiring.
- No other core/shell drift or verifier-hostile coupling was found: the pure/impure split itself is
  well-designed and consistently applied everywhere it IS wired up; the defect is entirely about WHICH
  file gets read across that boundary, not about impurity leaking into the pure layer.
