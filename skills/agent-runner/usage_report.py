#!/usr/bin/env python3
"""Render per-loop daily provider usage from the append-only runner ledger."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


JST = ZoneInfo("Asia/Tokyo")
DEFAULT_LEDGER = (
    Path.home()
    / ".local"
    / "state"
    / "life-manager"
    / "telemetry"
    / "agent-usage.jsonl"
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return rows
    for line in lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _event_date(row: dict[str, Any]) -> str | None:
    try:
        timestamp = str(row["timestamp"]).replace("Z", "+00:00")
        return datetime.fromisoformat(timestamp).astimezone(JST).date().isoformat()
    except (KeyError, TypeError, ValueError):
        return None


def summarize_events(rows: list[dict[str, Any]], date_jst: str) -> dict[str, Any]:
    selected = [row for row in rows if _event_date(row) == date_jst]
    grouped: dict[tuple[Any, ...], dict[str, Any]] = defaultdict(
        lambda: {
            "attempts": 0,
            "successes": 0,
            "failures": 0,
            "measured_attempts": 0,
            "unavailable_attempts": 0,
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "duration_ms": 0,
            "provider_cost_usd": 0.0,
            "cost_measurements": 0,
            "api_equivalent_cost_usd": 0.0,
            "api_equivalent_cost_measurements": 0,
            "actual_billed_cost_usd": 0.0,
            "actual_billed_cost_measurements": 0,
        }
    )
    for row in selected:
        key = (
            row.get("loop"),
            row.get("provider"),
            row.get("model"),
            row.get("effort"),
        )
        group = grouped[key]
        group["attempts"] += 1
        group["successes" if row.get("status") == "success" else "failures"] += 1
        group["duration_ms"] += int(row.get("duration_ms") or 0)
        tokens = row.get("tokens") if isinstance(row.get("tokens"), dict) else {}
        if (
            row.get("measurement") == "provider_reported"
            and isinstance(tokens.get("total"), int)
        ):
            group["measured_attempts"] += 1
            group["input_tokens"] += int(tokens.get("input") or 0)
            group["cached_input_tokens"] += int(tokens.get("cached_input") or 0)
            group["output_tokens"] += int(tokens.get("output") or 0)
            group["total_tokens"] += int(tokens["total"])
        else:
            group["unavailable_attempts"] += 1
        cost = row.get("provider_cost_usd")
        if isinstance(cost, (int, float)) and not isinstance(cost, bool):
            group["provider_cost_usd"] += float(cost)
            group["cost_measurements"] += 1
            if row.get("cost_basis") == "actual_billed":
                group["actual_billed_cost_usd"] += float(cost)
                group["actual_billed_cost_measurements"] += 1
            else:
                group["api_equivalent_cost_usd"] += float(cost)
                group["api_equivalent_cost_measurements"] += 1

    groups = []
    for key, values in sorted(
        grouped.items(), key=lambda item: tuple(str(value or "") for value in item[0])
    ):
        values.update(dict(zip(("loop", "provider", "model", "effort"), key)))
        values["provider_cost_usd"] = round(values["provider_cost_usd"], 8)
        values["api_equivalent_cost_usd"] = round(
            values["api_equivalent_cost_usd"], 8
        )
        values["actual_billed_cost_usd"] = round(values["actual_billed_cost_usd"], 8)
        groups.append(values)

    total_fields = (
        "attempts",
        "successes",
        "failures",
        "measured_attempts",
        "unavailable_attempts",
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "total_tokens",
        "duration_ms",
    )
    totals = {field: sum(group[field] for group in groups) for field in total_fields}
    totals["provider_cost_usd"] = round(
        sum(group["provider_cost_usd"] for group in groups), 8
    )
    totals["cost_measurements"] = sum(
        group["cost_measurements"] for group in groups
    )
    for field in ("api_equivalent_cost_usd", "actual_billed_cost_usd"):
        totals[field] = round(sum(group[field] for group in groups), 8)
    for field in (
        "api_equivalent_cost_measurements",
        "actual_billed_cost_measurements",
    ):
        totals[field] = sum(group[field] for group in groups)
    return {"version": 1, "date_jst": date_jst, "totals": totals, "groups": groups}


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "| Loop | Provider/model | Effort | Attempts | Measured | Unavailable | Tokens | API-equivalent estimate USD | Actual billed USD |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["groups"]:
        model = f"{row['provider']}/{row['model']}"
        estimate = (
            f"{row['api_equivalent_cost_usd']:.6f}"
            if row["api_equivalent_cost_measurements"]
            else "unmeasured"
        )
        actual = (
            f"{row['actual_billed_cost_usd']:.6f}"
            if row["actual_billed_cost_measurements"]
            else "unmeasured"
        )
        lines.append(
            f"| {row['loop']} | {model} | {row['effort'] or '-'} | "
            f"{row['attempts']} | {row['measured_attempts']} | "
            f"{row['unavailable_attempts']} | {row['total_tokens']} | "
            f"{estimate} | {actual} |"
        )
    totals = summary["totals"]
    lines.append(
        f"\nTotal: {totals['total_tokens']} tokens across "
        f"{totals['attempts']} attempts "
        f"({totals['unavailable_attempts']} unavailable)."
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--date")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args()
    date_jst = args.date or (datetime.now(JST).date() - timedelta(days=1)).isoformat()
    summary = summarize_events(read_jsonl(args.ledger), date_jst)
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
