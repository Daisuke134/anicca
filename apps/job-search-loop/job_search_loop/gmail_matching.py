from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .ledger import FenceError, Ledger
from .state import canonical_url


ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
SHA_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join("".join(character if character.isalnum() else " " for character in normalized).split())


def _identifier(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"{name} identifier must be an object")
    raw = value.get("value")
    span = value.get("source_span")
    if not isinstance(raw, str) or not raw.strip() or not isinstance(span, str) or not span.strip():
        raise ValueError(f"{name} identifier requires value and source span")
    if _normalize(raw) not in _normalize(span):
        raise ValueError(f"{name} value is absent from source span")
    return raw.strip()


def match_gmail_event(
    ledger: Ledger, event: dict[str, Any], *, persist: bool = True
) -> dict[str, str]:
    message_id = str(event.get("message_id") or "")
    thread_id = str(event.get("thread_id") or "")
    evidence_sha256 = str(event.get("evidence_sha256") or "")
    if not ID_PATTERN.fullmatch(message_id) or not ID_PATTERN.fullmatch(thread_id):
        raise ValueError("invalid Gmail message/thread ID")
    if not SHA_PATTERN.fullmatch(evidence_sha256):
        raise ValueError("invalid Gmail evidence SHA-256")
    try:
        received = datetime.fromisoformat(str(event.get("received_at") or ""))
    except ValueError as error:
        raise ValueError("received_at must be RFC3339") from error
    if received.tzinfo is None:
        raise ValueError("received_at must include timezone")

    company = _identifier(event.get("company"), "company")
    title = _identifier(event.get("title"), "title")
    posting_url = _identifier(event.get("posting_url"), "posting URL")
    if posting_url is None and (company is None or title is None):
        return {"status": "insufficient_evidence"}
    normalized_url = canonical_url(posting_url) if posting_url else None
    identifiers = {"company": company, "title": title, "posting_url": normalized_url}
    identifier_sha256 = hashlib.sha256(
        json.dumps(identifiers, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    existing = ledger.connection.execute(
        "SELECT * FROM gmail_application_matches WHERE message_id = ?", (message_id,)
    ).fetchone()
    if existing is not None:
        if (
            str(existing["thread_id"]) != thread_id
            or str(existing["evidence_sha256"]) != evidence_sha256
            or str(existing["identifier_sha256"]) != identifier_sha256
            or str(existing["received_at"]) != str(event["received_at"])
        ):
            raise FenceError("Gmail message is already bound to different evidence")
        return {"status": "matched", "application_id": str(existing["application_id"])}

    rows = ledger.connection.execute(
        """
        SELECT applications.*,
               COALESCE(external_application_imports.applied_at, applications.created_at)
                 AS effective_application_at
        FROM applications
        LEFT JOIN external_application_imports
          ON external_application_imports.application_id = applications.id
        """
    ).fetchall()
    matches = []
    for row in rows:
        try:
            effective = datetime.fromisoformat(str(row["effective_application_at"]))
        except ValueError:
            continue
        if effective.tzinfo is None or received < effective:
            continue
        if normalized_url is not None and str(row["canonical_url"]) != normalized_url:
            continue
        if company is not None and _normalize(str(row["company"])) != _normalize(company):
            continue
        if title is not None and _normalize(str(row["title"])) != _normalize(title):
            continue
        matches.append(str(row["id"]))
    if not matches:
        return {"status": "no_match"}
    if len(matches) != 1:
        return {"status": "ambiguous"}
    application_id = matches[0]
    if not persist:
        return {"status": "matched", "application_id": application_id}
    with ledger._transaction():
        ledger.connection.execute(
            """
            INSERT INTO gmail_application_matches
              (message_id, thread_id, application_id, evidence_sha256,
               identifier_sha256, received_at, matched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id, thread_id, application_id, evidence_sha256,
                identifier_sha256, str(event["received_at"]),
                datetime.now(received.tzinfo).isoformat(),
            ),
        )
    return {"status": "matched", "application_id": application_id}


def validate_match_result(
    *, ledger_path: Path, candidates_path: Path, result_path: Path
) -> dict[str, int]:
    candidates = json.loads(Path(candidates_path).read_text(encoding="utf-8"))
    result = json.loads(Path(result_path).read_text(encoding="utf-8"))
    events = {row["message_id"]: row for row in candidates.get("events", [])}
    processed = result.get("processed_message_ids")
    requests = result.get("gmail_matches")
    if not isinstance(processed, list) or not isinstance(requests, list):
        raise ValueError("processed_message_ids and gmail_matches must be arrays")
    request_ids = [row.get("message_id") for row in requests if isinstance(row, dict)]
    if len(request_ids) != len(requests) or len(request_ids) != len(set(request_ids)):
        raise ValueError("gmail_matches contains invalid or duplicate message IDs")
    if set(request_ids) != set(processed):
        raise ValueError("gmail_matches must cover exactly processed message IDs")
    ledger = Ledger(ledger_path)
    checked: list[tuple[dict[str, Any], dict[str, str]]] = []
    try:
        for request in requests:
            message_id = str(request["message_id"])
            candidate = events.get(message_id)
            if candidate is None:
                raise ValueError("gmail_matches contains an unscanned message")
            for field in ("thread_id", "received_at", "evidence_sha256"):
                if request.get(field) != candidate.get(field):
                    raise ValueError(f"gmail match {field} differs from scan evidence")
            match_event = {
                key: request.get(key) for key in (
                    "message_id", "thread_id", "received_at", "evidence_sha256",
                    "company", "title", "posting_url",
                )
            }
            actual = match_gmail_event(ledger, match_event, persist=False)
            checked.append((match_event, actual))
        matched = 0
        for match_event, actual in checked:
            persisted = match_gmail_event(ledger, match_event, persist=True)
            if persisted != actual:
                raise FenceError("Gmail match changed between validation and persistence")
            matched += actual["status"] == "matched"
    finally:
        ledger.close()
    return {"validated_count": len(checked), "matched_count": matched}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = validate_match_result(
        ledger_path=args.ledger,
        candidates_path=args.candidates,
        result_path=args.result,
    )
    args.output.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(args.output, 0o600)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
