"""Turn due observation windows into immutable scorable/insufficient receipts."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


def _instant(value: str, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO timestamp")
    try:
        result = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO timestamp") from error
    if result.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return result


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid observation: {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"observation must be an object: {path}")
    return value


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    fd, temporary = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _validate_evidence(
    observation: dict[str, Any],
    *,
    opened: datetime,
    due: datetime,
) -> list[dict[str, Any]]:
    evidence = observation.get("evidence", [])
    if not isinstance(evidence, list):
        raise ValueError("evidence must be an array")
    seen: set[str] = set()
    scorable: list[dict[str, Any]] = []
    for row in evidence:
        if not isinstance(row, dict):
            raise ValueError("evidence rows must be objects")
        if (
            row.get("product_id") != observation.get("product_id")
            or row.get("channel_id") != observation.get("channel_id")
        ):
            raise ValueError("evidence scope mismatch")
        evidence_id = row.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id:
            raise ValueError("evidence_id is required")
        if evidence_id in seen:
            raise ValueError("duplicate evidence_id")
        seen.add(evidence_id)
        observed = _instant(row.get("observed_at"), field="observed_at")
        if (
            row.get("status") == "scorable"
            and opened <= observed <= due
        ):
            scorable.append(row)
    return scorable


def terminalize_due(
    *,
    runtime_root: Path,
    now: str,
) -> dict[str, int]:
    """Terminalize every due open observation; preserve existing receipts."""

    runtime_root = Path(runtime_root)
    current = _instant(now, field="now")
    open_dir = runtime_root / "observations" / "open"
    terminal_dir = runtime_root / "observations" / "terminal"
    summary = {
        "scorable": 0,
        "insufficient": 0,
        "pending": 0,
        "preserved": 0,
    }
    for source in sorted(open_dir.glob("*.json")):
        observation = _read_object(source)
        observation_id = observation.get("observation_id")
        if (
            not isinstance(observation_id, str)
            or observation_id != source.stem
        ):
            raise ValueError("observation identity mismatch")
        destination = terminal_dir / source.name
        if destination.exists():
            summary["preserved"] += 1
            continue
        opened = _instant(observation.get("opened_at"), field="opened_at")
        due = _instant(observation.get("due_at"), field="due_at")
        if due < opened:
            raise ValueError("due_at must not precede opened_at")
        minimum = observation.get("minimum_evidence")
        if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
            raise ValueError("minimum_evidence must be a positive integer")
        scorable = _validate_evidence(
            observation,
            opened=opened,
            due=due,
        )
        if current < due:
            summary["pending"] += 1
            continue

        enough = len(scorable) >= minimum
        status = "scorable" if enough else "insufficient"
        receipt = {
            "observation_id": observation_id,
            "product_id": observation.get("product_id"),
            "channel_id": observation.get("channel_id"),
            "kind": observation.get("kind"),
            "opened_at": observation.get("opened_at"),
            "due_at": observation.get("due_at"),
            "terminal_at": now,
            "status": status,
            "minimum_evidence": minimum,
            "observed_count": len(scorable),
            "observed_value": len(scorable) if enough else None,
            "reward_effect": "eligible" if enough else "no_change",
            "evidence_ids": [row["evidence_id"] for row in scorable],
        }
        _atomic_json(destination, receipt)
        summary[status] += 1
    return summary
