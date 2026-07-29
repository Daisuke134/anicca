"""budget.py — agent-os orchestrator/budgets.py copy+tweak (agent -> loop), REQ-CEO-020..025.
Token/USD budget hard-stop gate (fail-open when config is missing) + soft-warn/hard-stop alert
dedup + cost-event bookkeeping, split into a UTC calendar-month aggregation (hard-stop gate,
REQ-CEO-022/023) and a JST Monday-Sunday week aggregation (bandit reward denominator, REQ-CEO-010/014).

B12 (REQ-CEO-021): pm-earner has no `__REPO_ROOT__/skills/earn/polymarket-trade/` pass-end reporting hook
(Ground truth in behavioral-spec.md, confirmed by grep), so it never appears in `ceo-cost-events.jsonl`
-- the aggregation functions below simply never produce a "pm-earner" key (no zero-fill branch is
needed, callers use dict.get(loop, 0.0))."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

try:
    import zoneinfo

    JST = zoneinfo.ZoneInfo("Asia/Tokyo")
except ImportError:  # pragma: no cover - py<3.9 fallback, not expected in this repo
    JST = timezone(timedelta(hours=9))


def _parse_ts(ts: str) -> datetime:
    dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _safe_float(value, default: float = 0.0) -> float:
    """Coerce a cost-event field to float; a wrong-type value (non-numeric string, nested dict/list,
    etc.) inside an otherwise-valid dict row returns `default` instead of raising (Phase 5 hardening
    Finding F5, same fix as allocator._safe_float)."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------- REQ-CEO-020: cost event (agent-os record_cost_events, single-event copy+tweak) ----------
def build_cost_event(ts: str, loop: str, usd_estimate: float) -> dict:
    """{ts, month_key(UTC), loop, usd_estimate} -- month_key derived from ts, never from wall-clock
    now (deterministic, testable, and correct for events appended slightly late)."""
    month_key = _parse_ts(ts).astimezone(timezone.utc).strftime("%Y-%m")
    return {"ts": ts, "month_key": month_key, "loop": loop, "usd_estimate": usd_estimate}


def record_cost_event(path: str, event: dict) -> None:
    """Atomic append (read-existing + tmp-write + os.replace, same pattern as agent-os
    record_cost_events) — Tier2 I/O boundary, called by each loop's own pass-end hook (REQ-CEO-020),
    never by the CEO WEEKLY pass itself."""
    existing = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            existing = f.read()
    tmp = f"{path}.tmp.{os.getpid()}"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(existing + json.dumps(event, sort_keys=True) + "\n")
    os.replace(tmp, path)


def load_cost_events(path: str) -> list:
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


# ---------- REQ-CEO-021: monthly (UTC calendar month, hard-stop gate) + weekly (JST Mon-Sun, bandit) ----------
def monthly_spend_by_loop(rows: list, month_key: str) -> dict:
    """agent-os monthly_spend_by_agent copy+tweak (agent -> loop). No key is zero-filled for a loop
    that has no rows this month (B12 fallback: pm-earner never appears). A row that parsed as valid
    JSON but is not itself a dict is skipped, not crashed on (Phase 5 hardening Finding F2)."""
    totals: dict = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("month_key") != month_key:
            continue
        loop = row.get("loop")
        usd = _safe_float(row.get("usd_estimate") or 0.0)
        totals[loop] = round(totals.get(loop, 0.0) + usd, 6)
    return totals


def weekly_spend_by_loop(rows: list, week_start_jst_date: str) -> dict:
    """New: weekly_report.py::_rows_in_week-style JST Monday-Sunday week bucketing, for REQ-CEO-010's
    per-loop reward denominator and REQ-CEO-014's company-wide BudgetPacer input. `week_start_jst_date`
    is the JST-local Monday date (YYYY-MM-DD) that opens the bucket [week_start 00:00 JST,
    week_start+7d 00:00 JST). A row that parsed as valid JSON but is not itself a dict is skipped,
    not crashed on (Phase 5 hardening Finding F2)."""
    year, month, day = (int(x) for x in week_start_jst_date.split("-"))
    week_start = datetime(year, month, day, tzinfo=JST)
    week_end = week_start + timedelta(days=7)
    totals: dict = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        dt_jst = _parse_ts(row.get("ts")).astimezone(JST)
        if week_start <= dt_jst < week_end:
            loop = row.get("loop")
            usd = _safe_float(row.get("usd_estimate") or 0.0)
            totals[loop] = round(totals.get(loop, 0.0) + usd, 6)
    return totals


# ---------- REQ-CEO-022/023: budget resolution + fail-open hard-stop gate ----------
def budget_for_loop(cfg: dict | None, loop: str):
    """agent-os budget_for_agent copy+tweak (agent -> loop). Missing config / missing section /
    missing entry (with no 'default' fallback either) -> None (fail-open, gate does not apply)."""
    section = ((cfg or {}).get("budgets")) or {}
    if not section:
        return None
    per_loop = section.get("per_loop") or {}
    entry = per_loop.get(loop)
    if entry is None:
        entry = section.get("default")
    if not entry:
        return None
    soft = entry.get("soft_warn_usd")
    hard = entry.get("hard_stop_usd")
    if soft is None and hard is None:
        return None
    return {"soft_warn_usd": soft, "hard_stop_usd": hard}


def filter_budget_compliant_loops(candidates: list, cfg: dict | None, spend_by_loop: dict):
    """agent-os filter_budget_compliant_agents copy+tweak (agent -> loop). Missing budgets config ->
    ALL candidates pass unchanged (fail-open). Otherwise excludes only candidates whose spend has
    crossed their own hard_stop_usd -- a loop with no budget entry (including pm-earner, REQ-CEO-021
    B12 fallback) always passes (fail-open per-loop)."""
    section = ((cfg or {}).get("budgets")) or {}
    if not section:
        return list(candidates), {}
    passed = []
    skipped = {}
    for loop in candidates:
        budget = budget_for_loop(cfg, loop)
        spend = (spend_by_loop or {}).get(loop, 0.0)
        if budget and budget.get("hard_stop_usd") is not None and spend > budget["hard_stop_usd"]:
            skipped[loop] = {**budget, "spend_usd": spend}
        else:
            passed.append(loop)
    return passed, skipped


def warn_if_budgets_missing(log_path: str, loop: str) -> None:
    """REQ-CEO-023: fail-open log, fired at most once (checked by scanning `log_path` for an existing
    line naming this loop, since this process is not long-running)."""
    marker = f"budget-config-missing loop={loop}"
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as f:
            if marker in f.read():
                return
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} {marker}\n")


# ---------- REQ-CEO-024: soft-warn / hard-stop alert dedup (agent-os check_budget_alerts pattern) ----------
def alert_key(month_key: str, loop: str, threshold_name: str) -> str:
    return f"{month_key}:{loop}:{threshold_name}"


def should_fire_alert(key: str, fired_keys: set) -> bool:
    return key not in fired_keys


def record_alert_fired(path: str, key: str) -> None:
    """Atomic append of a fired-alert dedup record (mirrors record_cost_event's I/O pattern)."""
    existing = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            existing = f.read()
    tmp = f"{path}.tmp.{os.getpid()}"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(existing + json.dumps({"key": key}, sort_keys=True) + "\n")
    os.replace(tmp, path)


def load_fired_alert_keys(path: str) -> set:
    keys = set()
    for row in load_cost_events(path):
        if not isinstance(row, dict):
            continue
        key = row.get("key")
        if key:
            keys.add(str(key))
    return keys


# ---------- REQ-CEO-025: budget_snapshot_for_registry (agent-os remaining_budget copy+tweak) ----------
def budget_snapshot_for_registry(cfg: dict | None, loop: str, spend: float) -> dict:
    budget = budget_for_loop(cfg, loop)
    if budget is None:
        return {"loop": loop, "spend_usd": round(float(spend), 6), "hard_stopped": False}
    hard = budget.get("hard_stop_usd")
    remaining = None if hard is None else max(0.0, round(float(hard) - float(spend), 6))
    return {
        "loop": loop,
        "spend_usd": round(float(spend), 6),
        "soft_warn_usd": budget.get("soft_warn_usd"),
        "hard_stop_usd": hard,
        "remaining_usd": remaining,
        "hard_stopped": bool(hard is not None and float(spend) >= float(hard)),
    }
