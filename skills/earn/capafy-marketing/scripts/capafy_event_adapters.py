#!/usr/bin/env python3
"""Translate verified Capafy outcome artifacts into canonical revenue events."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from capafy_event_store import append_event


ZERO_MONEY = {
    "currency": "USD",
    "gross_delta": "0.00",
    "pending_delta": "0.00",
    "realized_delta": "0.00",
    "mrr_delta": "0.00",
    "cost_delta": "0.00",
    "contribution_delta": "0.00",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _source(outcome: dict, producer: str, source_id: str) -> dict:
    source_material = {key: value for key, value in outcome.items() if key != "published_at"}
    return {
        "producer": producer,
        "source_id": source_id,
        "source_digest": "sha256:" + hashlib.sha256(_canonical(source_material)).hexdigest(),
    }


def _https(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _reel_shortcode(url: str) -> str | None:
    if not _https(url):
        return None
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2 or parts[0] != "reel":
        return None
    return parts[1] or None


def _event(
    *,
    event_id: str,
    event_type: str,
    occurred_at: str,
    loop: str,
    entity_type: str,
    entity_id: str,
    correlation_id: str | None,
    summary: str,
    before: str | None,
    after: str | None,
    urls: list[str],
    labels: list[str],
    source: dict,
    next_owner: str,
) -> dict:
    return {
        "schema_version": 1,
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "loop": loop,
        "entity": {"type": entity_type, "id": entity_id},
        "correlation_id": correlation_id,
        "summary": summary,
        "status": {"before": before, "after": after},
        "money": dict(ZERO_MONEY),
        "metrics": {},
        "public_evidence": {"urls": urls, "labels": labels},
        "technical_evidence_ref": event_id,
        "source": source,
        "next": {"owner": next_owner, "retry_at": None},
    }


def events_from_outcome(
    outcome: dict,
    occurred_at: str,
    correlation_id: str | None = None,
) -> list[dict]:
    """Return canonical events only for an already-verified success envelope."""

    kind = outcome.get("kind")
    if kind not in {"builder_submitted", "marketing_published", "account_created"}:
        return []
    from capafy_outcome import validate_outcome

    if validate_outcome(outcome):
        return []

    if kind == "builder_submitted":
        agent_id = str(outcome["agent_id"])
        status = int(outcome["remote_status"])
        event_id = f"capafy:listing.submitted:{agent_id}:status-{status}"
        return [
            _event(
                event_id=event_id,
                event_type="listing.submitted",
                occurred_at=occurred_at,
                loop="builder",
                entity_type="listing",
                entity_id=agent_id,
                correlation_id=correlation_id,
                summary=f"Builder verified listing {agent_id} in remote status {status}.",
                before=None,
                after="online" if status == 4 else "under_review",
                urls=[outcome["listing_url"]],
                labels=["remote skill and config confirmation verified"],
                source=_source(
                    outcome, "capafy-builder-handoff", f"builder-submitted:{agent_id}:status-{status}"
                ),
                next_owner="builder",
            )
        ]

    if kind == "marketing_published":
        persisted_time = outcome.get("published_at")
        if isinstance(persisted_time, str):
            try:
                parsed = datetime.fromisoformat(persisted_time.replace("Z", "+00:00"))
                if parsed.utcoffset() is not None:
                    occurred_at = parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            except ValueError:
                pass
        reel_url = outcome["reel_url"]
        shortcode = _reel_shortcode(reel_url)
        handle = outcome.get("handle")
        urls = [reel_url, outcome["listing_url"], outcome["campaign_url"]]
        if not shortcode or not isinstance(handle, str) or not handle or not all(
            _https(url) for url in urls
        ):
            return []
        source = _source(outcome, "capafy-marketing-handoff", f"marketing-published:{shortcode}")
        content_id = f"capafy:content.published:instagram:{shortcode}"
        proof_id = f"capafy:account.post_verified:{handle}:{shortcode}"
        ready_id = f"capafy:account.commercial_ready:{handle}:{shortcode}"
        return [
            _event(
                event_id=content_id,
                event_type="content.published",
                occurred_at=occurred_at,
                loop="marketer",
                entity_type="content",
                entity_id=f"instagram:{shortcode}",
                correlation_id=correlation_id,
                summary="Published and owner-verified an Instagram Reel.",
                before="publish_probe_ready",
                after="reach_observing",
                urls=urls,
                labels=["post-write owner session verified"],
                source=source,
                next_owner="marketer",
            ),
            _event(
                event_id=proof_id,
                event_type="account.post_verified",
                occurred_at=occurred_at,
                loop="marketer",
                entity_type="account",
                entity_id=handle,
                correlation_id=correlation_id,
                summary=f"Re-verified @{handle} as owner after Reel publication.",
                before="session_ready",
                after="post_verified",
                urls=[reel_url],
                labels=["post-write owner session verified"],
                source=source,
                next_owner="marketer",
            ),
            _event(
                event_id=ready_id,
                event_type="account.commercial_ready",
                occurred_at=occurred_at,
                loop="marketer",
                entity_type="account",
                entity_id=handle,
                correlation_id=correlation_id,
                summary=f"Granted immediate commercial posting capability to @{handle} after owner-verified publication.",
                before="post_verified",
                after="commercial_ready",
                urls=[reel_url],
                labels=["no elapsed warmup or reach gate"],
                source=source,
                next_owner="marketer",
            ),
        ]

    handle = str(outcome["handle"])
    source = _source(outcome, "capafy-marketing-handoff", f"account-created:{handle}")
    definitions = (
        ("created", "account.created", None, "created", "Created a new Instagram account."),
        (
            "session_ready",
            "account.session_ready",
            "created",
            "session_ready",
            "Verified the browser-owned Instagram session.",
        ),
        (
            "publish_probe_ready",
            "account.publish_probe_ready",
            "session_ready",
            "publish_probe_ready",
            "Verified immediate publish-probe capability.",
        ),
    )
    return [
        _event(
            event_id=f"capafy:account.{suffix}:{handle}",
            event_type=event_type,
            occurred_at=occurred_at,
            loop="marketer",
            entity_type="account",
            entity_id=handle,
            correlation_id=correlation_id,
            summary=f"{summary} @{handle}",
            before=before,
            after=after,
            urls=[],
            labels=["independent owner-session verification passed"],
            source=source,
            next_owner="marketer",
        )
        for suffix, event_type, before, after, summary in definitions
    ]


def events_from_lifecycle(before: dict, after: dict, occurred_at: str) -> list[dict]:
    """Translate newly verified deterministic account capabilities."""

    handle = after.get("handle")
    if not isinstance(handle, str) or not handle:
        return []
    envelope = {"before": before, "after": after}
    source = _source(envelope, "capafy-ig-lifecycle", f"lifecycle:{handle}")
    events: list[dict] = []
    if not before.get("session_established") and after.get("session_established") is True:
        events.append(
            _event(
                event_id=f"capafy:account.session_ready:{handle}",
                event_type="account.session_ready",
                occurred_at=occurred_at,
                loop="marketer",
                entity_type="account",
                entity_id=handle,
                correlation_id=None,
                summary=f"Verified the browser-owned Instagram session for @{handle}.",
                before=str(before.get("status") or "created"),
                after="session_ready",
                urls=[],
                labels=["independent owner-session verification passed"],
                source=source,
                next_owner="marketer",
            )
        )
    if before.get("capability") != "publish_probe" and after.get("capability") == "publish_probe":
        events.append(
            _event(
                event_id=f"capafy:account.publish_probe_ready:{handle}",
                event_type="account.publish_probe_ready",
                occurred_at=occurred_at,
                loop="marketer",
                entity_type="account",
                entity_id=handle,
                correlation_id=None,
                summary=f"Verified immediate publish-probe capability for @{handle}.",
                before="session_ready",
                after="publish_probe_ready",
                urls=[],
                labels=["no elapsed-day gate applies"],
                source=source,
                next_owner="marketer",
            )
        )
    return events


def _utc_timestamp(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _phase_occurrence(record: dict, phase: str) -> int:
    try:
        return int((record.get("phase_occurrences") or {}).get(phase) or 0)
    except (AttributeError, TypeError, ValueError):
        return 0


def _incident_event_id(record: dict, occurred_phase: str) -> str:
    incident_id = str(record["incident_id"])
    event_id = f"capafy:incident.{occurred_phase}:{incident_id}"
    occurrence = _phase_occurrence(record, occurred_phase)
    if occurred_phase == "unresolved":
        retry_at = _utc_timestamp(record.get("next_retry_at"))
        if retry_at is not None:
            compact_retry = retry_at.replace("-", "").replace(":", "")
            event_id = f"{event_id}:retry-{compact_retry}"
            if occurrence > 1:
                event_id = f"{event_id}:occurrence-{occurrence}"
            return event_id
        return event_id
    try:
        attempts = int(record.get("attempts") or 0)
    except (TypeError, ValueError):
        attempts = 0
    if occurred_phase in {"repair_started", "repaired", "verified"} and attempts > 0:
        event_id = f"{event_id}:attempt-{attempts}"
        if occurrence > attempts + 1:
            event_id = f"{event_id}:occurrence-{occurrence}"
        return event_id
    if occurrence > 1:
        return f"{event_id}:occurrence-{occurrence}"
    return event_id


def event_from_incident(record: dict) -> dict:
    """Translate one persisted incident phase into a retry-stable public event."""

    incident_id = record.get("incident_id")
    owner = record.get("owner")
    phase = record.get("phase")
    if not isinstance(incident_id, str) or not incident_id:
        raise ValueError("incident_id is required")
    if not isinstance(owner, str) or not owner:
        raise ValueError("incident owner is required")
    if phase not in {"detected", "repair_started", "repaired", "verified", "unresolved"}:
        raise ValueError(f"unsupported incident phase: {phase!r}")
    if phase == "verified" and not isinstance(record.get("verification"), dict):
        raise ValueError("incident.verified requires concrete verification")
    phase_times = record.get("phase_timestamps") or {}
    occurred_at = _utc_timestamp(phase_times.get(phase))
    if occurred_at is None:
        raise ValueError(f"incident phase timestamp is required: {phase}")

    phase_source = {
        "incident_id": incident_id,
        "owner": owner,
        "phase": phase,
        "occurred_at": occurred_at,
        "summary": record.get("summary"),
        "repair_summary": record.get("repair_summary"),
        "verification": record.get("verification"),
        "outcome": record.get("outcome"),
        "next_retry_at": (
            _utc_timestamp(record.get("next_retry_at"))
            if phase == "unresolved"
            else record.get("next_retry_at")
        ),
    }
    occurrence = _phase_occurrence(record, phase)
    if occurrence > 1:
        phase_source["occurrence"] = occurrence
    urls: list[str] = []
    outcome = record.get("outcome")
    if isinstance(outcome, dict):
        for field in ("reel_url", "listing_url", "campaign_url"):
            value = outcome.get(field)
            if _https(value) and value not in urls:
                urls.append(value)
    before_by_phase = {
        "detected": None,
        "repair_started": "detected",
        "repaired": "repair_started",
        "verified": "repaired",
        "unresolved": "repair_started",
    }
    summary = str(record.get("summary") or "Capafy incident")
    if phase in {"repaired", "verified"} and record.get("repair_summary"):
        summary = str(record["repair_summary"])
    retry_at = _utc_timestamp(record.get("next_retry_at")) if phase == "unresolved" else None
    event_id = _incident_event_id(record, phase)
    event = _event(
        event_id=event_id,
        event_type=f"incident.{phase}",
        occurred_at=occurred_at,
        loop=owner,
        entity_type="incident",
        entity_id=incident_id,
        correlation_id=incident_id,
        summary=summary,
        before=before_by_phase[phase],
        after=phase,
        urls=urls,
        labels=[f"incident phase: {phase.replace('_', '-')}"],
        source=_source(
            phase_source,
            "capafy-outcome",
            f"incident:{incident_id}:{phase}",
        ),
        next_owner=owner,
    )
    event["next"]["retry_at"] = retry_at
    return event


def _source_occurred_at(source: Path) -> str:
    return datetime.fromtimestamp(source.stat().st_mtime, timezone.utc).isoformat(
        timespec="seconds"
    ).replace("+00:00", "Z")


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    outcome_parser = commands.add_parser("append-outcome")
    outcome_parser.add_argument("--source", type=Path, required=True)
    outcome_parser.add_argument("--ledger", type=Path, required=True)
    outcome_parser.add_argument("--evidence-dir", type=Path, required=True)
    outcome_parser.add_argument("--technical-evidence-dir")
    outcome_parser.add_argument("--correlation-id")
    outcome_parser.add_argument("--outcome-stdin", action="store_true")
    lifecycle_parser = commands.add_parser("append-lifecycle")
    lifecycle_parser.add_argument("--before", type=Path, required=True)
    lifecycle_parser.add_argument("--after", type=Path, required=True)
    lifecycle_parser.add_argument("--ledger", type=Path, required=True)
    lifecycle_parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()

    try:
        if args.command == "append-outcome":
            outcome = (
                json.load(sys.stdin)
                if args.outcome_stdin
                else json.loads(args.source.read_text())
            )
            events = events_from_outcome(
                outcome,
                _source_occurred_at(args.source),
                args.correlation_id,
            )
            if outcome.get("kind") in {
                "builder_submitted",
                "marketing_published",
                "account_created",
            } and not events:
                raise ValueError(f"verified {outcome.get('kind')} outcome emitted no event")
            evidence = {
                "source": outcome,
                "evidence_directory": args.technical_evidence_dir,
            }
        else:
            before = json.loads(args.before.read_text())
            after = json.loads(args.after.read_text())
            events = events_from_lifecycle(before, after, _source_occurred_at(args.after))
            evidence = {"before": before, "after": after}
        results = [
            append_event(args.ledger, event, evidence, args.evidence_dir)
            for event in events
        ]
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    output = {
        "observed": len(results),
        "appended": sum(result.appended for result in results),
        "duplicates": sum(not result.appended for result in results),
        "event_ids": [result.event_id for result in results],
    }
    print(json.dumps(output, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
