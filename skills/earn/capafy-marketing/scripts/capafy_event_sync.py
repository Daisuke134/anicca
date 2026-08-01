#!/usr/bin/env python3
"""Convert Capafy money and marketing source rows into canonical events."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from capafy_event_store import append_event


CENT = Decimal("0.01")
ZERO_MONEY = {
    "currency": "USD",
    "gross_delta": "0.00",
    "pending_delta": "0.00",
    "realized_delta": "0.00",
    "mrr_delta": "0.00",
    "cost_delta": "0.00",
    "contribution_delta": "0.00",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def _cent(value: Any) -> Decimal:
    return _decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def _money_text(value: Decimal) -> str:
    return f"{value.quantize(CENT, rounding=ROUND_HALF_UP):.2f}"


def _timestamp(value: Any) -> str:
    return datetime.fromtimestamp(int(value), timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _date_timestamp(value: str) -> str:
    return f"{value}T00:00:00Z"


def _reel_shortcode(url: str) -> str | None:
    parsed = urlparse(str(url))
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme != "https" or not parsed.netloc or len(parts) != 2 or parts[0] != "reel":
        return None
    return parts[1]


def _event(
    *,
    event_id: str,
    event_type: str,
    occurred_at: str,
    loop: str,
    entity_type: str,
    entity_id: str,
    summary: str,
    money: dict[str, str] | None = None,
    metrics: dict[str, int] | None = None,
    urls: list[str] | None = None,
    labels: list[str] | None = None,
    source_producer: str,
    source_id: str,
    source_row: Any,
) -> dict:
    return {
        "schema_version": 1,
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "loop": loop,
        "entity": {"type": entity_type, "id": entity_id},
        "correlation_id": None,
        "summary": summary,
        "status": {"before": None, "after": "measured"},
        "money": {**ZERO_MONEY, **(money or {})},
        "metrics": metrics or {},
        "public_evidence": {"urls": urls or [], "labels": labels or []},
        "technical_evidence_ref": event_id,
        "source": {
            "producer": source_producer,
            "source_id": source_id,
            "source_digest": _digest(source_row),
        },
        "next": {"owner": "company", "retry_at": None},
    }


def events_from_sales_rows(rows: list[dict]) -> list[dict]:
    events: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for row in sorted(rows, key=lambda item: (str(item.get("date") or ""), int(item.get("ts") or 0))):
        if row.get("source") != "capafy-sales" or not row.get("date"):
            continue
        identity = (str(row["source"]), str(row["date"]))
        if identity in seen:
            continue
        seen.add(identity)
        gross = _cent(row.get("gross_usd"))
        orders = max(0, int(row.get("orders") or 0))
        if gross == 0 and orders == 0:
            continue
        date = str(row["date"])
        events.append(
            _event(
                event_id=f"capafy:order.received:{date}:daily-aggregate",
                event_type="order.received",
                occurred_at=_date_timestamp(date),
                loop="company",
                entity_type="order_batch",
                entity_id=date,
                summary=f"Reconciled {orders} Capafy order(s) for {date}.",
                money={"gross_delta": _money_text(gross)},
                metrics={"orders": orders},
                labels=["gross buyer payment; settlement tracked separately"],
                source_producer="capafy_earn_reconcile",
                source_id=f"capafy-sales:{date}",
                source_row=row,
            )
        )
    return events


def events_from_payout_rows(rows: list[dict]) -> list[dict]:
    events: list[dict] = []
    pending = Decimal("0.00")
    realized = Decimal("0.00")
    for row in sorted(rows, key=lambda item: (int(item.get("ts") or 0), str(item.get("date") or ""))):
        if row.get("source") != "capafy-payout" or not row.get("date"):
            continue
        date = str(row["date"])
        current_pending = _cent(row.get("balance_payout_usd"))
        pending_delta = current_pending - pending
        if pending_delta != 0:
            events.append(
                _event(
                    event_id=f"capafy:balance.reconciled:{date}:balance-payout",
                    event_type="balance.reconciled",
                    occurred_at=_timestamp(row.get("ts") or 0),
                    loop="company",
                    entity_type="seller_balance",
                    entity_id="capafy-bank-wire",
                    summary="Reconciled the pending Capafy seller balance.",
                    money={"pending_delta": _money_text(pending_delta)},
                    labels=["pending unpaid seller balance; not a bank payout"],
                    source_producer="capafy_earn_reconcile",
                    source_id=f"capafy-payout:{date}:pending",
                    source_row=row,
                )
            )
            pending = current_pending

        current_realized = _cent(row.get("total_payout_usd"))
        if current_realized > realized:
            realized_delta = current_realized - realized
            events.append(
                _event(
                    event_id=f"capafy:payout.received:{date}:bank-total",
                    event_type="payout.received",
                    occurred_at=_timestamp(row.get("ts") or 0),
                    loop="company",
                    entity_type="payout",
                    entity_id="capafy-bank-wire",
                    summary="Reconciled a positive realized Capafy bank payout delta.",
                    money={
                        "realized_delta": _money_text(realized_delta),
                        "contribution_delta": _money_text(realized_delta),
                    },
                    labels=["realized bank payout"],
                    source_producer="capafy_earn_reconcile",
                    source_id=f"capafy-payout:{date}:realized",
                    source_row=row,
                )
            )
            realized = current_realized
    return events


def events_from_cost_rows(rows: list[dict]) -> list[dict]:
    events: list[dict] = []
    totals: dict[str, Decimal] = {}
    for row in sorted(rows, key=lambda item: int(item.get("ts") or 0)):
        provider = str(row.get("provider") or "")
        if not provider or row.get("total_usage_usd") is None:
            continue
        current = _cent(row["total_usage_usd"])
        prior = totals.get(provider, Decimal("0.00"))
        if current < prior:
            continue
        delta = current - prior
        totals[provider] = current
        if delta == 0:
            continue
        ts = int(row.get("ts") or 0)
        events.append(
            _event(
                event_id=f"capafy:cost.measured:{provider}:{ts}",
                event_type="cost.measured",
                occurred_at=_timestamp(ts),
                loop="company",
                entity_type="provider_cost",
                entity_id=provider,
                summary=f"Measured a ${_money_text(delta)} {provider} cost increase.",
                money={
                    "cost_delta": _money_text(delta),
                    "contribution_delta": _money_text(-delta),
                },
                labels=["public amount rounded to cents; exact source retained privately"],
                source_producer="capafy-cost-reconcile",
                source_id=f"{provider}:{ts}",
                source_row=row,
            )
        )
    return events


def events_from_attribution_rows(
    rows: list[dict], verification_clicks: dict[str, int]
) -> list[dict]:
    events: list[dict] = []
    for row in sorted(rows, key=lambda item: str(item.get("date") or "")):
        date = str(row.get("date") or "")
        if not date:
            continue
        for agent in row.get("agents") or []:
            agent_id = str(agent.get("agent_id") or "")
            if not agent_id:
                continue
            excluded = max(0, int(verification_clicks.get(agent_id, 0)))
            clicks = max(0, int(agent.get("clicks") or 0) - excluded)
            labels = []
            if excluded:
                word = "two" if excluded == 2 else str(excluded)
                labels.append(f"{word} deployment-verification clicks excluded")
            events.append(
                _event(
                    event_id=f"capafy:content.measured:campaign:{agent_id}:{date}",
                    event_type="content.measured",
                    occurred_at=_date_timestamp(date),
                    loop="marketer",
                    entity_type="content",
                    entity_id=f"campaign:{agent_id}",
                    summary=f"Measured attributed campaign clicks for Capafy listing {agent_id}.",
                    metrics={"clicks": clicks},
                    urls=[f"https://capafy-skills-daily.netlify.app/go/{agent_id}"],
                    labels=labels,
                    source_producer="pull_attribution",
                    source_id=f"attribution:{date}:{agent_id}",
                    source_row=agent,
                )
            )
    return events


def events_from_ig_metrics(rows: list[dict]) -> list[dict]:
    events: list[dict] = []
    for row in sorted(rows, key=lambda item: int(item.get("ts") or 0)):
        reel_url = str(row.get("reel_url") or "")
        shortcode = _reel_shortcode(reel_url)
        if not shortcode:
            continue
        ts = int(row.get("ts") or 0)
        metrics = {
            field: max(0, int(row[field]))
            for field in ("views", "likes", "comments")
            if row.get(field) is not None
        }
        if not metrics:
            continue
        events.append(
            _event(
                event_id=f"capafy:content.measured:instagram:{shortcode}:{ts}",
                event_type="content.measured",
                occurred_at=_timestamp(ts),
                loop="marketer",
                entity_type="content",
                entity_id=f"instagram:{shortcode}",
                summary="Measured the latest public Instagram Reel engagement snapshot.",
                metrics=metrics,
                urls=[reel_url],
                labels=["cumulative snapshot; replace rather than sum"],
                source_producer="ig_metrics",
                source_id=f"instagram:{shortcode}:{ts}",
                source_row=row,
            )
        )
    return events


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _match_source_row(event: dict, candidates: list[dict]) -> dict:
    wanted = event["source"]["source_digest"]
    return next((row for row in candidates if _digest(row) == wanted), {})


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    repo_skills = Path(__file__).resolve().parents[3]
    defaults = {
        "money": repo_skills / "self/capafy-loop/state/capafy-earn-ledger.jsonl",
        "cost": Path(os.path.expanduser("~/.openclaw/logs/capafy-loop-daily.log")),
        "attribution": Path(os.path.expanduser("~/.openclaw/state/capafy-attribution.jsonl")),
        "metrics": Path(os.path.expanduser("~/.openclaw/state/capafy-marketing-ig-metrics.jsonl")),
        "ledger": Path(os.path.expanduser("~/.openclaw/state/capafy-revenue-events.jsonl")),
        "evidence": Path(os.path.expanduser("~/.openclaw/state/capafy-revenue-evidence")),
    }
    for name in ("sync-money", "sync-attribution", "sync-metrics", "sync-all"):
        command = commands.add_parser(name)
        command.add_argument("--money-ledger", type=Path, default=defaults["money"])
        command.add_argument("--cost-log", type=Path, default=defaults["cost"])
        command.add_argument("--attribution-ledger", type=Path, default=defaults["attribution"])
        command.add_argument("--metrics-ledger", type=Path, default=defaults["metrics"])
        command.add_argument("--verification-clicks-json", default='{"4866150011":2}')
        command.add_argument("--ledger", type=Path, default=defaults["ledger"])
        command.add_argument("--evidence-dir", type=Path, default=defaults["evidence"])
    return parser


def _main() -> int:
    args = _parser().parse_args()
    conflicts = 0
    try:
        verification_clicks = json.loads(args.verification_clicks_json)
        if not isinstance(verification_clicks, dict):
            raise ValueError("verification clicks must be a JSON object")

        groups: dict[str, tuple[list[dict], list[dict], Path]] = {}
        if args.command in {"sync-money", "sync-all"}:
            money_rows = _read_jsonl(args.money_ledger)
            groups["money"] = (
                events_from_sales_rows(money_rows) + events_from_payout_rows(money_rows),
                money_rows,
                args.money_ledger,
            )
            cost_rows = _read_jsonl(args.cost_log)
            groups["cost"] = (events_from_cost_rows(cost_rows), cost_rows, args.cost_log)
        if args.command in {"sync-attribution", "sync-all"}:
            attribution_rows = _read_jsonl(args.attribution_ledger)
            attribution_sources = [
                agent
                for row in attribution_rows
                for agent in (row.get("agents") or [])
                if isinstance(agent, dict)
            ]
            groups["attribution"] = (
                events_from_attribution_rows(attribution_rows, verification_clicks),
                attribution_sources,
                args.attribution_ledger,
            )
        if args.command in {"sync-metrics", "sync-all"}:
            metric_rows = _read_jsonl(args.metrics_ledger)
            groups["metrics"] = (
                events_from_ig_metrics(metric_rows),
                metric_rows,
                args.metrics_ledger,
            )

        source_counts: dict[str, dict[str, int]] = {}
        for source_name, (events, candidates, source_path) in groups.items():
            appended = 0
            duplicates = 0
            for event in events:
                source_row = _match_source_row(event, candidates)
                evidence = {"source": source_row, "source_path": str(source_path)}
                try:
                    result = append_event(args.ledger, event, evidence, args.evidence_dir)
                except ValueError:
                    conflicts += 1
                    raise
                appended += int(result.appended)
                duplicates += int(not result.appended)
            source_counts[source_name] = {
                "observed": len(events),
                "appended": appended,
                "duplicates": duplicates,
            }
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc), "conflicts": conflicts}), file=sys.stderr)
        return 2

    output = {
        "observed": sum(value["observed"] for value in source_counts.values()),
        "appended": sum(value["appended"] for value in source_counts.values()),
        "duplicates": sum(value["duplicates"] for value in source_counts.values()),
        "conflicts": conflicts,
        "sources": source_counts,
    }
    print(json.dumps(output, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
