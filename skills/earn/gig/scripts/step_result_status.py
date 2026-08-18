#!/usr/bin/env python3
"""Read the semantic status an agent step reported, from its runner evidence.

C3b. ``agent_runner.py`` exits 0 for any *schema-valid* result -- that is its
contract, and widening ``gig_step_result.schema.json`` to admit ``blocked``/
``error`` does not change it. So the caller has to look. Measured 2026-08-01,
pass 1785549600-94110: the PAID_WORK builder wrote
``{"status":"ok","summary":"blocked: 買い手フィードバック本文が…存在せず…"}`` because
``status`` was pinned to the const ``ok``; the runner exited 0 and the pass fell
through to validate-promote, which reported 13 errors about an artifact that was
never attempted.

Deliberately total: this module never raises and the CLI never exits nonzero.
It is called from ``gig_pass.sh``, where an escaping exception would be recorded
against a lane that is otherwise healthy. Absence of evidence is reported as
``unknown``, never as a status -- the caller decides what to do with that, and
today it keeps the pre-C3b behaviour so no existing lane or fixture changes.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


UNKNOWN = "unknown"
# The status is model-authored text that flows into the pass log and into a
# rollback reason. It is a closed vocabulary, so clamp it to that shape: a
# newline inside `status` would otherwise forge lines in the pass log and in the
# failure ledger. Anything off-shape becomes `invalid_status` -- which is not
# `ok`, so its step still fails. Fail-closed and unforgeable.
INVALID = "invalid_status"
_STATUS_SHAPE = re.compile(r"[a-z][a-z_]{0,31}")


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def status_from_result(result_path: Path | str) -> str:
    """Return the ``status`` string in a runner result file, or ``unknown``."""
    result = _load_json(Path(result_path))
    if not isinstance(result, dict):
        return UNKNOWN
    status = result.get("status")
    if not isinstance(status, str) or not status.strip():
        return UNKNOWN
    status = status.strip()
    return status if _STATUS_SHAPE.fullmatch(status) else INVALID


def status_from_evidence(evidence_dir: Path | str) -> str:
    """Return the status of the result the runner selected in ``evidence_dir``."""
    summary = _load_json(Path(evidence_dir) / "summary.json")
    if not isinstance(summary, dict):
        return UNKNOWN
    result_path = summary.get("result_path")
    if not isinstance(result_path, str) or not result_path:
        return UNKNOWN
    return status_from_result(result_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True)
    args = parser.parse_args()
    try:
        print(status_from_evidence(args.evidence_dir))
    except Exception:  # noqa: BLE001 - a reader must never fail its caller's lane
        print(UNKNOWN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
