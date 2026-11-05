#!/usr/bin/env python3
"""Export Capafy account analytics for Open without exposing credentials."""
from __future__ import annotations

import argparse
import datetime as dt
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
        snapshot["windows"][label] = {
            "start_utc": traffic["window"]["start_utc"], "end_utc": traffic["window"]["end_utc"],
            "views": totals["views"], "paid_orders": totals["paid_orders"],
            "trial_orders": totals["trial_orders"], "sales_usd": totals["sales_usd"],
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
