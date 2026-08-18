#!/usr/bin/env python3
"""Validate one marketplace envelope and feed the shared KPI projector."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from kpi_contract import validate_kpi_record
from kpi_funnel_projector import project_records


class AdapterBoundaryError(ValueError):
    """A platform adapter did not satisfy the shared ingestion boundary."""


def _time(value: object) -> str:
    if not isinstance(value, str):
        raise AdapterBoundaryError("official readback timestamp is unavailable")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AdapterBoundaryError("official readback timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise AdapterBoundaryError("official readback timestamp requires timezone")
    return parsed.isoformat(timespec="seconds")


def project_adapter_envelope(envelope: Mapping[str, Any], *, as_of: str) -> dict[str, Any]:
    """Return a platform-scoped projection without platform-specific business logic."""
    if set(envelope) != {"schema_version", "platform", "official_readback", "records"}:
        raise AdapterBoundaryError("adapter envelope fields are invalid")
    platform = envelope.get("platform")
    if envelope.get("schema_version") != 1 or not isinstance(platform, str) or not platform:
        raise AdapterBoundaryError("adapter identity is invalid")
    readback = envelope.get("official_readback")
    if not isinstance(readback, Mapping) or set(readback) != {
        "observed_at", "evidence_ref", "content_sha256"
    }:
        raise AdapterBoundaryError("official readback is invalid")
    _time(readback.get("observed_at"))
    if not isinstance(readback.get("evidence_ref"), str) or not readback["evidence_ref"]:
        raise AdapterBoundaryError("official readback evidence is unavailable")
    digest = readback.get("content_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(
        char not in "0123456789abcdef" for char in digest
    ):
        raise AdapterBoundaryError("official readback hash is invalid")
    records = envelope.get("records")
    if not isinstance(records, list):
        raise AdapterBoundaryError("adapter records are invalid")
    for record in records:
        if not isinstance(record, Mapping) or record.get("platform") != platform:
            raise AdapterBoundaryError("record platform does not match adapter")
        validate_kpi_record(record)
    return {
        "schema_version": 1,
        "platform": platform,
        "official_readback": dict(readback),
        "projection": project_records(records, as_of=as_of),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    json.dump(project_adapter_envelope(payload, as_of=args.as_of), sys.stdout,
              ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
