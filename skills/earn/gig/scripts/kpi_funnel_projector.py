#!/usr/bin/env python3
"""Deterministically rebuild hour/day/seven-day funnels from validated KPI records."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from kpi_contract import validate_kpi_record
from kpi_reconciler import ReconciliationError, reconcile_state


JST = ZoneInfo("Asia/Tokyo")
LANE_STAGES = {
    "storefront": ("impression", "view", "inquiry", "qualified", "estimate_order", "settled"),
    "apply": ("eligible_opportunity", "application", "reply", "qualified", "estimate_order", "settled"),
}
EVENT_STAGE = {
    "inquiry_received": "inquiry", "qualified": "qualified",
    "estimate_sent": "estimate_order", "order_confirmed": "estimate_order",
    "application_submitted": "application", "reply_received": "reply",
    "settled": "settled",
}
STAGE_IDENTITY = {
    "inquiry": "thread_id", "qualified": "thread_id", "application": "application_id",
    "reply": "thread_id", "estimate_order": "offer_id", "settled": "payment_receipt_id",
}


class ProjectionError(ValueError):
    pass


def _time(value: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ProjectionError("invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise ProjectionError("timestamp requires timezone")
    return parsed.astimezone(JST)


def _period_windows(as_of: str) -> dict[str, tuple[dt.datetime, dt.datetime]]:
    moment = _time(as_of)
    end = moment.replace(minute=0, second=0, microsecond=0)
    return {
        "hour": (end - dt.timedelta(hours=1), end),
        "day": (end.replace(hour=0), end),
        "seven_day": (end - dt.timedelta(days=7), end),
    }


def _canonical(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _dedupe(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, str]:
    by_id: dict[str, tuple[str, dict[str, Any]]] = {}
    total = 0
    for record in records:
        total += 1
        try:
            validate_kpi_record(record)
        except ValueError as exc:
            raise ProjectionError("invalid KPI record") from exc
        record_id = str(record.get("event_id") or record.get("snapshot_id") or "")
        canonical = _canonical(record)
        previous = by_id.get(record_id)
        if previous is not None and previous[0] != canonical:
            raise ProjectionError("conflicting record id")
        by_id[record_id] = (canonical, record)
    ordered = [value[1] for _, value in sorted(by_id.items())]
    receipts: set[str] = set()
    for record in ordered:
        if record["record_kind"] == "event" and _time(record["observed_at"]) < _time(
            record["occurred_at"]
        ):
            raise ProjectionError("event observed before occurrence")
        if (
            record["record_kind"] == "metric_snapshot"
            and record["window"]["complete"] is True
            and _time(record["observed_at"]) < _time(record["window"]["end"])
        ):
            raise ProjectionError("complete snapshot observed before window end")
        if record["record_kind"] != "event" or record["event_name"] not in {
            "settled", "refund"
        }:
            continue
        receipt = record["identity"]["payment_receipt_id"]
        if receipt in receipts:
            raise ProjectionError("duplicate payment receipt")
        receipts.add(receipt)
    digest = hashlib.sha256(
        "\n".join(_canonical(record) for record in ordered).encode("utf-8")
    ).hexdigest()
    return ordered, total, digest


def _known(value: int) -> dict[str, Any]:
    return {"status": "known", "value": value}


def _unknown(reason: str = "no complete evidence") -> dict[str, Any]:
    return {"status": "unknown", "value": None, "reason": reason}


def _snapshot_value(
    snapshots: list[dict[str, Any]], lane: str, stage: str, metric: str,
) -> dict[str, Any] | None:
    selected = [
        row for row in snapshots
        if row["acquisition_lane"] == lane and row["stage"] == stage
        and row["metric_name"] == metric
    ]
    if not selected:
        return None
    scopes = {row["aggregation_scope"] for row in selected}
    if len(scopes) > 1:
        raise ProjectionError("mixed snapshot scopes")
    known_rows = [row for row in selected if row["value"]["status"] == "known"]
    if len(known_rows) != len(selected):
        return _unknown("snapshot value unknown")
    if "lane_total" in scopes:
        if len(known_rows) != 1:
            raise ProjectionError("multiple lane-total snapshots")
        return _known(int(known_rows[0]["value"]["value"]))
    by_dimension: dict[str, int] = {}
    for row in known_rows:
        key = _canonical(row["dimension"])
        if key in by_dimension:
            raise ProjectionError("duplicate entity snapshot")
        by_dimension[key] = int(row["value"]["value"])
    return _known(sum(by_dimension.values()))


def _event_stage_key(event: dict[str, Any], stage: str) -> str:
    field = STAGE_IDENTITY[stage]
    value = event["identity"].get(field)
    if not isinstance(value, str) or not value:
        raise ProjectionError(f"{stage} event requires exact {field}")
    return value


def _conversions(stages: tuple[str, ...], counts: dict[str, dict[str, Any]]):
    conversions: list[dict[str, Any]] = []
    first_dropoff = None
    for upstream, downstream in zip(stages, stages[1:]):
        left, right = counts[upstream], counts[downstream]
        item: dict[str, Any] = {"from": upstream, "to": downstream}
        if left["status"] != "known" or right["status"] != "known":
            item.update(status="unknown", rate=None, reason="missing stage evidence")
        elif left["value"] == 0:
            item.update(status="unknown", rate=None, reason="zero denominator")
        elif right["value"] > left["value"]:
            item.update(status="unknown", rate=None, reason="non-monotonic window counts")
        else:
            lost = left["value"] - right["value"]
            item.update(status="known", rate=round(right["value"] / left["value"], 4), lost=lost)
            if first_dropoff is None and lost > 0:
                first_dropoff = {
                    "from": upstream, "to": downstream, "lost": lost, "rate": item["rate"]
                }
        conversions.append(item)
    return conversions, first_dropoff


def _lane_projection(
    lane: str, events: list[dict[str, Any]], snapshots: list[dict[str, Any]], end: dt.datetime,
) -> dict[str, Any]:
    stages = LANE_STAGES[lane]
    event_keys: dict[str, set[str]] = {stage: set() for stage in stages}
    money_events: list[dict[str, Any]] = []
    for event in events:
        if event["acquisition_lane"] != lane:
            continue
        stage = EVENT_STAGE.get(event["event_name"])
        if stage in event_keys:
            event_keys[stage].add(_event_stage_key(event, stage))
        if event["event_name"] in {"settled", "refund"}:
            money_events.append(event)
    counts: dict[str, dict[str, Any]] = {}
    for stage in stages:
        snap = _snapshot_value(snapshots, lane, stage, "stage_count")
        if snap is not None and event_keys[stage]:
            raise ProjectionError("event and snapshot sources overlap")
        if snap is not None:
            counts[stage] = snap
        elif event_keys[stage]:
            counts[stage] = _known(len(event_keys[stage]))
        else:
            counts[stage] = _unknown()
    net_snapshot = _snapshot_value(snapshots, lane, "settled", "net_jpy")
    if net_snapshot is not None and money_events:
        raise ProjectionError("event and snapshot money sources overlap")
    if net_snapshot is not None:
        net_jpy = net_snapshot
    elif money_events:
        net_jpy = _known(sum(event["amount"]["net_jpy"] for event in money_events))
    else:
        net_jpy = _unknown()
    lane_records = [row for row in events + snapshots if row["acquisition_lane"] == lane]
    if lane_records:
        latest = max(_time(row["observed_at"]) for row in lane_records)
        freshness = {
            "status": "known", "observed_at": latest.isoformat(timespec="seconds"),
            "lag_seconds": max(0, int((end - latest).total_seconds())),
        }
    else:
        freshness = {"status": "unknown", "observed_at": None, "lag_seconds": None}
    conversions, first_dropoff = _conversions(stages, counts)
    return {
        "stages": counts, "conversions": conversions, "first_dropoff": first_dropoff,
        "net_jpy": net_jpy, "freshness": freshness,
    }


def _project_period(
    records: list[dict[str, Any]], start: dt.datetime, end: dt.datetime,
) -> dict[str, Any]:
    events = [
        row for row in records if row["record_kind"] == "event"
        and start <= _time(row["occurred_at"]) < end
        and _time(row["observed_at"]) <= end
    ]
    snapshots = [
        row for row in records if row["record_kind"] == "metric_snapshot"
        and row["window"]["complete"] is True
        and _time(row["window"]["start"]) == start
        and _time(row["window"]["end"]) == end
        and _time(row["observed_at"]) <= end
    ]
    if any(row["metric_name"] == "net_jpy" and row["stage"] != "settled"
           for row in snapshots):
        raise ProjectionError("net_jpy snapshot must use settled stage")
    lanes = {
        lane: _lane_projection(lane, events, snapshots, end) for lane in LANE_STAGES
    }
    unknown_money = [
        row for row in events if row["acquisition_lane"] == "unknown"
        and row["event_name"] in {"settled", "refund"}
    ]
    unknown_count_snapshot = _snapshot_value(snapshots, "unknown", "settled", "stage_count")
    unknown_net_snapshot = _snapshot_value(snapshots, "unknown", "settled", "net_jpy")
    if unknown_count_snapshot is not None and any(
        row["event_name"] == "settled" for row in unknown_money
    ):
        raise ProjectionError("event and snapshot sources overlap")
    if unknown_net_snapshot is not None and unknown_money:
        raise ProjectionError("event and snapshot money sources overlap")
    if unknown_count_snapshot is not None:
        unknown_count = unknown_count_snapshot
    elif any(row["event_name"] == "settled" for row in unknown_money):
        unknown_count = _known(sum(row["event_name"] == "settled" for row in unknown_money))
    else:
        unknown_count = _unknown()
    if unknown_net_snapshot is not None:
        unknown_net = unknown_net_snapshot
    elif unknown_money:
        unknown_net = _known(sum(row["amount"]["net_jpy"] for row in unknown_money))
    else:
        unknown_net = _unknown()

    count_parts = [lanes[lane]["stages"]["settled"] for lane in LANE_STAGES] + [unknown_count]
    net_parts = [lanes[lane]["net_jpy"] for lane in LANE_STAGES] + [unknown_net]

    def combine(parts: list[dict[str, Any]]) -> dict[str, Any]:
        if not all(part["status"] == "known" for part in parts):
            return _unknown()
        return _known(sum(part["value"] for part in parts))

    all_count, all_net = combine(count_parts), combine(net_parts)
    conserved = True if all_count["status"] == all_net["status"] == "known" else None
    return {
        "window": {"start": start.isoformat(timespec="seconds"),
                   "end": end.isoformat(timespec="seconds"), "timezone": "Asia/Tokyo"},
        "lanes": lanes,
        "unknown": {"settled_count": unknown_count, "net_jpy": unknown_net},
        "all": {"settled_count": all_count, "net_jpy": all_net},
        "conserved": conserved,
    }


def project_records(records: Iterable[dict[str, Any]], *, as_of: str) -> dict[str, Any]:
    unique, total, digest = _dedupe(records)
    periods = {
        name: _project_period(unique, start, end)
        for name, (start, end) in _period_windows(as_of).items()
    }
    return {
        "schema_version": 1, "as_of": _period_windows(as_of)["hour"][1].isoformat(timespec="seconds"),
        "input": {"records": total, "unique_records": len(unique), "content_sha256": digest},
        "periods": periods,
    }


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    def reject_constant(_value: str):
        raise ValueError("non-standard JSON constant")
    try:
        rows = [json.loads(line, parse_constant=reject_constant)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ProjectionError("malformed KPI JSONL") from exc
    if not all(isinstance(row, dict) for row in rows):
        raise ProjectionError("malformed KPI JSONL")
    return rows


def project_state(
    state_dir: Path, *, as_of: str, records_path: Path | None = None,
) -> dict[str, Any]:
    try:
        settlement_events = reconcile_state(state_dir)["events"]
    except ReconciliationError as exc:
        raise ProjectionError("settlement reconciliation failed") from exc
    extra = _jsonl(records_path) if records_path is not None else []
    return project_records([*settlement_events, *extra], as_of=as_of)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--records", type=Path)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    json.dump(
        project_state(args.state_dir, as_of=args.as_of, records_path=args.records),
        sys.stdout, ensure_ascii=False, indent=2,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
