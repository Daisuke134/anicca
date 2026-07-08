#!/usr/bin/env python3
"""run_pass.py — REQ-CEO-058: one CEO pass. DAILY (light, read-only) unless `is_ceo_weekly_due()`
fires, in which case the full WEEKLY sequence (steps (1)-(12) below, numbered per REQ-CEO-058) runs.
Called by ceo-pass.sh; state root overridable via CEO_STATE_DIR (test seam, mirrors founder-loop.sh's
own FOUNDER_TEST/FOUNDER_DIR pattern) so tests never touch the real ~/.anicca-founder/state/.

Every write in this module goes through allocator.write_registry_atomic /
allocator/budget/bandit's own atomic-write helpers (tmp-write + os.replace) -- the same pattern
record-earn.mjs's writeCursorAtomic uses. loop-registry.json is written exactly once per WEEKLY pass,
at step (9) -- INV-CEO-2.

Step (8) (agent allocation decision) is intentionally NOT auto-computed here from the bandit's own
scores: REQ-CEO-012 forbids writing the bandit's argmax straight to the registry. A real agent
session supplies its decisions via CEO_AGENT_DECISIONS_JSON (a small JSON file the agent writes
before invoking this pass in "apply" mode); a headless-only pass (no agent, most cron wakes) leaves
allocation_decisions empty, so build_next_registry() carries the existing allocation forward
unchanged -- observation/budget/rollback bookkeeping keeps running either way (steps 1-7, 9-12)."""
from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
import zoneinfo

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import allocator  # noqa: E402
import bandit  # noqa: E402
import budget  # noqa: E402
from budget_pacer import BudgetPacer  # noqa: E402

JST = zoneinfo.ZoneInfo("Asia/Tokyo")


def _state_dir() -> str:
    return os.environ.get("CEO_STATE_DIR") or os.path.expanduser("~/.anicca-founder/state")


def _cadence_contracts_path() -> str:
    return os.environ.get("CEO_CADENCE_CONTRACTS") or os.path.expanduser(
        "~/anicca/skills/self/cadence-contracts.json"
    )


def _read_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _write_json_atomic(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp, path)


def _append_jsonl_atomic(path: str, row: dict) -> None:
    existing = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            existing = f.read()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(existing + json.dumps(row, sort_keys=True) + "\n")
    os.replace(tmp, path)


def _today_jst() -> str:
    return datetime.datetime.now(JST).date().isoformat()


def main() -> int:
    state_dir = _state_dir()
    os.makedirs(state_dir, exist_ok=True)
    marker_log = os.path.join(state_dir, "ceo-pass.log")
    today = _today_jst()
    ts_now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # PROP-CEO-022: this marker MUST be written unconditionally, first, before anything below can
    # fail -- it is the direct evidence that ceo-pass.sh ran even on a RC!=0 founder-loop wake.
    with open(marker_log, "a", encoding="utf-8") as f:
        f.write(f"{ts_now} ceo-pass ran (today_jst={today})\n")

    weekly_meta_path = os.path.join(state_dir, "ceo-weekly-meta.json")
    weekly_meta = _read_json(weekly_meta_path, {"last_ceo_run_jst_date": None})
    is_weekly = allocator.is_ceo_weekly_due(weekly_meta.get("last_ceo_run_jst_date"), today)

    cadence_contract = _read_json(_cadence_contracts_path(), {})
    roster = allocator.derive_roster(cadence_contract) if cadence_contract else []

    if not is_weekly:
        # REQ-CEO-003: DAILY pass reads the same snapshot shape but never writes bandit state,
        # loop-registry.json, or ceo-verification.jsonl.
        print(json.dumps({"pass": "daily", "today": today, "roster": roster}))
        return 0

    # ---------------- WEEKLY pass, REQ-CEO-058 steps (1)-(12) ----------------
    fx_config = _read_json(os.path.join(state_dir, "ceo-fx-config.json"), {"jpy_usd_rate": 150.0})
    registry_path = os.path.join(state_dir, "loop-registry.json")
    existing_registry = allocator.bootstrap_registry_if_missing(registry_path)  # (1)

    budget_cfg = _read_json(os.path.join(state_dir, "ceo-budget-config.json"), None)
    cost_events_path = os.path.join(state_dir, "ceo-cost-events.jsonl")
    cost_rows = budget.load_cost_events(cost_events_path)
    month_key = ts_now[:7]
    monthly_spend = budget.monthly_spend_by_loop(cost_rows, month_key)
    weekly_spend = budget.weekly_spend_by_loop(cost_rows, today)  # (2)

    # (3-a/b): bandit + BudgetPacer update -- unconditional, every WEEKLY pass (PROP-CEO-023).
    bandit_state_path = os.path.join(state_dir, "ceo-bandit-state.json")
    arms = bandit.load_state(bandit_state_path)
    pacer_path = os.path.join(state_dir, "ceo-budget-pacer-state.json")
    pacer = BudgetPacer.load(pacer_path)
    pacer.update(sum(weekly_spend.values()))
    pacer.save(pacer_path)

    per_loop_entries = {}
    for loop in roster:
        # Best-effort per-loop earn ledger; each loop owns its own ledger file, this pass only reads.
        ledger_path = os.path.join(state_dir, f"{loop}-earn-ledger.jsonl")
        rows = budget.load_cost_events(ledger_path)
        per_loop_entries[loop] = allocator.sum_earn_by_currency(rows)

    for loop in roster:
        realized = allocator.realized_profit_usd(per_loop_entries.get(loop, []), fx_config)
        reward = bandit.compute_reward(realized, weekly_spend.get(loop, 0.0), pacer.lambda_)
        context = [1.0, weekly_spend.get(loop, 0.0), realized]
        arms = bandit.update_arm(arms, loop, context, reward, d=len(context), prior=0.5)
    bandit.save_state(bandit_state_path, arms)

    # (3-c): budget fail-open log + snapshot -- unconditional, every WEEKLY pass.
    budget_snapshot_by_loop = {}
    for loop in roster:
        if budget.budget_for_loop(budget_cfg, loop) is None:
            budget.warn_if_budgets_missing(marker_log, loop)
        budget_snapshot_by_loop[loop] = budget.budget_snapshot_for_registry(
            budget_cfg, loop, monthly_spend.get(loop, 0.0)
        )

    # (4): company_score
    this_week_score = allocator.company_score(per_loop_entries, fx_config)
    verification_path = os.path.join(state_dir, "ceo-verification.jsonl")
    prior_rows = budget.load_cost_events(verification_path)
    prev_week_score = prior_rows[-1]["this_week_company_score"] if prior_rows else 0.0
    beats = this_week_score > prev_week_score

    # (6): rollback state machine
    miss_streak_path = os.path.join(state_dir, "ceo-miss-streak.json")
    miss_streak = _read_json(
        miss_streak_path, {"consecutive_miss_count": 0, "cooldown_weeks_remaining": 0}
    )
    count_in = miss_streak["consecutive_miss_count"]
    cooldown_in = miss_streak["cooldown_weeks_remaining"]

    rollback_path = os.path.join(state_dir, "ceo-rollback.json")
    rollback_snapshot = _read_json(rollback_path, None)
    if allocator.should_snapshot(count_in, cooldown_in):
        rollback_snapshot = {
            loop: {"allocation": existing_registry[loop].get("allocation")}
            for loop in roster
            if loop in existing_registry
        }
        _write_json_atomic(rollback_path, rollback_snapshot)

    count_new = allocator.update_miss_count(count_in, beats, cooldown_in)
    rollback_fired = allocator.should_rollback(count_new, cooldown_in)
    rollback_restore = (
        allocator.restore_from_rollback(rollback_snapshot)
        if rollback_fired and rollback_snapshot
        else None
    )

    # (8): allocation-decision gate -- agent judgment only, REQ-CEO-012. Skipped entirely
    # (allocation_decisions stays {}) when cooldown is active or a rollback just fired this pass.
    allocation_decisions = {}
    gate_open = (cooldown_in == 0) and (not rollback_fired)
    decisions_path = os.environ.get("CEO_AGENT_DECISIONS_JSON")
    if gate_open and decisions_path and os.path.exists(decisions_path):
        candidate_decisions = _read_json(decisions_path, {})
        ranges_cfg = _read_json(os.path.join(state_dir, "ceo-allocation-ranges.json"), {})
        allocation_decisions = {
            loop: decision
            for loop, decision in candidate_decisions.items()
            if allocator.validate_allocation_ranges(decision.get("allocation", {}), ranges_cfg)
        }

    # (9): THE single loop-registry.json write for this pass -- INV-CEO-2.
    next_registry = allocator.build_next_registry(
        existing_registry, budget_snapshot_by_loop, rollback_restore, allocation_decisions
    )
    allocator.write_registry_atomic(registry_path, next_registry)

    # (10): miss-streak persistence -- the only place cooldown_weeks_remaining is written.
    cooldown_next = allocator.next_cooldown_weeks_remaining(
        cooldown_in, rollback_fired, rollback_cooldown_weeks=1
    )
    count_persisted = 0 if rollback_fired else count_new
    _write_json_atomic(
        miss_streak_path,
        {"consecutive_miss_count": count_persisted, "cooldown_weeks_remaining": cooldown_next},
    )

    # (11): verification row -- one canonical row per WEEKLY pass.
    row = allocator.build_verification_row(
        ts=ts_now,
        week_start=today,
        prev=prev_week_score,
        this=this_week_score,
        beats=beats,
        alloc_ref=f"loop-registry.json@{ts_now}",
        consecutive_miss_count=count_persisted,
        cooldown_weeks_remaining=cooldown_next,
        rollback_fired=rollback_fired,
        rolled_back_to_week=(today if rollback_fired else None),
    )
    _append_jsonl_atomic(verification_path, row)

    # (12): mail report -- best-effort, must never fail the pass.
    actions_summary = (
        ", ".join(f"{loop}:{d.get('allocation')}" for loop, d in allocation_decisions.items())
        or "none"
    )
    verification_summary = (
        f"beats_previous_week={str(beats).lower()}, rollback_fired={str(rollback_fired).lower()}"
    )
    report_args = allocator.build_ceo_report_args(this_week_score, actions_summary, verification_summary)
    evidence = allocator.build_evidence_pointer(
        verification_path if roster else None, today if roster else None
    )
    report_script = os.path.join(HERE, "..", "..", "..", "report", "loop-report.sh")
    try:
        subprocess.run(
            [
                "bash", report_script, "ceo", "weekly pass",
                report_args["result"], str(report_args["earned_usdc"]), evidence,
            ],
            check=False, timeout=30,
        )
    except Exception:  # noqa: BLE001 -- mail failure must never fail the pass
        pass

    _write_json_atomic(weekly_meta_path, {"last_ceo_run_jst_date": today})
    print(
        json.dumps(
            {
                "pass": "weekly",
                "today": today,
                "company_score": this_week_score,
                "rollback_fired": rollback_fired,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
