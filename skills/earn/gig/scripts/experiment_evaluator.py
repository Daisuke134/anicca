#!/usr/bin/env python3
"""Evaluate one isolated Gig strategy experiment from fresh funnel evidence.

The historical B4 prompt created many simultaneous mutations, then compared cumulative
counts.  That cannot identify which mutation caused an outcome.  This evaluator makes
the safe boundary executable:

* overlapping active experiments are quarantined, never guessed into keep/revert;
* only code-owned strategy fields can be reverted automatically;
* the post-mutation cohort must contain enough fresh applications;
* reply/win/paid rates, not ever-growing cumulative counts, decide the verdict;
* every terminal verdict is atomically persisted and appended once to an audit ledger.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


DEFAULT_STATE = Path.home() / "gig"
REVERSIBLE_ROOTS = {
    "proposal_playbook",
    "proposal_templates",
    "price_defaults",
    "listing_categories",
    "priority_categories",
}
RATE_METRICS = {"replied", "won", "paid"}
TERMINAL = {"kept", "reverted", "quarantined"}


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _active_due(experiment: Any, pass_count: int) -> bool:
    return (
        isinstance(experiment, dict)
        and experiment.get("status") == "active"
        and isinstance(experiment.get("eval_by_pass"), int)
        and experiment["eval_by_pass"] <= pass_count
    )


def _set_path(root: dict[str, Any], dotted: str, value: Any) -> bool:
    parts = [part for part in str(dotted or "").split(".") if part]
    if not parts or parts[0] not in REVERSIBLE_ROOTS:
        return False
    cursor: dict[str, Any] = root
    for part in parts[:-1]:
        child = cursor.get(part)
        if not isinstance(child, dict):
            return False
        cursor = child
    cursor[parts[-1]] = deepcopy(value)
    return True


def _get_path(root: dict[str, Any], dotted: str) -> tuple[bool, Any]:
    parts = [part for part in str(dotted or "").split(".") if part]
    if not parts or parts[0] not in REVERSIBLE_ROOTS:
        return False, None
    cursor: Any = root
    for part in parts:
        if not isinstance(cursor, dict) or part not in cursor:
            return False, None
        cursor = cursor[part]
    return True, deepcopy(cursor)


def start(strategy: dict[str, Any], latest_funnel: dict[str, Any] | None,
          spec: dict[str, Any], *, category_order: list[str],
          now: int | None = None) -> dict[str, Any]:
    """Start exactly one reversible experiment and freeze its category epoch."""
    now = int(time.time()) if now is None else int(now)
    updated = deepcopy(strategy) if isinstance(strategy, dict) else {}
    experiments = updated.get("experiments")
    experiments = experiments if isinstance(experiments, list) else []
    if any(isinstance(row, dict) and row.get("status") == "active"
           for row in experiments):
        return {"ok": False, "reason": "active_experiment_exists", "strategy": updated}
    if not isinstance(spec, dict):
        return {"ok": False, "reason": "spec_invalid", "strategy": updated}
    experiment_id = str(spec.get("id") or "").strip()
    if (
        not experiment_id
        or len(experiment_id) > 96
        or any(not (ch.isalnum() or ch in "._-") for ch in experiment_id)
    ):
        return {"ok": False, "reason": "experiment_id_invalid", "strategy": updated}
    if any(isinstance(row, dict) and row.get("id") == experiment_id
           for row in experiments):
        return {"ok": False, "reason": "experiment_id_duplicate", "strategy": updated}
    field = str(spec.get("field_changed") or "")
    found, old_value = _get_path(updated, field)
    if not found:
        return {"ok": False, "reason": "field_not_code_reversible", "strategy": updated}
    if "new_value" not in spec or spec.get("new_value") == old_value:
        return {"ok": False, "reason": "new_value_missing_or_unchanged", "strategy": updated}
    metric = str(spec.get("target_metric") or "")
    if metric not in RATE_METRICS:
        return {"ok": False, "reason": "target_metric_invalid", "strategy": updated}
    parsed = urlsplit(str(spec.get("source_url") or ""))
    if parsed.scheme != "https" or not parsed.netloc:
        return {"ok": False, "reason": "source_url_invalid", "strategy": updated}
    hypothesis = str(spec.get("hypothesis") or "").strip()
    if not hypothesis:
        return {"ok": False, "reason": "hypothesis_missing", "strategy": updated}
    latest = latest_funnel if isinstance(latest_funnel, dict) else {}
    required = ("ts", "pass_id", "applied", "replied", "won", "paid")
    if any(key not in latest for key in required):
        return {"ok": False, "reason": "fresh_funnel_required", "strategy": updated}
    frozen_order = list(dict.fromkeys(
        str(value).strip() for value in category_order if str(value).strip()
    ))
    if not frozen_order:
        return {"ok": False, "reason": "category_order_required", "strategy": updated}
    if not _set_path(updated, field, spec["new_value"]):
        return {"ok": False, "reason": "field_not_code_reversible", "strategy": updated}
    pass_count = int(updated.get("pass_count") or 0)
    cadence = max(1, int(updated.get("improve_cadence_passes") or 4))
    experiment = {
        "id": experiment_id,
        "ts": now,
        "mode": "isolated",
        "hypothesis": hypothesis,
        "source_url": str(spec["source_url"]),
        "field_changed": field,
        "old_value": old_value,
        "new_value": deepcopy(spec["new_value"]),
        "target_metric": metric,
        "baseline": {key: deepcopy(latest[key]) for key in required},
        "eval_by_pass": pass_count + 2 * cadence,
        "min_post_applications": max(
            8, int(spec.get("min_post_applications") or 8)
        ),
        "frozen_category_order": frozen_order,
        "status": "active",
    }
    experiments.append(experiment)
    updated["experiments"] = experiments
    updated["last_experiment_started_at"] = now
    return {
        "ok": True,
        "reason": "started",
        "strategy": updated,
        "experiment": experiment,
    }


def _evaluation(experiment: dict[str, Any], *, status: str, reason: str,
                now: int, **details: Any) -> dict[str, Any]:
    updated = deepcopy(experiment)
    updated["status"] = status
    updated["evaluated_at"] = now
    updated["evaluation"] = {
        "reason": reason,
        "evaluated_at": now,
        **details,
    }
    return updated


def assess(strategy: dict[str, Any], latest_funnel: dict[str, Any] | None, *,
           now: int | None = None) -> dict[str, Any]:
    """Return an updated strategy and appendable evaluation events without I/O."""
    now = int(time.time()) if now is None else int(now)
    updated = deepcopy(strategy) if isinstance(strategy, dict) else {}
    experiments = updated.get("experiments")
    experiments = experiments if isinstance(experiments, list) else []
    pass_count = int(updated.get("pass_count") or 0)
    active_indexes = [
        index for index, row in enumerate(experiments)
        if isinstance(row, dict) and row.get("status") == "active"
    ]
    due_indexes = [
        index for index in active_indexes
        if not isinstance(experiments[index].get("eval_by_pass"), int)
        or _active_due(experiments[index], pass_count)
    ]
    active_count = len(active_indexes)
    summary = {
        "evaluated": 0,
        "kept": 0,
        "reverted": 0,
        "quarantined": 0,
        "deferred": 0,
    }
    events: list[dict[str, Any]] = []

    for index in due_indexes:
        experiment = experiments[index]
        assert isinstance(experiment, dict)
        terminal: dict[str, Any] | None = None

        if not isinstance(experiment.get("eval_by_pass"), int):
            terminal = _evaluation(
                experiment, status="quarantined",
                reason="evaluation_deadline_missing", now=now,
            )
        elif active_count > 1:
            terminal = _evaluation(
                experiment, status="quarantined",
                reason="overlapping_active_experiments", now=now,
                active_experiment_count=active_count,
            )
        else:
            field = str(experiment.get("field_changed") or "")
            reversible = (
                field.split(".", 1)[0] in REVERSIBLE_ROOTS
                and experiment.get("old_value") is not None
                and experiment.get("new_value") is not None
            )
            if not reversible:
                terminal = _evaluation(
                    experiment, status="quarantined",
                    reason="mutation_not_code_reversible", now=now,
                    field_changed=field,
                )
            else:
                baseline = experiment.get("baseline")
                baseline = baseline if isinstance(baseline, dict) else {}
                metric = str(experiment.get("target_metric") or "")
                baseline_applied = _number(baseline.get("applied"))
                baseline_target = _number(baseline.get(metric))
                latest = latest_funnel if isinstance(latest_funnel, dict) else {}
                latest_applied = _number(latest.get("applied"))
                latest_target = _number(latest.get(metric))
                fresh = (
                    _number(latest.get("ts")) is not None
                    and _number(experiment.get("ts")) is not None
                    and float(latest["ts"]) > float(experiment["ts"])
                    and str(latest.get("pass_id") or "")
                    != str(baseline.get("pass_id") or "")
                )
                if not fresh:
                    experiments[index] = _evaluation(
                        experiment, status="active",
                        reason="fresh_funnel_required", now=now,
                    )
                    summary["deferred"] += 1
                    continue
                if (
                    metric not in RATE_METRICS
                    or baseline_applied is None
                    or baseline_target is None
                    or latest_applied is None
                    or latest_target is None
                    or baseline_applied <= 0
                    or latest_applied < baseline_applied
                    or latest_target < baseline_target
                ):
                    terminal = _evaluation(
                        experiment, status="quarantined",
                        reason="metric_contract_invalid", now=now,
                        target_metric=metric,
                    )
                else:
                    post_applications = int(latest_applied - baseline_applied)
                    minimum = max(1, int(experiment.get("min_post_applications") or 8))
                    if post_applications < minimum:
                        experiments[index] = _evaluation(
                            experiment, status="active",
                            reason="insufficient_post_applications", now=now,
                            post_applications=post_applications,
                            required_post_applications=minimum,
                        )
                        summary["deferred"] += 1
                        continue
                    baseline_rate = baseline_target / baseline_applied
                    observed_rate = (latest_target - baseline_target) / post_applications
                    details = {
                        "target_metric": metric,
                        "baseline_rate": round(baseline_rate, 12),
                        "observed_rate": round(observed_rate, 12),
                        "post_applications": post_applications,
                        "baseline_pass_id": baseline.get("pass_id"),
                        "observed_pass_id": latest.get("pass_id"),
                    }
                    if observed_rate > baseline_rate:
                        terminal = _evaluation(
                            experiment, status="kept",
                            reason="metric_improved", now=now, **details,
                        )
                    elif _set_path(updated, field, experiment.get("old_value")):
                        terminal = _evaluation(
                            experiment, status="reverted",
                            reason="metric_did_not_improve", now=now, **details,
                        )
                    else:
                        terminal = _evaluation(
                            experiment, status="quarantined",
                            reason="revert_path_unavailable", now=now, **details,
                        )

        assert terminal is not None
        experiments[index] = terminal
        status = str(terminal["status"])
        summary["evaluated"] += 1
        summary[status] += 1
        events.append({
            "ts": now,
            "experiment_id": terminal.get("id"),
            "status": status,
            "field_changed": terminal.get("field_changed"),
            "target_metric": terminal.get("target_metric"),
            "evaluation": terminal.get("evaluation"),
        })

    updated["experiments"] = experiments
    if summary["evaluated"] or summary["deferred"]:
        updated["last_experiment_evaluation_at"] = now
    return {"strategy": updated, "events": events, "summary": summary}


def _latest_jsonl(path: Path) -> dict[str, Any] | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def evaluate_files(*, strategy_path: Path, funnel_path: Path, events_path: Path,
                   now: int | None = None) -> dict[str, int]:
    try:
        strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        strategy = {}
    result = assess(strategy, _latest_jsonl(funnel_path), now=now)
    summary = result["summary"]
    if summary["evaluated"] or summary["deferred"]:
        _atomic_json(strategy_path, result["strategy"])
    if result["events"]:
        events_path.parent.mkdir(parents=True, exist_ok=True)
        with events_path.open("a", encoding="utf-8") as handle:
            for event in result["events"]:
                handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    return summary


def start_files(*, strategy_path: Path, funnel_path: Path, events_path: Path,
                decisions_path: Path, spec: dict[str, Any],
                now: int | None = None) -> dict[str, Any]:
    try:
        strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        strategy = {}
    decision = _latest_jsonl(decisions_path) or {}
    order = decision.get("category_order")
    if not isinstance(order, list):
        order = [
            row.get("arm") for row in (decision.get("arms") or [])
            if isinstance(row, dict) and row.get("arm")
        ]
    if not order:
        order = strategy.get("priority_categories") or []
    result = start(
        strategy, _latest_jsonl(funnel_path), spec,
        category_order=order, now=now,
    )
    if not result["ok"]:
        return {"ok": False, "reason": result["reason"]}
    _atomic_json(strategy_path, result["strategy"])
    event = {
        "ts": result["experiment"]["ts"],
        "experiment_id": result["experiment"]["id"],
        "status": "started",
        "field_changed": result["experiment"]["field_changed"],
        "target_metric": result["experiment"]["target_metric"],
        "source_url": result["experiment"]["source_url"],
    }
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return {"ok": True, "reason": "started", "experiment_id": event["experiment_id"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", nargs="?", choices=("evaluate", "start"),
                        default="evaluate")
    parser.add_argument("--strategy", type=Path, default=DEFAULT_STATE / "strategy.json")
    parser.add_argument("--funnel", type=Path, default=DEFAULT_STATE / "gig-funnel.jsonl")
    parser.add_argument(
        "--events", type=Path,
        default=DEFAULT_STATE / "experiment-evaluations.jsonl",
    )
    parser.add_argument(
        "--decisions", type=Path,
        default=DEFAULT_STATE / "category-decisions.jsonl",
    )
    parser.add_argument("--spec-json")
    args = parser.parse_args(argv)
    if args.command == "start":
        try:
            spec = json.loads(args.spec_json or "")
        except json.JSONDecodeError:
            spec = {}
        result = start_files(
            strategy_path=args.strategy,
            funnel_path=args.funnel,
            events_path=args.events,
            decisions_path=args.decisions,
            spec=spec,
        )
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    summary = evaluate_files(
        strategy_path=args.strategy,
        funnel_path=args.funnel,
        events_path=args.events,
    )
    print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
