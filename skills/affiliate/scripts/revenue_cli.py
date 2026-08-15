#!/usr/bin/env python3
"""Read ElevenLabs PartnerStack overview metrics into a durable local receipt."""

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from websocket import create_connection

from provider_cli import atomic_write, cdp_call, read_json


class RevenueError(Exception):
    pass


LABELS = {
    "clicks": ("クリック数", "Clicks"),
    "signups": ("登録数", "Signups"),
    "paid_signups": ("有料会員登録", "Paid signups"),
    "conversion_rate": ("コンバージョン率", "Conversion rate"),
    "revenue_minor": ("収益", "Revenue"),
    "pending_minor": ("支払い待ちのコミッション", "Commissions pending payment"),
    "paid_minor": ("支払い済みコミッション", "Commissions paid"),
    "earnings_per_click_minor": ("クリックあたりの収益", "Earnings per click"),
}


def parse_value(key, value):
    compact = value.strip().replace(",", "")
    if key.endswith("_minor"):
        match = re.fullmatch(r"\$([0-9]+(?:\.[0-9]{2})?)", compact)
        if not match:
            raise RevenueError("invalid USD dashboard value")
        return int(round(float(match.group(1)) * 100))
    if key == "conversion_rate":
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?%", compact):
            raise RevenueError("invalid conversion rate")
        return compact
    if not re.fullmatch(r"[0-9]+", compact):
        raise RevenueError("invalid integer dashboard value")
    return int(compact)


def parse_cards(cards):
    metrics = {}
    for key, aliases in LABELS.items():
        values = [cards[alias] for alias in aliases if alias in cards]
        if len(values) != 1:
            raise RevenueError("dashboard metric is missing or ambiguous")
        metrics[key] = parse_value(key, values[0])
    metrics.update(approved_minor=None, reversed_minor=None)
    return metrics


def extract_cards(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cards = {}
    for key, aliases in LABELS.items():
        candidates = []
        for alias in aliases:
            for index, line in enumerate(lines[:-1]):
                if line != alias:
                    continue
                try:
                    parse_value(key, lines[index + 1])
                except RevenueError:
                    continue
                candidates.append((alias, lines[index + 1]))
        if len(candidates) != 1:
            raise RevenueError("dashboard metric is missing or ambiguous")
        cards[candidates[0][0]] = candidates[0][1]
    return cards


def build_receipt(metrics, previous, observed_at):
    baseline = previous.get("baseline_metrics") or previous.get("metrics") or metrics
    delta = {}
    for key, value in metrics.items():
        base = baseline.get(key)
        delta[key] = value - base if isinstance(value, int) and isinstance(base, int) else None
    return {
        "schema_version": 1,
        "receipt_type": "PARTNERSTACK_OVERVIEW",
        "provider": "elevenlabs",
        "currency": "USD",
        "window": "last_30_days",
        "metrics": metrics,
        "metrics_sha256": hashlib.sha256(json.dumps(metrics, sort_keys=True).encode()).hexdigest(),
        "baseline_metrics": baseline,
        "baseline_observed_at": previous.get("baseline_observed_at") or previous.get("observed_at") or observed_at,
        "delta_from_baseline": delta,
        "attribution_state": "BASELINE_ONLY" if not previous else "DELTA_OBSERVABLE",
        "observed_at": observed_at,
    }


def observe(args):
    pages = [item for item in read_json(f"http://{args.cdp_host}:{args.cdp_port}/json/list") if item.get("type") == "page"]
    if len(pages) != 1:
        raise RevenueError(f"expected one provider tab, found {len(pages)}")
    ws = create_connection(
        f"ws://{args.cdp_host}:{args.cdp_port}/devtools/page/{pages[0]['id']}",
        timeout=20, max_size=None, suppress_origin=True,
    )
    cards = None
    try:
        cdp_call(ws, 1, "Page.enable")
        cdp_call(ws, 2, "Page.navigate", {"url": "https://dash.partnerstack.com/elevenlabsinc"})
        expression = "({url:location.href,text:(document.body&&document.body.innerText)||''})"
        for request_id in range(10, 70):
            result = cdp_call(ws, request_id, "Runtime.evaluate", {"expression": expression, "returnByValue": True})
            page = result.get("result", {}).get("value", {})
            try:
                cards = extract_cards(page.get("text", ""))
                break
            except RevenueError:
                pass
            if "Sign in to PartnerStack" in page.get("text", ""):
                raise RevenueError("PartnerStack authentication is required")
            time.sleep(0.5)
    finally:
        try:
            cdp_call(ws, 100, "Page.navigate", {"url": "https://elevenlabs.io/app/home"})
        finally:
            ws.close()
    if cards is None:
        raise RevenueError("PartnerStack metrics did not become ready")
    metrics = parse_cards(cards)
    state = args.state.expanduser()
    previous = {}
    receipt_path = state / "provider-metrics" / "elevenlabs.json"
    if receipt_path.is_file():
        previous = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt = build_receipt(metrics, previous, datetime.now(timezone.utc).isoformat())
    atomic_write(receipt_path, receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(prog="affiliate revenue")
    parser.add_argument("command", choices=("observe",))
    parser.add_argument("--cdp-host", default="127.0.0.1")
    parser.add_argument("--cdp-port", type=int, default=9324)
    parser.add_argument("--state", type=Path, default=Path("~/.local/state/life-manager/affiliate"))
    args = parser.parse_args()
    result = observe(args)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RevenueError, OSError, ValueError, KeyError, json.JSONDecodeError):
        print("affiliate revenue: failed closed", file=sys.stderr)
        raise SystemExit(1)
