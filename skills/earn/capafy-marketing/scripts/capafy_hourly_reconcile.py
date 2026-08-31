#!/usr/bin/env python3
"""Read-only Capafy company reconcile with an atomic, truthful receipt."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any


API = "https://api.capafy.ai"
SOURCE_NAMES = (
    "account", "inventory", "sales", "payout", "refunds",
    "seller_sales", "seller_ranking", "statements",
)
CAPAFY_ACTIVE_SUBMISSION_CAP = 5


def _money(value: Any) -> str | None:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return None
    return f"{amount:.2f}" if amount.is_finite() else None


def _ok(payload: Any) -> bool:
    return isinstance(payload, dict) and "_error" not in payload and payload.get("code", 0) == 0


def _data(payload: Any) -> Any:
    return payload.get("data") if isinstance(payload, dict) and "data" in payload else payload


def _sales_money(payload: dict) -> tuple[str | None, str | None, int | None]:
    if not _ok(payload):
        return None, None, None
    data = _data(payload)
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return None, None, None
    gross = Decimal("0")
    refunds = Decimal("0")
    orders = 0
    try:
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError
            gross += Decimal(str(row.get("revenue", 0) or 0))
            refunds += Decimal(str(row.get("refundAmount", 0) or 0))
            raw_orders = row.get("orders", 0) or 0
            if isinstance(raw_orders, bool):
                raise ValueError
            orders += int(raw_orders)
    except (InvalidOperation, TypeError, ValueError):
        return None, None, None
    return _money(gross), _money(refunds), orders


def _payout_money(payload: dict) -> tuple[str | None, str | None]:
    if not _ok(payload):
        return None, None
    data = _data(payload)
    if not isinstance(data, dict):
        return None, None
    return _money(data.get("balancePayout")), _money(data.get("totalPayout"))


def _refund_count(payload: dict) -> int | None:
    if not _ok(payload):
        return None
    data = _data(payload)
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("list", "refunds", "records"):
            if isinstance(data.get(key), list):
                return len(data[key])
    return None


def _seller_money(sales_payload: dict, ranking_payload: dict, statements_payload: dict) -> dict:
    empty = {"gross": None, "orders": None, "refunds": None, "one_time": None,
             "mrr": None, "ending_balance": None, "payable": None, "winner": None}
    if not all(_ok(value) for value in (sales_payload, ranking_payload, statements_payload)):
        return empty
    sales = _data(sales_payload)
    ranking = _data(ranking_payload)
    statements = _data(statements_payload)
    if not isinstance(sales, dict) or not isinstance(ranking, dict) or not isinstance(statements, dict):
        return empty
    rows = sales.get("data")
    agents = ranking.get("agents")
    statement_rows = statements.get("list")
    if not isinstance(rows, list) or not isinstance(agents, list) or not isinstance(statement_rows, list):
        return empty
    try:
        gross = Decimal(str(sales.get("totalRevenue", 0) or 0))
        orders = sum(
            int(row.get("orders", 0) or 0)
            for row in rows
            if Decimal(str(row.get("revenue", 0) or 0)) > 0
        )
        refunds = sum(Decimal(str(row.get("refundAmount", 0) or 0)) for row in rows)
        subscription_sales = sum(
            Decimal(str(sku.get("salesAmount", 0) or 0))
            for agent in agents for sku in (agent.get("skus") or [])
            if str(sku.get("skuType") or "").startswith("subscription_")
        )
        winner_row = max(agents, key=lambda agent: Decimal(str(agent.get("totalSalesAmount", 0) or 0)), default={})
        winner_sales = Decimal(str(winner_row.get("totalSalesAmount", 0) or 0))
        winner_sku = max(
            winner_row.get("skus") or [],
            key=lambda sku: Decimal(str(sku.get("salesAmount", 0) or 0)),
            default={},
        )
        latest = max(statement_rows, key=lambda row: str(row.get("settlementMonth") or ""), default={})
    except (InvalidOperation, TypeError, ValueError):
        return empty
    # Zero lifetime subscription sales proves current MRR is zero. Once any
    # subscription sale exists, active/canceled status is required; do not infer it.
    mrr = "0.00" if subscription_sales == 0 else None
    sku_type = str(winner_sku.get("skuType") or "")
    winner = None
    if winner_sales > 0 and winner_row.get("agentId") and winner_row.get("agentTitle"):
        winner = {
            "agent_id": str(winner_row["agentId"]),
            "name": str(winner_row["agentTitle"]),
            "sales_usd": _money(winner_sales),
            "sku_type": sku_type,
            "revenue_kind": "subscription" if sku_type.startswith("subscription_") else "one_time",
            "source": "official_publisher_console",
        }
    return {
        "gross": _money(gross), "orders": orders, "refunds": _money(refunds),
        "one_time": _money(gross - subscription_sales), "mrr": mrr,
        "ending_balance": _money(latest.get("endingSettlementBalance")) if latest else None,
        "payable": _money(latest.get("payableAmount")) if latest else None,
        "winner": winner,
    }


def _inventory(payload: dict) -> dict:
    result = {"status": "unknown_unrecognized_shape", "observed_agents": None, "occupied": None, "free": None}
    if not _ok(payload):
        result["status"] = "unknown_source_error"
        return result
    data = _data(payload)
    rows = None
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        for key in ("list", "agents"):
            if isinstance(data.get(key), list):
                rows = data[key]
                break
    if rows is None:
        return result

    counts = {"listed": 0, "occupied": 0, "retry": 0, "blocked": 0}
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("agentId") or "").strip():
            result.update(status="unknown_invalid_agent", observed_agents=len(rows))
            return result
        status = row.get("agentStatus")
        if status in {"online", "approved"}:
            counts["listed"] += 1
        elif status in {"draft", "under_review"}:
            counts["occupied"] += 1
        elif status == "review_rejected":
            counts["retry"] += 1
        elif status == "banned":
            counts["blocked"] += 1
        else:
            result.update(status="unknown_unrecognized_status", observed_agents=len(rows))
            return result
    result.update(
        status="normalized",
        observed_agents=len(rows),
        listed=counts["listed"],
        occupied=counts["occupied"],
        free=max(0, CAPAFY_ACTIVE_SUBMISSION_CAP - counts["occupied"]),
        retry=counts["retry"],
        blocked=counts["blocked"],
    )
    return result


def build_receipt(payloads: dict[str, dict], observed_at: str) -> dict:
    sources = {
        name: {
            "freshness": "fresh" if _ok(payloads.get(name)) else "unknown",
            "error": payloads.get(name, {}).get("_error") if isinstance(payloads.get(name), dict) else "missing",
        }
        for name in SOURCE_NAMES
    }
    legacy_gross, legacy_refunds, legacy_orders = _sales_money(payloads.get("sales", {}))
    seller = _seller_money(
        payloads.get("seller_sales", {}), payloads.get("seller_ranking", {}), payloads.get("statements", {})
    )
    gross, refunds, orders = seller["gross"], seller["refunds"], seller["orders"]
    pending, realized = _payout_money(payloads.get("payout", {}))
    inventory = _inventory(payloads.get("inventory", {}))
    required_fresh = (
        all(sources[name]["freshness"] == "fresh" for name in SOURCE_NAMES)
        and inventory["status"] == "normalized"
    )
    return {
        "schema_version": 1,
        "kind": "capafy_hourly_reconcile",
        "observed_at": observed_at,
        "verdict": "success" if required_fresh else "degraded",
        "account": {"authenticated": True if _ok(payloads.get("account")) else None},
        "inventory": inventory,
        "orders": orders,
        "seller_winner": seller["winner"],
        "legacy_agent_api": {"orders": legacy_orders, "gross_usd": legacy_gross, "refunds_usd": legacy_refunds},
        "refunds": {"tickets": _refund_count(payloads.get("refunds", {}))},
        "money": {
            "gross_usd": gross,
            "one_time_revenue_usd": seller["one_time"],
            "pending_usd": pending,
            "realized_usd": realized,
            "refunds_usd": refunds,
            "settled_mrr_usd": seller["mrr"],
            "net_mrr_usd": seller["mrr"],
            "statement_ending_balance_usd": seller["ending_balance"],
            "statement_payable_usd": seller["payable"],
        },
        "money_status": {
            "gross_usd": "fresh" if gross is not None else "unknown",
            "one_time_revenue_usd": "fresh_official_seller_console" if seller["one_time"] is not None else "unknown",
            "pending_usd": "fresh" if pending is not None else "unknown",
            "realized_usd": "fresh" if realized is not None else "unknown",
            "refunds_usd": "fresh" if refunds is not None else "unknown",
            "settled_mrr_usd": "fresh_zero_lifetime_subscription_sales" if seller["mrr"] == "0.00" else "unknown_active_subscription_status",
            "net_mrr_usd": "fresh_zero_lifetime_subscription_sales" if seller["mrr"] == "0.00" else "unknown_active_subscription_status",
        },
        "sources": sources,
    }


def _token(repo_root: Path) -> str:
    for key in ("CAPAFY_ACCESS_TOKEN", "CAPAFY_TOKEN"):
        if os.environ.get(key):
            return str(os.environ[key])
    candidates = (
        Path.home() / ".local/state/mr-bot/credentials/capafy-publisher.json",
        repo_root / "skills/capafy-autopublish/vendor/capafy-publisher/config.json",
    )
    for path in candidates:
        try:
            token = json.loads(path.read_text()).get("access_token")
        except (OSError, json.JSONDecodeError, AttributeError):
            continue
        if token:
            return str(token)
    return ""


def _web_token() -> str:
    try:
        credentials = json.loads((Path.home() / ".local/share/anicca/credentials.json").read_text())["credentials"]
        matches = [row for row in credentials if row.get("service") == "capafy-publisher"]
        return str(matches[0].get("web_token") or "") if len(matches) == 1 else ""
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return ""


def _get(path: str, token: str) -> dict:
    request = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            value = json.loads(response.read().decode("utf-8"))
            return value if isinstance(value, dict) else {"_error": "response_not_object"}
    except (OSError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}


def _live_payloads(repo_root: Path, observed: dt.datetime) -> dict[str, dict]:
    token = _token(repo_root)
    web_token = _web_token()
    if not token:
        return {name: {"_error": "access_token_unavailable"} for name in SOURCE_NAMES}
    start = (observed.date() - dt.timedelta(days=89)).isoformat()
    end = observed.date().isoformat()
    paths = {
        "account": "/agent/account",
        "inventory": "/agent/agents",
        "sales": f"/agent/sales/trend?startDate={start}&endDate={end}",
        "payout": "/agent/developer/payout-info",
        "refunds": "/agent/refund/developer/list",
    }
    payloads = {name: _get(path, token) for name, path in paths.items()}
    if not web_token:
        payloads.update({name: {"_error": "web_token_unavailable"} for name in ("seller_sales", "seller_ranking", "statements")})
        return payloads
    payloads.update({
        "seller_sales": _get("/app/sales/trend?sinceLaunch=true&granularity=daily", web_token),
        "seller_ranking": _get("/app/sales/ranking?sinceLaunch=true&granularity=daily&languageCode=en", web_token),
        "statements": _get("/app/developer/settlement-statement/list?page=1&size=20", web_token),
    })
    return payloads


def _atomic_write(path: Path, receipt: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-dir", type=Path)
    parser.add_argument("--output", type=Path, default=Path.home() / ".local/state/mr-bot/state/capafy-hourly-reconcile.json")
    parser.add_argument("--observed-at")
    args = parser.parse_args(argv)
    observed = dt.datetime.now(dt.timezone.utc)
    if args.observed_at:
        observed = dt.datetime.fromisoformat(args.observed_at.replace("Z", "+00:00"))
    observed_at = observed.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    repo_root = Path(__file__).resolve().parents[4]
    if args.fixture_dir:
        payloads = {name: json.loads((args.fixture_dir / f"{name}.json").read_text()) for name in SOURCE_NAMES}
    else:
        payloads = _live_payloads(repo_root, observed)
    receipt = build_receipt(payloads, observed_at)
    _atomic_write(args.output, receipt)
    print(json.dumps(receipt, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    return 0 if receipt["verdict"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
