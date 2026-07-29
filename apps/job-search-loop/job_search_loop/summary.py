from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from .ats import detect_provider
from .ledger import Ledger


REQUIRED_ATS_ADAPTERS = ("ashby", "workday")


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
    parser.add_argument("--day", required=True)
    parser.add_argument("--model-route", required=True)
    parsed = parser.parse_args(argv)

    ledger = Ledger(parsed.ledger)
    try:
        applications = ledger.application_summary_rows()
    finally:
        ledger.close()
    value = build_summary(
        day=parsed.day,
        states=[row["current_state"] for row in applications],
        model_route=parsed.model_route,
        applications=applications,
    )
    write_summary(parsed.output, value)
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
