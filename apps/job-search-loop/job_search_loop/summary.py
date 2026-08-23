from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from .ats import detect_provider
from .ledger import Ledger


REQUIRED_ATS_ADAPTERS = ("ashby", "greenhouse", "lever", "workday", "generic")


def build_summary(
    *,
    day: str,
    states: list[str],
    model_route: str,
    applications: list[dict[str, str | None]] | None = None,
) -> dict[str, Any]:
    adapter_counts: dict[str, Counter[str]] = {}
    for application in applications or []:
        adapter = detect_provider(application["canonical_url"])
        adapter_counts.setdefault(adapter, Counter())[
            application.get("submission_state") or application["current_state"]
        ] += 1
    confirmed_adapters = [
        adapter
        for adapter in REQUIRED_ATS_ADAPTERS
        if adapter_counts.get(adapter, Counter()).get("submitted", 0) > 0
    ]
    return {
        "version": 1,
        "day": day,
        "counts": dict(sorted(Counter(states).items())),
        "model_route": model_route,
        "ats_progress": {
            "required_adapters": list(REQUIRED_ATS_ADAPTERS),
            "confirmed_adapters": confirmed_adapters,
            "complete": len(confirmed_adapters) == len(REQUIRED_ATS_ADAPTERS),
            "adapters": {
                adapter: dict(sorted(counts.items()))
                for adapter, counts in sorted(adapter_counts.items())
            },
        },
    }


def build_summary_v2(
    *,
    day: str,
    applications: list[dict[str, Any]],
    event_high_water: int,
) -> dict[str, Any]:
    counts = Counter(str(row["current_state"]) for row in applications)
    owners = Counter(str(row["owner"]) for row in applications)
    adapter_counts: dict[str, Counter[str]] = {}
    confirmed_adapters: list[str] = []
    for application in applications:
        adapter = detect_provider(str(application["canonical_url"]))
        state = str(application["current_state"])
        adapter_counts.setdefault(adapter, Counter())[state] += 1
        if application["ever_submitted"]:
            adapter_counts[adapter]["ever_submitted"] += 1
    for adapter in REQUIRED_ATS_ADAPTERS:
        if adapter_counts.get(adapter, Counter()).get("ever_submitted", 0) > 0:
            confirmed_adapters.append(adapter)
    application_sets = {
        "attempted": {
            str(row["application_id"])
            for row in applications
            if row["submission_attempted"]
        }
    }
    for stage in (
        "confirmed_application",
        "recruiter_response",
        "interview",
        "final_round",
        "offer",
        "accepted",
    ):
        application_sets[stage] = {
            str(row["application_id"])
            for row in applications
            if stage in row["positive_funnel_stages"]
        }
    metric_cohorts = {
        "confirmed_application_rate": ("confirmed_application", "attempted"),
        "recruiter_reply_rate": ("recruiter_response", "confirmed_application"),
        "interview_rate": ("interview", "confirmed_application"),
        "final_round_rate": ("final_round", "interview"),
        "offer_rate": ("offer", "confirmed_application"),
        "acceptance_rate": ("accepted", "offer"),
    }
    funnel: dict[str, dict[str, Any]] = {}
    for metric, (numerator_name, denominator_name) in metric_cohorts.items():
        numerator_set = application_sets[numerator_name]
        denominator_set = application_sets[denominator_name]
        if not numerator_set.issubset(denominator_set):
            raise ValueError(f"{metric} numerator is outside its denominator cohort")
        numerator = len(numerator_set)
        denominator = len(denominator_set)
        funnel[metric] = {
            "numerator": numerator,
            "denominator": denominator,
            "rate": round(numerator / denominator, 4) if denominator else None,
        }
    value: dict[str, Any] = {
        "version": 2,
        "day": day,
        "event_high_water": event_high_water,
        "counts": dict(sorted(counts.items())),
        "owners": dict(sorted(owners.items())),
        "funnel": funnel,
        "ats_progress": {
            "required_adapters": list(REQUIRED_ATS_ADAPTERS),
            "confirmed_adapters": confirmed_adapters,
            "complete": len(confirmed_adapters) == len(REQUIRED_ATS_ADAPTERS),
            "adapters": {
                adapter: dict(sorted(states.items()))
                for adapter, states in sorted(adapter_counts.items())
            },
        },
    }
    value["projection_sha256"] = hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    return value


def write_summary(path: Path, value: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(target.parent, 0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
        os.chmod(target, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compat-output", type=Path)
    parser.add_argument("--day", required=True)
    parser.add_argument("--model-route", required=True)
    parsed = parser.parse_args(argv)

    ledger = Ledger(parsed.ledger)
    try:
        if parsed.compat_output is None:
            applications = ledger.application_summary_rows()
            value = build_summary(
                day=parsed.day,
                states=[row["current_state"] for row in applications],
                model_route=parsed.model_route,
                applications=applications,
            )
        else:
            ledger.connection.execute("BEGIN")
            try:
                applications_v2 = ledger.event_summary_rows()
                event_high_water = int(
                    ledger.connection.execute(
                        "SELECT COALESCE(MAX(rowid),0) FROM events"
                    ).fetchone()[0]
                )
                ledger.connection.execute("COMMIT")
            except Exception:
                ledger.connection.execute("ROLLBACK")
                raise
            value = build_summary_v2(
                day=parsed.day,
                applications=applications_v2,
                event_high_water=event_high_water,
            )
            compatibility_rows = [
                {
                    **row,
                    "submission_state": (
                        "submitted" if row["ever_submitted"] else None
                    ),
                }
                for row in applications_v2
            ]
            compatibility = build_summary(
                day=parsed.day,
                states=[row["current_state"] for row in applications_v2],
                model_route=parsed.model_route,
                applications=compatibility_rows,
            )
    finally:
        ledger.close()
    write_summary(parsed.output, value)
    if parsed.compat_output is not None:
        write_summary(parsed.compat_output, compatibility)
    print(
        json.dumps(
            {
                "output": str(parsed.output.resolve()),
                "counts": value["counts"],
                "ats_progress": value["ats_progress"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
