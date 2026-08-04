#!/usr/bin/env python3
"""Detect the failure the gig loop cannot see: it ran, it burned money, it produced nothing.

Deliberately lives OUTSIDE skills/gig-work. The loop must never be able to edit its own
detector — Anthropic measured models sabotaging monitoring in 12% of reward-hack episodes,
and on 2026-08-04 this loop's own auditor reported "STALE" 26 times in a row while the pass
ran fine, because the auditor read a different tree than the pass wrote.

Definition of an outcome, and nothing else counts:
  an externally verifiable side effect — money marked 検収 in earnings.jsonl, or an
  application whose submission was verified against the marketplace's own applied page.
exit code, "status": "ok", and a model's own summary are NOT outcomes. On 2026-08-04 every
pass "succeeded" and 30,180,595 tokens were spent while zero yen arrived.

Alerts (SRE pipeline SLIs, not request-driven ones):
  SILENT_SUCCESS  spend happened in the window and outcomes are zero
  STALE_OUTCOME   nothing has landed for longer than the freshness budget
  LEDGER_ABSENT   a ledger this check depends on is missing/unreadable (meta layer:
                  without it the two above can never fire, and silence would look healthy)
"""
from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

GIG = Path(os.path.expanduser("~/gig"))
EARNINGS = GIG / "earnings.jsonl"
APPLIED = GIG / "applied.jsonl"
TOKENS = Path(os.path.expanduser(
    "~/.local/state/anicca/telemetry/token-budget.jsonl"))


@dataclass
class Findings:
    window_hours: int
    spend_tokens: int = 0
    model_calls: int = 0
    earnings_rows: int = 0
    earnings_jpy: float = 0.0
    verified_applications: int = 0
    hours_since_outcome: float | None = None
    alerts: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def outcomes(self) -> int:
        return self.earnings_rows + self.verified_applications


def _rows(path: Path) -> list[dict]:
    out: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # a truncated append must not blind the whole check
    return out


def _epoch(value: object) -> float | None:
    """Ledgers disagree on time format: unix seconds here, '2026/08/03 16:00' there."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        for fmt in ("%Y/%m/%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return time.mktime(time.strptime(value[:19], fmt))
            except ValueError:
                continue
    return None


def collect(window_hours: int, now: float) -> Findings:
    f = Findings(window_hours=window_hours)
    cutoff = now - window_hours * 3600
    latest_outcome: float | None = None

    if TOKENS.exists():
        # Reservation rows carry no per-call charge; spend only shows up as the running
        # daily_consumed_tokens counter, and it resets each day. Measure it as the sum of
        # per-day (max - min), which survives both the reset and out-of-order rows.
        by_day: dict[str, list[int]] = {}
        for row in _rows(TOKENS):
            if row.get("loop") != "gig":
                continue
            ts = _epoch(row.get("timestamp"))
            if ts is None or ts < cutoff:
                continue
            f.model_calls += 1
            consumed = row.get("daily_consumed_after_tokens")
            if consumed is None:
                consumed = row.get("daily_consumed_tokens")
            if consumed is None:
                continue
            by_day.setdefault(str(row.get("day") or ""), []).append(int(consumed))
        for values in by_day.values():
            f.spend_tokens += max(values) - min(values)
    else:
        f.missing.append(str(TOKENS))

    if EARNINGS.exists():
        for row in _rows(EARNINGS):
            ts = _epoch(row.get("ts"))
            if ts is None:
                continue
            if latest_outcome is None or ts > latest_outcome:
                latest_outcome = ts
            if ts >= cutoff:
                f.earnings_rows += 1
                f.earnings_jpy += float(row.get("jpy") or 0)
    else:
        f.missing.append(str(EARNINGS))

    if APPLIED.exists():
        for row in _rows(APPLIED):
            # Only a readback against the marketplace's own applied page counts.
            if not row.get("applied_page_verified"):
                continue
            ts = _epoch(row.get("ts"))
            if ts is None:
                continue
            if latest_outcome is None or ts > latest_outcome:
                latest_outcome = ts
            if ts >= cutoff:
                f.verified_applications += 1
    else:
        f.missing.append(str(APPLIED))

    if latest_outcome is not None:
        f.hours_since_outcome = round((now - latest_outcome) / 3600, 1)
    return f


def judge(f: Findings, *, min_spend: int, stale_hours: int) -> Findings:
    if f.missing:
        f.alerts.append("LEDGER_ABSENT")
    if f.spend_tokens >= min_spend and f.outcomes == 0:
        f.alerts.append("SILENT_SUCCESS")
    if f.hours_since_outcome is None or f.hours_since_outcome > stale_hours:
        f.alerts.append("STALE_OUTCOME")
    return f


def human(f: Findings) -> str:
    if not f.alerts:
        return (f"🟢 gig: 直近{f.window_hours}時間で成果{f.outcomes}件"
                f"（入金{int(f.earnings_jpy):,}円・応募{f.verified_applications}件）")
    lines = [f"🔴 gig loop が空回りしています（直近{f.window_hours}時間）", ""]
    if "SILENT_SUCCESS" in f.alerts:
        lines += [
            f"・モデル呼び出し {f.model_calls}回・{f.spend_tokens:,}トークンを消費しましたが、",
            "  外部から確認できる成果は0件です（入金も、検証済みの応募も0）。",
        ]
    if "STALE_OUTCOME" in f.alerts:
        since = "一度もありません" if f.hours_since_outcome is None else f"{f.hours_since_outcome}時間前です"
        lines.append(f"・最後に成果が出たのは{since}。")
    if "LEDGER_ABSENT" in f.alerts:
        lines.append(f"・台帳が読めません: {', '.join(f.missing)}（この状態だと上の検知自体が効きません）")
    lines += ["", "Daisの操作は不要です。原因を調べて修復します。"]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window-hours", type=int, default=24)
    ap.add_argument("--min-spend-tokens", type=int, default=500_000)
    ap.add_argument("--stale-hours", type=int, default=48)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    f = judge(collect(args.window_hours, time.time()),
              min_spend=args.min_spend_tokens, stale_hours=args.stale_hours)
    if args.json:
        print(json.dumps({
            "window_hours": f.window_hours, "spend_tokens": f.spend_tokens,
            "model_calls": f.model_calls, "earnings_rows": f.earnings_rows,
            "earnings_jpy": f.earnings_jpy,
            "verified_applications": f.verified_applications,
            "outcomes": f.outcomes, "hours_since_outcome": f.hours_since_outcome,
            "alerts": f.alerts, "missing": f.missing,
        }, ensure_ascii=False))
    else:
        print(human(f))
    return 1 if f.alerts else 0


if __name__ == "__main__":
    raise SystemExit(main())
