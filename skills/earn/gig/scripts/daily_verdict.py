#!/usr/bin/env python3
"""A19: four-layer daily health verdict — liveness / coverage / productivity / economics.

The 2026-08-01 outage proved the daily report judged itself by raw row counts and
pass status, so a morning with six days of zero revenue, 0% pass success and no
lane evidence still read as success. This module is the code-owned prohibition:
each layer is judged separately from the loop's own ledgers (§6 four-layer
table), and the whole day may only be GREEN when every layer is GREEN.

Deterministic bookkeeping only. No model calls (§4.2: reporting is bookkeeping,
not judgment). External BP: symptom-based alerting — judge by "did money and
applications actually happen", not by "did the pass claim success"
(Google SRE Book, Monitoring Distributed Systems).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

JST = timezone(timedelta(hours=9))

GREEN = "GREEN"
WARN = "WARN"
RED = "RED"
LAYER_NAMES = ("liveness", "coverage", "productivity", "economics")

SETTLED_STATES = {"検収", "支払", "検収完了", "completed", "paid"}
# Economics is RED when settled net revenue has been flat for this many
# consecutive JST days including today. 3 mirrors the productivity rule
# ("3 wakes with zero effect") and the A19 done-evidence ("3 days of deltas").
ZERO_SETTLEMENT_RED_DAYS = 3
# The pass schedule is hourly; a heartbeat older than this means at least one
# scheduled wake was missed. Matches the auditor's own STALE threshold scale.
STALE_HEARTBEAT_MINUTES = 90
# Three hourly wakes in a row with zero real side effects anywhere -> WARN.
EFFECT_SILENCE_WARN_HOURS = 3


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not Path(path).exists():
        return rows
    for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _epoch(value: Any) -> float | None:
    """Read a ledger timestamp: epoch seconds, ISO-8601, or JST '%Y/%m/%d %H:%M'."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except ValueError:
        pass
    try:
        return datetime.strptime(text, "%Y/%m/%d %H:%M").replace(tzinfo=JST).timestamp()
    except ValueError:
        return None


def overall_verdict(layers: dict[str, dict[str, Any]]) -> str:
    """One RED layer makes the day RED; GREEN requires all four GREEN.

    This is the structural ban on false-OK: there is no code path that can
    print success while any layer is failing.
    """
    verdicts = [str(layer.get("verdict")) for layer in layers.values()]
    if any(verdict == RED for verdict in verdicts):
        return RED
    if any(verdict == WARN for verdict in verdicts):
        return WARN
    if verdicts and all(verdict == GREEN for verdict in verdicts):
        return GREEN
    return RED  # missing or malformed layer = fail closed, never GREEN


def _liveness(auditor_rows: list[dict[str, Any]], now_epoch: float) -> dict[str, Any]:
    window = [
        row for row in auditor_rows
        if isinstance(row.get("ts"), (int, float))
        and now_epoch - 86400 <= float(row["ts"]) <= now_epoch
    ]
    if not window:
        return {
            "verdict": RED,
            "reason_ja": "直近24時間、監視の記録がありません（欠測扱い）",
        }
    latest = max(window, key=lambda row: float(row["ts"]))
    stale_detections = sum(1 for row in window if row.get("progressing") is False)
    age_min = latest.get("heartbeat_age_min")
    latest_stale = latest.get("progressing") is False or (
        isinstance(age_min, (int, float)) and float(age_min) > STALE_HEARTBEAT_MINUTES
    )
    if latest_stale:
        shown = int(age_min) if isinstance(age_min, (int, float)) else "?"
        return {
            "verdict": RED,
            "reason_ja": f"定時の巡回が{shown}分間止まっています（監視の実測）",
        }
    if stale_detections:
        return {
            "verdict": WARN,
            "reason_ja": f"直近24時間に巡回の欠測を{stale_detections}回検出しました（現在は復帰）",
        }
    return {"verdict": GREEN, "reason_ja": "定時の巡回は予定どおり動いています"}


def _coverage(missing: list[str], not_run_total: int) -> dict[str, Any]:
    if missing:
        return {
            "verdict": RED,
            "reason_ja": f"4つの仕事のうち{len(missing)}つで確認記録が欠けています",
        }
    if not_run_total:
        return {
            "verdict": RED,
            "reason_ja": f"実行されなかった確認が{not_run_total}回あります",
        }
    return {"verdict": GREEN, "reason_ja": "4つの仕事すべてに確認記録があります"}


def _productivity(gig_dir: Path, now_epoch: float) -> tuple[dict[str, Any], dict[str, int]]:
    applied_rows = _jsonl(gig_dir / "applied.jsonl")
    progress_rows = _jsonl(gig_dir / "paid-progress.jsonl")
    listing_rows = _jsonl(gig_dir / "shuppin.jsonl")

    def in_24h(row: dict[str, Any]) -> bool:
        moment = _epoch(row.get("ts"))
        return moment is not None and now_epoch - 86400 <= moment <= now_epoch

    counts = {
        "applications": sum(
            1 for row in applied_rows if row.get("status") == "applied" and in_24h(row)
        ),
        "replies_deliveries": sum(
            1 for row in applied_rows
            if row.get("status") in ("replied", "評価依頼", "delivered") and in_24h(row)
        ) + sum(1 for row in progress_rows if in_24h(row)),
        "listings": sum(1 for row in listing_rows if in_24h(row)),
    }
    last_effect = max(
        (
            _epoch(row.get("ts"))
            for row in (*applied_rows, *progress_rows, *listing_rows)
            if _epoch(row.get("ts")) is not None
        ),
        default=None,
    )
    if counts["applications"] == 0:
        # §6: 24h with zero applications is an incident, never a success.
        return (
            {"verdict": RED, "reason_ja": "直近24時間の応募が0件です（異常）"},
            counts,
        )
    if last_effect is None or now_epoch - last_effect > EFFECT_SILENCE_WARN_HOURS * 3600:
        return (
            {
                "verdict": WARN,
                "reason_ja": f"直近{EFFECT_SILENCE_WARN_HOURS}時間、実作業の記録がありません",
            },
            counts,
        )
    return (
        {
            "verdict": GREEN,
            "reason_ja": (
                f"応募{counts['applications']}件・返信/納品{counts['replies_deliveries']}件・"
                f"出品{counts['listings']}件の実作業を確認しました"
            ),
        },
        counts,
    )


def _settled_by_jst_day(gig_dir: Path) -> dict[str, float]:
    totals: dict[str, float] = {}
    for row in _jsonl(gig_dir / "earnings.jsonl"):
        if row.get("status") not in SETTLED_STATES or not row.get("evidence"):
            continue
        moment = _epoch(row.get("ts")) or _epoch(row.get("finished_at"))
        if moment is None:
            continue
        try:
            amount = float(str(row.get("jpy", 0)).replace(",", "") or 0)
        except ValueError:
            continue
        day = datetime.fromtimestamp(moment, JST).date().isoformat()
        totals[day] = totals.get(day, 0.0) + amount
    return totals


def _economics(gig_dir: Path, now: datetime) -> tuple[dict[str, Any], dict[str, Any]]:
    totals = _settled_by_jst_day(gig_dir)
    local = now.astimezone(JST)
    today = local.date()
    settled_today = int(totals.get(today.isoformat(), 0))
    settled_yesterday = int(totals.get((today - timedelta(days=1)).isoformat(), 0))
    streak = 0
    probe = today
    while totals.get(probe.isoformat(), 0) <= 0:
        streak += 1
        probe -= timedelta(days=1)
        if streak >= 365:  # a ledger with no settlement at all
            break
    detail = {
        "settled_today_jpy": settled_today,
        "settled_yesterday_jpy": settled_yesterday,
        "settled_delta_jpy": settled_today - settled_yesterday,
        "zero_settlement_streak_days": streak,
    }
    if settled_today > 0:
        return (
            {
                "verdict": GREEN,
                "reason_ja": f"本日{settled_today:,}円の検収済み入金があります",
            },
            detail,
        )
    if streak >= ZERO_SETTLEMENT_RED_DAYS:
        return (
            {
                "verdict": RED,
                "reason_ja": f"検収済みの入金が{streak}日連続で増えていません",
            },
            detail,
        )
    return (
        {
            "verdict": WARN,
            "reason_ja": f"本日の検収済み入金はまだ0円です（{streak}日目）",
        },
        detail,
    )


def _pass_stats(gig_dir: Path, now_epoch: float) -> tuple[dict[str, int], float | None]:
    def window_ids(path: Path, status: str) -> set[str]:
        ids: set[str] = set()
        for row in _jsonl(path):
            ts = row.get("ts")
            if (
                row.get("status") == status
                and isinstance(row.get("pass_id"), str)
                and isinstance(ts, (int, float))
                and now_epoch - 86400 <= float(ts) <= now_epoch
            ):
                ids.add(str(row["pass_id"]))
        return ids

    succeeded = window_ids(gig_dir / "pass-report.jsonl", "success")
    failed = window_ids(gig_dir / "pass-failures.jsonl", "failed") - succeeded
    last_success = max(
        (
            float(row["ts"])
            for row in _jsonl(gig_dir / "pass-report.jsonl")
            if row.get("status") == "success" and isinstance(row.get("ts"), (int, float))
        ),
        default=None,
    )
    return (
        {
            "succeeded": len(succeeded),
            "failed": len(failed),
            "total": len(succeeded) + len(failed),
        },
        last_success,
    )


def evaluate(
    *,
    gig_dir: Path,
    auditor_log: Path,
    lane_evidence_missing: list[str],
    lane_not_run_total: int,
    now: datetime,
) -> dict[str, Any]:
    """Judge the four layers separately from the loop's own ledgers."""
    if now.tzinfo is None:
        raise ValueError("daily verdict needs an aware timestamp")
    gig_dir = Path(gig_dir)
    now_epoch = now.timestamp()
    productivity, effect_counts = _productivity(gig_dir, now_epoch)
    economics, economics_detail = _economics(gig_dir, now)
    layers = {
        "liveness": _liveness(_jsonl(Path(auditor_log)), now_epoch),
        "coverage": _coverage(list(lane_evidence_missing), int(lane_not_run_total)),
        "productivity": productivity,
        "economics": economics,
    }
    pass_24h, last_success_epoch = _pass_stats(gig_dir, now_epoch)
    return {
        "verdict": overall_verdict(layers),
        "layers": layers,
        "pass_24h": pass_24h,
        "last_success_pass_epoch": last_success_epoch,
        "last_success_pass_jst": (
            datetime.fromtimestamp(last_success_epoch, JST).strftime("%m-%d %H:%M")
            if last_success_epoch is not None
            else None
        ),
        "effects_24h": effect_counts,
        "applications_24h": effect_counts["applications"],
        **economics_detail,
    }
