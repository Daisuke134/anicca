#!/usr/bin/env python3
"""Private changed-head ledger for Upwork rooms, offers and contracts."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


KINDS = {"message_room", "offer", "contract"}


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _head_sha(kind: str, text: str) -> str:
    identity_text = text
    if kind == "message_room":
        identity_text = _norm(re.sub(
            r"\b\d{1,2}:\d{2}\s+[AP]M\s+local time\b", "", text, flags=re.IGNORECASE,
        ))
    return hashlib.sha256(identity_text.encode()).hexdigest()


def _money_minor(value: str) -> int:
    return int(round(float(value.replace(",", "")) * 100))


def parse_terms(text: str) -> dict[str, Any]:
    normalized = _norm(text)
    amounts = [_money_minor(item) for item in re.findall(r"\$([\d,]+(?:\.\d{1,2})?)", normalized)]
    fee = re.search(r"(?:service fee|freelancer fee)\s*:?[ ]*(\d+(?:\.\d+)?)%", normalized, re.I)
    deadline = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", normalized)
    milestones = [_money_minor(item) for item in re.findall(
        r"milestone[^$]{0,120}\$([\d,]+(?:\.\d{1,2})?)", normalized, re.I,
    )]
    state = "unknown"
    for label, pattern in (
        ("active", r"\bactive contract\b|\bcontract room\b|\bworkroom\b"),
        ("offered", r"\baccept offer\b"),
        ("declined", r"\boffer declined\b"),
        ("ended", r"\bcontract ended\b|\bclosed contract\b"),
    ):
        if re.search(pattern, normalized, re.I):
            state = label
            break
    return {
        "amounts_usd_minor": amounts,
        "fee_bps": int(float(fee.group(1)) * 100) if fee else None,
        "milestones_usd_minor": milestones,
        "deadline": deadline.group(1) if deadline else None,
        "contract_state": state,
    }


def normalize_observation(
    *, kind: str, resource_id: str, resource_url: str, rendered_text: str,
    source_evidence_sha256: str, observed_at: str,
    rendered_links: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if kind not in KINDS or not isinstance(resource_id, str) or not resource_id:
        raise ValueError("upwork_inbox_identity_invalid")
    url = urlsplit(resource_url)
    if (
        url.scheme != "https" or url.netloc != "www.upwork.com" or resource_id not in url.path
        or not re.fullmatch(r"[0-9a-f]{64}", source_evidence_sha256)
        or not isinstance(observed_at, str) or not observed_at
    ):
        raise ValueError("upwork_inbox_identity_invalid")
    text = _norm(rendered_text)
    if not text:
        raise ValueError("upwork_inbox_head_invalid")
    if rendered_links is not None and not isinstance(rendered_links, list):
        raise ValueError("upwork_inbox_links_invalid")
    related = {"job_ids": set(), "proposal_ids": set(), "contract_ids": set()}
    for link in rendered_links or []:
        href = str(link.get("href") or "") if isinstance(link, dict) else ""
        parsed = urlsplit(href)
        if parsed.scheme != "https" or parsed.netloc != "www.upwork.com":
            continue
        job = re.search(r"/jobs/[^/?#]*(~[A-Za-z0-9]+)(?:[/?#]|$)", href)
        proposal = re.search(r"/proposals/(?!job(?:/|$))([^/?#]+)", href)
        contract = re.search(r"/workroom/([^/?#]+)", href)
        if job:
            related["job_ids"].add(job.group(1))
        if proposal:
            related["proposal_ids"].add(proposal.group(1))
        if contract:
            related["contract_ids"].add(contract.group(1))
    head_sha = _head_sha(kind, text)
    return {
        "version": 1, "provider": "upwork", "kind": kind,
        "resource_id": resource_id, "resource_url": resource_url,
        "head_sha256": head_sha, "source_evidence_sha256": source_evidence_sha256,
        "observed_at": observed_at, "rendered_text": text,
        "terms": parse_terms(text),
        "related_ids": {key: sorted(value) for key, value in related.items()},
    }


def append_changed_heads(path: Path, observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Append each never-seen exact head once; return a copy-free public projection."""
    if not observations:
        return {"observed": 0, "appended": 0, "heads": []}
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    with path.open("a+", encoding="utf-8") as handle:
        os.chmod(path, 0o600)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        rows: list[dict[str, Any]] = []
        for line in handle:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError("upwork_inbox_ledger_invalid") from exc
            if not isinstance(row, dict) or not row.get("event_id"):
                raise ValueError("upwork_inbox_ledger_invalid")
            rows.append(row)
        seen = {str(row["event_id"]) for row in rows}
        event_revisions = {str(row["event_id"]): int(row.get("revision", 0)) for row in rows}
        for row in rows:
            if row.get("kind") != "message_room" or not row.get("rendered_text"):
                continue
            canonical_event_id = hashlib.sha256(
                f"upwork:inbox:v1:message_room:{row.get('resource_id')}:"
                f"{_head_sha('message_room', _norm(row['rendered_text']))}".encode()
            ).hexdigest()
            seen.add(canonical_event_id)
            event_revisions[canonical_event_id] = int(row.get("revision", 0))
        revisions: dict[tuple[str, str], int] = {}
        for row in rows:
            key = (str(row.get("kind")), str(row.get("resource_id")))
            revisions[key] = max(revisions.get(key, 0), int(row.get("revision", 0)))
        appended: list[dict[str, Any]] = []
        public: list[dict[str, Any]] = []
        for observation in sorted(observations, key=lambda item: (item["kind"], item["resource_id"])):
            key = (observation["kind"], observation["resource_id"])
            event_id = hashlib.sha256(
                f"upwork:inbox:v1:{key[0]}:{key[1]}:{observation['head_sha256']}".encode()
            ).hexdigest()
            revision = revisions.get(key, 0)
            if event_id not in seen:
                revision += 1
                row = {**observation, "event_id": event_id, "revision": revision}
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
                appended.append(row)
                seen.add(event_id)
                event_revisions[event_id] = revision
                revisions[key] = revision
            else:
                revision = event_revisions[event_id]
            public.append({
                "kind": key[0], "resource_id": key[1], "resource_url": observation["resource_url"],
                "head_sha256": observation["head_sha256"], "revision": revision,
                "event_id": event_id, "changed": any(row["event_id"] == event_id for row in appended),
            })
        handle.flush()
        os.fsync(handle.fileno())
        return {"observed": len(observations), "appended": len(appended), "heads": public}
