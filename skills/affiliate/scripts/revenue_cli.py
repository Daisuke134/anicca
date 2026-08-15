#!/usr/bin/env python3
"""Read ElevenLabs PartnerStack overview metrics into a durable local receipt."""

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
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

COMMISSION_FIELDS = {
    "created_at": ("作成日", "Created at"),
    "partnership": ("パートナーシップ", "Partnership"),
    "team_member": ("チームメンバー", "Team member"),
    "offer_name": ("オファー名", "Offer name"),
    "status": ("コミッションステータス", "Commission status"),
    "customer_name": ("顧客名", "Customer name"),
    "customer_email": ("顧客のメールアドレス", "Customer email"),
    "customer_key": ("顧客キー", "Customer key"),
    "customer_location": ("お客様の所在地", "Customer location"),
    "product_key": ("プロダクトキー", "Product key"),
    "action": ("アクション", "Action"),
    "sub_id_1": ("サブID 1", "Sub ID 1"),
    "sub_id_2": ("サブID 2", "Sub ID 2"),
    "sub_id_3": ("サブID 3", "Sub ID 3"),
    "shared_id": ("共有ID", "Shared ID"),
    "clicked_at": ("日付をクリック", "Click date"),
    "click_location": ("場所をクリック", "Click location"),
    "link": ("リンク", "Link"),
    "referrer_page": ("リファラーページ", "Referrer page"),
    "landing_page": ("ランディングページ", "Landing page"),
    "commission_amount": ("コミッション", "Commission"),
    "reward_key": ("コミッション・キー", "Commission key"),
    "target_type": ("ターゲット・タイプ", "Target type"),
}

COMMISSION_STATUS = {
    "pending": "pending",
    "hold": "pending",
    "approved": "approved",
    "scheduled": "approved",
    "declined": "reversed",
    "paid": "paid",
}

PAYOUT_FIELDS = {
    "earned_at": ("獲得済み", "Earned"),
    "program": ("プログラム", "Program"),
    "source": ("ソース", "Source"),
    "status": ("コミッションステータス", "Commission status"),
    "available_at": ("利用可能予定日", "Available on"),
    "amount": ("金額", "Amount"),
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


def present_fields(text, schema):
    found = []
    for key, aliases in schema.items():
        if not any(alias in text for alias in aliases):
            raise RevenueError("provider report schema is incomplete")
        found.append(key)
    return found


def normalize_commission_row(row, currency="USD"):
    key = row.get("reward_key")
    provider_status = row.get("reward_status")
    if not isinstance(key, str) or not key or provider_status not in COMMISSION_STATUS:
        raise RevenueError("commission identity or status is invalid")
    try:
        minor_decimal = Decimal(str(row["commission_amount"])) * 100
    except (KeyError, InvalidOperation, ValueError):
        raise RevenueError("commission amount is invalid") from None
    if minor_decimal != minor_decimal.to_integral_value() or minor_decimal < 0:
        raise RevenueError("commission amount is invalid")
    gross_minor = int(minor_decimal)
    status = COMMISSION_STATUS[provider_status]
    reversal_minor = gross_minor if status == "reversed" else 0
    return {
        "provider_transaction_id": key,
        "provider_status": provider_status,
        "status": status,
        "currency": currency,
        "gross_commission_minor": gross_minor,
        "reversal_minor": reversal_minor,
        "net_commission_minor": gross_minor - reversal_minor,
        "created_at": row.get("created_at_date"),
        "offer": row.get("reward_description"),
        "target_type": row.get("target_type"),
        "action": row.get("action_external_type"),
        "attribution": {
            "sub_id_1": row.get("sub_id_1"),
            "sub_id_2": row.get("sub_id_2"),
            "sub_id_3": row.get("sub_id_3"),
            "shared_id": row.get("shared_id"),
            "clicked_at": row.get("click_created_at_date"),
            "link": row.get("link_path"),
            "referrer": row.get("referral_source"),
            "landing_page": row.get("link_destination_path"),
        },
    }


def navigate_text(ws, request_id, url, ready_markers):
    cdp_call(ws, request_id, "Page.navigate", {"url": url})
    expression = "({url:location.href,text:(document.body&&document.body.innerText)||''})"
    for offset in range(1, 61):
        result = cdp_call(ws, request_id + offset, "Runtime.evaluate", {
            "expression": expression, "returnByValue": True,
        })
        page = result.get("result", {}).get("value", {})
        if any(marker in page.get("text", "") for marker in ready_markers):
            return page
        if "Sign in to PartnerStack" in page.get("text", ""):
            raise RevenueError("PartnerStack authentication is required")
        time.sleep(0.5)
    raise RevenueError("PartnerStack report did not become ready")


def cdp_call_collect(ws, request_id, method, params, events):
    ws.send(json.dumps({"id": request_id, "method": method, "params": params or {}}))
    while True:
        message = json.loads(ws.recv())
        if message.get("method"):
            events.append(message)
        if message.get("id") == request_id:
            if "error" in message:
                raise RevenueError(f"CDP {method} failed")
            return message.get("result", {})


def capture_commission_rows(args):
    pages = [item for item in read_json(f"http://{args.cdp_host}:{args.cdp_port}/json/list") if item.get("type") == "page"]
    if len(pages) != 1:
        raise RevenueError(f"expected one provider tab, found {len(pages)}")
    ws = create_connection(
        f"ws://{args.cdp_host}:{args.cdp_port}/devtools/page/{pages[0]['id']}",
        timeout=20, max_size=None, suppress_origin=True,
    )
    events = []
    try:
        cdp_call_collect(ws, 1, "Network.enable", {}, events)
        cdp_call_collect(ws, 2, "Page.enable", {}, events)
        cdp_call_collect(ws, 3, "Page.navigate", {
            "url": "https://dash.partnerstack.com/reporting/commission_performance",
        }, events)
        request_id = None
        for attempt in range(20):
            time.sleep(0.5)
            cdp_call_collect(ws, 10 + attempt, "Runtime.evaluate", {
                "expression": "document.readyState", "returnByValue": True,
            }, events)
            for event in events:
                if event.get("method") != "Network.responseReceived":
                    continue
                response = event.get("params", {}).get("response", {})
                url = response.get("url", "").split("?", 1)[0]
                if "/api/v2/stats/commission_report/" in url and not url.endswith("/summary"):
                    request_id = event["params"]["requestId"]
            if request_id:
                break
        if not request_id:
            raise RevenueError("PartnerStack commission response was not observed")
        result = cdp_call_collect(ws, 100, "Network.getResponseBody", {"requestId": request_id}, events)
        rows = json.loads(result.get("body", ""))
        if not isinstance(rows, list):
            raise RevenueError("PartnerStack commission response is not a list")
        return rows
    finally:
        try:
            cdp_call_collect(ws, 200, "Page.navigate", {"url": "https://elevenlabs.io/app/home"}, events)
        finally:
            ws.close()


def capture_reports(args):
    pages = [item for item in read_json(f"http://{args.cdp_host}:{args.cdp_port}/json/list") if item.get("type") == "page"]
    if len(pages) != 1:
        raise RevenueError(f"expected one provider tab, found {len(pages)}")
    ws = create_connection(
        f"ws://{args.cdp_host}:{args.cdp_port}/devtools/page/{pages[0]['id']}",
        timeout=20, max_size=None, suppress_origin=True,
    )
    try:
        cdp_call(ws, 1, "Page.enable")
        commissions = navigate_text(
            ws, 10, "https://dash.partnerstack.com/reporting/commission_performance",
            ("コミッション・レポート", "Commission report"),
        )
        payouts = navigate_text(
            ws, 100, "https://dash.partnerstack.com/payouts/rewards",
            ("コミッションおよび引き出し", "Commissions and withdrawals"),
        )
    finally:
        try:
            cdp_call(ws, 200, "Page.navigate", {"url": "https://elevenlabs.io/app/home"})
        finally:
            ws.close()
    commission_rows = capture_commission_rows(args)
    observed_at = datetime.now(timezone.utc).isoformat()
    normalized_rows = [normalize_commission_row(row) for row in commission_rows]
    artifact = {
        "schema_version": 1,
        "receipt_type": "PARTNERSTACK_RENDERED_REPORT_ARTIFACT",
        "observed_at": observed_at,
        "commission_url": commissions["url"],
        "commission_text": commissions["text"],
        "commission_rows": commission_rows,
        "normalized_commissions": normalized_rows,
        "payout_url": payouts["url"],
        "payout_text": payouts["text"],
    }
    artifact_hash = hashlib.sha256(json.dumps(artifact, sort_keys=True).encode()).hexdigest()
    state = args.state.expanduser()
    artifact_path = state / "provider-reports" / "partnerstack" / f"{artifact_hash}.json"
    atomic_write(artifact_path, artifact)
    receipt = {
        "schema_version": 1,
        "receipt_type": "PARTNERSTACK_REPORT_CAPTURE",
        "provider": "elevenlabs",
        "currency_display": "USD",
        "commission_fields": present_fields(commissions["text"], COMMISSION_FIELDS),
        "payout_fields": present_fields(payouts["text"], PAYOUT_FIELDS),
        "generic_transaction_id_available": False,
        "provider_transaction_key": "reward_key",
        "attribution_keys": ["sub_id_1", "sub_id_2", "sub_id_3", "shared_id", "click_created_at_date", "link_path"],
        "commission_row_count": len(commission_rows),
        "commission_row_state": "EMPTY" if not commission_rows else "ROWS_PRESENT",
        "normalizer_state": "NO_LIVE_ROWS" if not commission_rows else "NORMALIZED",
        "payout_row_state": "EMPTY" if ("0 to 0" in payouts["text"] or "0件中0" in payouts["text"]) else "ROWS_PRESENT",
        "rendered_artifact_sha256": artifact_hash,
        "observed_at": observed_at,
    }
    atomic_write(state / "provider-reports" / "partnerstack" / "latest.json", receipt)
    return receipt


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
    parser.add_argument("command", choices=("observe", "capture"))
    parser.add_argument("--cdp-host", default="127.0.0.1")
    parser.add_argument("--cdp-port", type=int, default=9324)
    parser.add_argument("--state", type=Path, default=Path("~/.local/state/life-manager/affiliate"))
    args = parser.parse_args()
    result = observe(args) if args.command == "observe" else capture_reports(args)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RevenueError, OSError, ValueError, KeyError, json.JSONDecodeError):
        print("affiliate revenue: failed closed", file=sys.stderr)
        raise SystemExit(1)
