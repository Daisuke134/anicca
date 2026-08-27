#!/usr/bin/env python3
"""Mature-only experiment scoring and replay-safe hook performance receipts."""

from __future__ import annotations

import datetime as dt
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any


METRIC_ORDER = (
    "net_revenue", "paid_orders", "trials", "installs",
    "first_time_downloads", "qualified_clicks", "views",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "timestamp timezone required")
    return parsed.astimezone(dt.timezone.utc)


def stable_id(values: list[str]) -> str:
    encoded = json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode()
    return f"writeback.{hashlib.sha256(encoded).hexdigest()[:24]}"


def _latest_per_experiment(snapshots: list[dict[str, Any]], observed_at: str) -> list[dict[str, Any]]:
    cutoff = parse_time(observed_at)
    latest: dict[str, dict[str, Any]] = {}
    for row in snapshots:
        if row.get("schema_version") != "marketing.experiment-attribution.v1":
            continue
        if parse_time(row["observed_at"]) > cutoff:
            continue
        key = row["experiment_id"]
        if key not in latest or parse_time(row["observed_at"]) > parse_time(latest[key]["observed_at"]):
            latest[key] = row
    return list(latest.values())


def _metric(row: dict[str, Any], name: str) -> dict[str, Any] | None:
    return next((item for item in row.get("results", [])
                 if item.get("metric_name") == name), None)


def _common_metric(rows: list[dict[str, Any]]) -> str | None:
    for name in METRIC_ORDER:
        values = [_metric(row, name) for row in rows]
        if all(value and value.get("status") == "observed"
               and value.get("value") is not None
               and value.get("attribution_class") != "unknown"
               for value in values):
            return name
    return None


def build_decision(*, snapshots: list[dict[str, Any]], observed_at: str,
                   product_id: str, platform: str, renderer_id: str,
                   checkpoint_hours: float = 24.0, min_cohort: int = 10,
                   experiment_plans: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    require(checkpoint_hours >= 24, "checkpoint must be at least 24 hours")
    require(min_cohort >= 10, "minimum cohort cannot be reduced below ten")
    latest = _latest_per_experiment(snapshots, observed_at)
    candidates = [row for row in latest
                  if row.get("product_id") == product_id
                  and row.get("renderer_id") == renderer_id]
    mature = [row for row in candidates
              if (parse_time(observed_at) - parse_time(row["published_at"])).total_seconds()
              >= checkpoint_hours * 3600]
    source_ids = sorted(row["attribution_id"] for row in mature)
    plans = {row.get("experiment_id"): row for row in (experiment_plans or [])}
    mapped = sum(row["experiment_id"] in plans for row in mature)
    tactic_status = "available" if mature and mapped == len(mature) else "partial" if mapped else "unavailable"
    decision = {
        "schema_version": "marketing.hook-performance.v1",
        "decision_id": stable_id([product_id, platform, renderer_id,
                                  str(checkpoint_hours), observed_at, *source_ids]),
        "observed_at": observed_at, "product_id": product_id,
        "platform": platform, "renderer_id": renderer_id,
        "checkpoint_hours": checkpoint_hours, "min_cohort": min_cohort,
        "eligible_experiments": len(mature), "status": "insufficient_data",
        "reason": None, "reward_metric": None,
        "source_attribution_ids": source_ids, "winners": [], "losers": [],
        "mutations": [], "tactic_mapping_status": tactic_status,
    }
    if len(mature) < min_cohort:
        decision["reason"] = ("checkpoint_not_mature" if candidates and not mature
                              else "comparable_cohort_below_minimum")
        return decision
    reward = _common_metric(mature)
    if reward is None:
        decision["reason"] = "no_common_observed_attributable_metric"
        return decision
    scored = []
    for row in mature:
        value = _metric(row, reward)["value"]
        scored.append({"experiment_id": row["experiment_id"],
                       "attribution_id": row["attribution_id"],
                       "hook_id": row["hook_id"], "value": value})
    scored.sort(key=lambda row: (row["value"], row["experiment_id"]), reverse=True)
    cut = max(1, len(scored) // 5)
    winners = scored[:cut]
    losers = sorted(scored[-cut:], key=lambda row: (row["value"], row["experiment_id"]))
    winner_ids = {row["experiment_id"] for row in winners}
    loser_ids = {row["experiment_id"] for row in losers}
    low = min(row["value"] for row in scored)
    high = max(row["value"] for row in scored)
    mutations = []
    for row in scored:
        normalized = 0.5 if high == low else (row["value"] - low) / (high - low)
        result = ("won" if row["experiment_id"] in winner_ids else
                  "lost" if row["experiment_id"] in loser_ids else "observed")
        mutations.append({"entity": "hook", "id": row["hook_id"],
                          "experiment_id": row["experiment_id"],
                          "result": result, "normalized_score": round(normalized, 6)})
    decision.update({
        "status": "scored", "reason": None, "reward_metric": reward,
        "winners": winners, "losers": losers,
        "mutations": mutations,
    })
    return decision


def apply_hook_updates(decision: dict[str, Any], hooks: list[dict[str, Any]],
                       *, alpha: float = 0.3, min_retire_observations: int = 3,
                       exploration_fraction: float = 0.2
                       ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return proposed canonical hooks plus receipts; never mutates inputs."""
    require(0 < alpha <= 1, "EWMA alpha invalid")
    require(min_retire_observations >= 3, "retirement observation floor invalid")
    require(0.2 <= exploration_fraction < 1, "exploration floor cannot be below 20%")
    if decision.get("status") != "scored":
        return copy.deepcopy(hooks), []
    updated = copy.deepcopy(hooks)
    by_id: dict[str, dict[str, Any]] = {}
    for row in updated:
        require(row.get("id") not in by_id, "duplicate hook id")
        by_id[row["id"]] = row
    hook_mutations = [row for row in decision.get("mutations", [])
                      if row.get("entity") == "hook"]
    require(len(hook_mutations) == decision.get("eligible_experiments"),
            "complete hook mutations required")
    receipts: list[dict[str, Any]] = []
    retire_candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for mutation in hook_mutations:
        hook = by_id.get(mutation.get("id"))
        require(hook is not None, f"unknown hook in decision: {mutation.get('id')}")
        score = mutation.get("normalized_score")
        require(isinstance(score, (int, float)) and 0 <= score <= 1,
                "normalized hook score invalid")
        previous = hook.get("ewma_score")
        require(previous is None or isinstance(previous, (int, float)),
                "existing hook EWMA invalid")
        before_observations = int(hook.get("observations") or 0)
        new_ewma = score if previous is None else (1 - alpha) * previous + alpha * score
        hook["ewma_score"] = round(new_ewma, 6)
        hook["observations"] = before_observations + 1
        receipt = {
            "hook_id": hook["id"], "result": mutation["result"],
            "previous_ewma": previous, "ewma_score": hook["ewma_score"],
            "observations": hook["observations"], "retired": False,
            "retirement_blocked_reason": None,
        }
        if mutation["result"] == "lost":
            if hook["observations"] < min_retire_observations:
                receipt["retirement_blocked_reason"] = "minimum_three_observations"
            else:
                retire_candidates.append((hook, receipt))
        receipts.append(receipt)
    active_count = sum(row.get("status") == "active" for row in updated)
    minimum_active = max(1, int(len(updated) * exploration_fraction + 0.999999))
    for hook, receipt in retire_candidates:
        if hook.get("status") != "active":
            continue
        if active_count - 1 < minimum_active:
            receipt["retirement_blocked_reason"] = "exploration_floor_20_percent"
            continue
        hook["status"] = "retired"
        receipt["retired"] = True
        active_count -= 1
    return updated, receipts


def _performance_result(score: float) -> str:
    if score >= 0.7:
        return "won"
    if score <= 0.3:
        return "lost"
    return "observed"


def build_entity_performance(decision: dict[str, Any],
                             experiment_plans: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate exact experiment mappings into tactic and renderer evidence."""
    if decision.get("status") != "scored":
        return {"tactic_mapping_status": "unavailable", "tactics": [],
                "renderer": None}
    mutations = [row for row in decision.get("mutations", [])
                 if row.get("entity") == "hook"]
    plan_by_experiment: dict[str, dict[str, Any]] = {}
    for plan in experiment_plans:
        experiment_id = plan.get("experiment_id")
        require(experiment_id not in plan_by_experiment, "duplicate experiment plan")
        plan_by_experiment[experiment_id] = plan
    exact = all(row.get("experiment_id") in plan_by_experiment for row in mutations)
    tactic_rows: list[dict[str, Any]] = []
    if exact and mutations:
        grouped: dict[str, list[float]] = {}
        for row in mutations:
            tactic_id = plan_by_experiment[row["experiment_id"]].get("tactic_id")
            require(isinstance(tactic_id, str) and tactic_id, "experiment tactic missing")
            grouped.setdefault(tactic_id, []).append(float(row["normalized_score"]))
        for tactic_id, values in sorted(grouped.items()):
            average = sum(values) / len(values)
            tactic_rows.append({"tactic_id": tactic_id,
                                "normalized_score": round(average, 6),
                                "observations": len(values),
                                "result": _performance_result(average)})
    renderer_values = [float(row["normalized_score"]) for row in mutations]
    renderer_average = sum(renderer_values) / len(renderer_values)
    renderer = {"renderer_id": decision["renderer_id"],
                "normalized_score": round(renderer_average, 6),
                "observations": len(renderer_values),
                "result": _performance_result(renderer_average)}
    return {"tactic_mapping_status": "available" if exact else "unavailable",
            "tactics": tactic_rows, "renderer": renderer}


def append_decision(path: Path, decision: dict[str, Any]) -> bool:
    path = Path(path)
    rows = [] if not path.exists() else [json.loads(line) for line in
                                         path.read_text(encoding="utf-8").splitlines()
                                         if line.strip()]
    matches = [row for row in rows if row.get("decision_id") == decision["decision_id"]]
    encoded = json.dumps(decision, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if matches:
        existing = json.dumps(matches[0], ensure_ascii=False, sort_keys=True,
                              separators=(",", ":"))
        require(existing == encoded, "conflicting writeback replay")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                            for row in rows + [decision]), encoding="utf-8")
    os.replace(temp, path)
    return True


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def write_json(path: Path, value: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8")
    os.replace(temp, path)


def run_writeback(*, attribution_path: Path, plans_path: Path, perf_path: Path,
                  evidence_path: Path, observed_at: str, product_id: str,
                  platform: str, renderer_id: str, checkpoint_hours: float = 24,
                  min_cohort: int = 10) -> dict[str, Any]:
    decision = build_decision(
        snapshots=read_jsonl(attribution_path), observed_at=observed_at,
        product_id=product_id, platform=platform, renderer_id=renderer_id,
        checkpoint_hours=checkpoint_hours, min_cohort=min_cohort,
        experiment_plans=read_jsonl(plans_path))
    appended = append_decision(perf_path, decision)
    evidence = {
        "schema_version": 1, "gate": 14,
        "implementation_status": "verified",
        "evidence_status": ("production_scored" if decision["status"] == "scored"
                            else "waiting_for_mature_cohort"),
        "decision": decision, "perf_appended": appended,
        "canonical_mutation_count": len(decision["mutations"]),
        "source_paths": {"attribution": str(attribution_path),
                         "plans": str(plans_path), "hook_perf": str(perf_path)},
    }
    write_json(evidence_path, evidence)
    return evidence
