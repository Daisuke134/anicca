#!/usr/bin/env python3
"""cadence-evidence.py — REQ-LV-104: gathers REAL evidence (ledger reads, file mtimes) for each of
the 7 Cadence Contract loops (clip/affiliate/video/gig/bounty/pm-earner/founder-loop) and calls the
pure `cadence.py` dispatcher on it. This is the IMPURE side of the purity boundary — cadence.py
itself never touches a file; this module is the only thing that does, and its job is narrowly
"read a real timestamp/value, hand it to the pure function," never "decide what health means."

CLI: `python3 cadence-evidence.py status <loop-name>` -> one JSON line:
  {"loop": "clip", "met": true, "streak": 3, "scorecard": "✅posted-today (streak=3)"}
Missing/not-yet-populated source files are NOT an error — they simply produce empty evidence, which
cadence_met() honestly evaluates as unmet (never fabricated, matches this codebase's fail-closed
convention across record_earn.py / loop-report.sh / record-earn.mjs).
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadence import cadence_met, streak  # noqa: E402

JST = zoneinfo.ZoneInfo("Asia/Tokyo")
CONTRACTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cadence-contracts.json")
STREAK_WINDOW_DAYS = 14  # how far back streak() looks; matches this codebase's other rolling-window conventions


def _load_contracts():
    with open(CONTRACTS_PATH) as f:
        d = json.load(f)
    d.pop("_comment", None)
    return d


def _epoch_to_jst_date(ts_seconds: float) -> str:
    return datetime.datetime.fromtimestamp(ts_seconds, tz=JST).date().isoformat()


def _mtime_epoch(path: str):
    try:
        return os.stat(path).st_mtime
    except OSError:
        return None


def _read_jsonl_rows(path: str):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except (json.JSONDecodeError, ValueError):
                continue
    return rows


def _event_dates_from_ts_rows(rows, ts_field="ts"):
    dates = set()
    for r in rows:
        ts = r.get(ts_field)
        if isinstance(ts, (int, float)):
            dates.add(_epoch_to_jst_date(ts))
    return dates


# ---------------------------------------------------------------------------
# Per-loop evidence sources (the only place real paths are known)
# ---------------------------------------------------------------------------

def _clip_ledger_path():
    return os.environ.get("EARN_LEDGER") or os.path.expanduser("~/.openclaw/state/clip-earn-ledger.jsonl")


def _video_metrics_path():
    override = os.environ.get("EARN_VIDEO_METRICS_PATH")
    if override:
        return override
    handle = os.environ.get("EARN_VIDEO_HANDLE", "money_blueprintdaily")
    return os.path.expanduser(f"~/.cloak/earn-video-metrics-{handle}.jsonl")


def _affiliate_metrics_path():
    return os.environ.get("AFFILIATE_METRICS_PATH") or os.path.expanduser("~/.cloak/affiliate-metrics.jsonl")


def _gig_funnel_path():
    return os.environ.get("GIG_FUNNEL_PATH") or os.path.expanduser("~/gig/gig-funnel.jsonl")


# Test-only override seams (mirrors this codebase's own EARN_LEDGER/FOUNDER_DIR/FOUNDER_TEST
# convention, e.g. record_earn.py/founder-loop.sh) so a Tier2 test can exercise this module's REAL
# evidence-gathering logic against real temp fixture files instead of production paths — never
# reaches for a mock of cadence_met/streak themselves (those stay pure and untouched).
LEDGER_PATH_FOR_LOOP = {
    "clip": _clip_ledger_path,
    "affiliate": _affiliate_metrics_path,
    "video": _video_metrics_path,
    "gig": _gig_funnel_path,
}


def _row_exists_event_dates(loop):
    path = LEDGER_PATH_FOR_LOOP[loop]()
    rows = _read_jsonl_rows(path)
    dates = _event_dates_from_ts_rows(rows)
    if dates:
        return dates
    # FALLBACK (clip's existing ledger predates this feature and carries no per-row `ts` field —
    # see self_heal.py's ledger writer, confirmed 2026-07-08). The new metrics/funnel files this
    # feature introduces for affiliate/video/gig (REQ-LV-013/015) DO carry `ts`; this branch only
    # ever fires for a ledger with real rows but none of them timestamped, so the file's own mtime
    # is the most honest single-day signal available — never fabricates a date beyond "this file
    # was genuinely written on this JST calendar day."
    if rows:
        m = _mtime_epoch(path)
        if m is not None:
            return {_epoch_to_jst_date(m)}
    return dates


def _bounty_funnel_path():
    return os.environ.get("BOUNTY_FUNNEL_PATH") or os.path.expanduser(
        "~/profitable-claude/skills/human-funded/bounty/state/bounty-funnel.jsonl")


def _bounty_funnel_rows():
    return _read_jsonl_rows(_bounty_funnel_path())


def _bounty_today_and_previous_checked(today_jst_date):
    rows = _bounty_funnel_rows()
    by_date = {}
    for r in rows:
        ts = r.get("ts")
        checked = r.get("checked")
        if isinstance(ts, (int, float)) and isinstance(checked, (int, float)):
            d = _epoch_to_jst_date(ts)
            # keep the LATEST value seen for each JST day (pass-order in the file = chronological)
            by_date[d] = checked
    today_value = by_date.get(today_jst_date, 0)
    prior_dates = sorted(d for d in by_date if d < today_jst_date)
    previous_value = by_date[prior_dates[-1]] if prior_dates else 0
    return today_value, previous_value, by_date


def _founder_state_md_path():
    return os.environ.get("FOUNDER_STATE_MD_PATH") or os.path.expanduser("~/.anicca-founder/state/STATE.md")


def _founder_loop_marker_jst_date():
    m = _mtime_epoch(_founder_state_md_path())
    return _epoch_to_jst_date(m) if m is not None else None


def _pm_earner_log_path():
    return os.environ.get("PM_EARNER_LOG_PATH") or os.path.expanduser("~/anicca/skills/earn/polymarket-trade/earner.log")


def _pm_earner_ledger_path():
    return os.environ.get("PM_EARNER_LEDGER_PATH") or os.path.expanduser("~/anicca/skills/earn/state/earn-ledger.jsonl")


def _pm_earner_earner_log_epoch():
    return _mtime_epoch(_pm_earner_log_path())


def _pm_earner_redeem_event_dates():
    rows = _read_jsonl_rows(_pm_earner_ledger_path())
    redeem_rows = [r for r in rows if r.get("source") == "polymarket-redeem" or "redeem" in str(r.get("task", "")).lower()]
    return _event_dates_from_ts_rows(redeem_rows)


def gather_evidence(loop: str, today_jst_date: str, now_epoch_seconds: float) -> dict:
    if loop in ("clip", "affiliate", "video", "gig"):
        return {"event_dates": sorted(_row_exists_event_dates(loop))}

    if loop == "bounty":
        today_value, previous_value, _ = _bounty_today_and_previous_checked(today_jst_date)
        return {"today_value": today_value, "previous_value": previous_value}

    if loop == "founder-loop":
        return {"marker_jst_date": _founder_loop_marker_jst_date()}

    if loop == "pm-earner":
        marker = _pm_earner_earner_log_epoch()
        return {
            "by_condition": {
                "hourly-pass": {
                    "marker_epoch_seconds": marker,
                    "now_epoch_seconds": now_epoch_seconds,
                },
                "daily-redeem": {"event_dates": sorted(_pm_earner_redeem_event_dates())},
            }
        }

    raise ValueError(f"no evidence source wired for loop: {loop!r}")


def evidence_by_date_for_streak(loop: str, today_jst_date: str, window_days: int = STREAK_WINDOW_DAYS) -> dict:
    """Build the evidence_by_date map streak() needs by re-gathering each day's own evidence. For
    row-exists loops this is cheap (same event_dates set, evaluated once per day in the window). For
    increment/pass-marker/compound this re-derives each day's evidence from the same underlying
    real sources — never fabricated, just re-sliced per day."""
    today = datetime.date.fromisoformat(today_jst_date)
    out = {}
    if loop in ("clip", "affiliate", "video", "gig"):
        dates = _row_exists_event_dates(loop)
        for i in range(window_days):
            d = (today - datetime.timedelta(days=i)).isoformat()
            out[d] = {"event_dates": [d] if d in dates else []}
        return out

    if loop == "bounty":
        _, _, by_date = _bounty_today_and_previous_checked(today_jst_date)
        sorted_dates = sorted(by_date)
        for i in range(window_days):
            d = (today - datetime.timedelta(days=i)).isoformat()
            prior = [x for x in sorted_dates if x < d]
            out[d] = {
                "today_value": by_date.get(d, 0),
                "previous_value": by_date[prior[-1]] if prior else 0,
            }
        return out

    if loop == "founder-loop":
        marker = _founder_loop_marker_jst_date()
        for i in range(window_days):
            d = (today - datetime.timedelta(days=i)).isoformat()
            out[d] = {"marker_jst_date": marker}
        return out

    if loop == "pm-earner":
        marker = _pm_earner_earner_log_epoch()
        redeem_dates = _pm_earner_redeem_event_dates()
        now = datetime.datetime.now(tz=JST).timestamp()
        for i in range(window_days):
            d = (today - datetime.timedelta(days=i)).isoformat()
            out[d] = {
                "by_condition": {
                    "hourly-pass": {"marker_epoch_seconds": marker, "now_epoch_seconds": now},
                    "daily-redeem": {"event_dates": [d] if d in redeem_dates else []},
                }
            }
        return out

    raise ValueError(f"no evidence source wired for loop: {loop!r}")


def status_for_loop(loop: str) -> dict:
    contracts = _load_contracts()
    contract = contracts[loop]
    now_jst = datetime.datetime.now(tz=JST)
    today_jst_date = now_jst.date().isoformat()
    now_epoch = now_jst.timestamp()

    evidence = gather_evidence(loop, today_jst_date, now_epoch)
    met = cadence_met(today_jst_date, contract, evidence)
    evidence_by_date = evidence_by_date_for_streak(loop, today_jst_date)
    s = streak(evidence_by_date, today_jst_date, contract)

    scorecard = f"{'✅posted-today' if met else '❌missed'} (streak={s})"
    return {"loop": loop, "met": met, "streak": s, "scorecard": scorecard}


def _main():
    if len(sys.argv) < 3 or sys.argv[1] != "status":
        print("usage: cadence-evidence.py status <loop-name>", file=sys.stderr)
        sys.exit(2)
    loop = sys.argv[2]
    print(json.dumps(status_for_loop(loop), ensure_ascii=False))


if __name__ == "__main__":
    _main()
