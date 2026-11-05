#!/usr/bin/env python3
"""Export Capafy account analytics for Open without exposing credentials."""
from __future__ import annotations

import argparse
import datetime as dt
from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess

import capafy_hourly_reconcile as reconcile


def read_token() -> str:
    # Hosted refreshes receive this value from the runner's encrypted secret store.
    # Local runs continue to resolve the credential from the shared 1Password vault.
    hosted = os.environ.get("CAPAFY_WEB_TOKEN")
    if hosted:
        return hosted
    try:
        result = subprocess.run(
            ["op", "item", "get", "capafy-publisher", "--vault", "Agents", "--format", "json"],
            capture_output=True, text=True, check=True, timeout=30,
        )
        fields = json.loads(result.stdout)["fields"]
        source = next(row["value"] for row in fields if row.get("label") == "source_json")
        token = json.loads(source).get("web_token")
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, StopIteration, TypeError):
        raise RuntimeError("Capafy shared vault credential unavailable") from None
    if not isinstance(token, str) or not token:
        raise RuntimeError("Capafy shared vault credential unavailable")
    return token


def build_snapshot(token: str, observed: dt.datetime) -> dict:
    observed = observed.astimezone(dt.timezone.utc)
    observed_at = observed.isoformat(timespec="seconds")
    end = reconcile._epoch_ms(observed.date(), end_of_day=True)
    snapshot = {"observed_at": observed_at, "source": "Capafy developer traffic analytics", "windows": {}}
    for label, days in (("last_7d", 6), ("last_30d", 29)):
        start = reconcile._epoch_ms(observed.date() - dt.timedelta(days=days))
        traffic = reconcile._traffic_window(token, start, end, observed_at=observed_at)
        impressions = reconcile._impressions_window(token, start, end, observed_at)
        if traffic.get("status") != "fresh" or impressions.get("status") != "fresh":
            raise RuntimeError("Capafy source read unavailable")
        totals = traffic["totals"]
        rows = impressions["by_source"]
        safe = [row for row in rows if row.get("source_type") == "internal"
                and row.get("source_name") in {"category", "search", "hot"}]
        if any(type(row.get("exposure_count")) is not int or row["exposure_count"] < 0 for row in safe):
            raise RuntimeError("Capafy impression data malformed")
        start_date = observed.date() - dt.timedelta(days=days)
        trend_body = {
            "startDate": start_date.isoformat(), "endDate": observed.date().isoformat(),
            "granularity": "daily",
        }
        sales_response = reconcile._post("/app/sales/clickhouse/trend", token, trend_body)
        units_response = reconcile._post("/app/unit-sales/clickhouse/trend", token, trend_body)
        sales = reconcile._data(sales_response) if reconcile._ok(sales_response) else None
        units = reconcile._data(units_response) if reconcile._ok(units_response) else None
        expected_dates = {
            (start_date + dt.timedelta(days=offset)).isoformat()
            for offset in range(days + 1)
        }
        if (not isinstance(sales, dict) or sales.get("startDate") != trend_body["startDate"]
                or sales.get("endDate") != trend_body["endDate"] or sales.get("granularity") != "daily"
                or not isinstance(sales.get("data"), list)
                or not isinstance(units, dict) or units.get("startDate") != trend_body["startDate"]
                or units.get("endDate") != trend_body["endDate"] or units.get("granularity") != "daily"
                or not isinstance(units.get("data"), list)):
            raise RuntimeError("Capafy sales or unit trend unavailable")
        sales_by_date = {row.get("date"): row for row in sales["data"] if isinstance(row, dict)}
        units_by_date = {row.get("date"): row for row in units["data"] if isinstance(row, dict)}
        if (len(sales_by_date) != len(sales["data"]) or len(units_by_date) != len(units["data"])
                or set(sales_by_date) != expected_dates or set(units_by_date) != expected_dates):
            raise RuntimeError("Capafy sales or unit trend coverage incomplete")
        daily = []
        refund_total = Decimal("0")
        order_total = 0
        unit_total = 0
        trial_total = 0
        for date in sorted(expected_dates):
            sale, unit = sales_by_date[date], units_by_date[date]
            revenue = reconcile._money(sale.get("revenue"))
            refunds = reconcile._money(sale.get("refundAmount"))
            orders = sale.get("orders")
            refund_count = sale.get("refundCount")
            unit_count = unit.get("salesVolume")
            trial_count = unit.get("freeTrialCount")
            invalid = [
                name for name, valid in (
                    ("revenue", revenue is not None), ("refunds", refunds is not None),
                    ("orders", type(orders) is int),
                    ("refund_count", type(refund_count) is int and refund_count >= 0),
                    ("units", type(unit_count) is int),
                    ("trial_units", type(trial_count) is int and trial_count >= 0),
                ) if not valid
            ]
            if invalid:
                raise RuntimeError(f"Capafy daily metrics malformed: {date} {','.join(invalid)}")
            daily.append({
                "date": date, "revenue_usd": revenue, "orders": orders,
                "refunds_usd": refunds, "refund_count": refund_count,
                "units": unit_count, "trial_units": trial_count,
            })
            refund_total += Decimal(refunds)
            order_total += orders
            unit_total += unit_count
            trial_total += trial_count
        gross = reconcile._money(sales.get("totalRevenue"))
        if (gross is None or type(units.get("totalSalesVolume")) is not int
                or type(units.get("totalFreeTrialCount")) is not int
                or units["totalFreeTrialCount"] < 0
                or Decimal(gross) != sum((Decimal(row["revenue_usd"]) for row in daily), Decimal("0"))
                or units["totalSalesVolume"] != unit_total
                or units["totalFreeTrialCount"] != trial_total):
            raise RuntimeError("Capafy sales or unit totals malformed")
        snapshot["windows"][label] = {
            "start_utc": traffic["window"]["start_utc"], "end_utc": traffic["window"]["end_utc"],
            "page_views": totals["page_views"], "detail_views": totals["detail_views"],
            "attributed_unique_visitors": totals["unique_visitors"], "views": totals["views"],
            "paid_orders": totals["paid_orders"],
            "trial_orders": totals["trial_orders"], "sales_usd": totals["sales_usd"],
            "platform_orders": order_total, "platform_revenue_usd": gross,
            "refunds_usd": reconcile._money(refund_total),
            "unit_sales": units["totalSalesVolume"], "trial_units": units["totalFreeTrialCount"],
            "daily": daily,
            "impressions": [{"name": row["source_name"], "count": row["exposure_count"]} for row in safe],
            "omitted_impression_sources": len(rows) - len(safe),
        }
    return snapshot


def write_snapshot(output: Path) -> None:
    snapshot = build_snapshot(read_token(), dt.datetime.now(dt.timezone.utc))
    reconcile._atomic_write(output, snapshot)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    write_snapshot(args.output)
    print("Capafy Open snapshot collected")


if __name__ == "__main__":
    main()
