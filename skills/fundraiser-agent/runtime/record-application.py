#!/usr/bin/env python3
"""Persist a verified fundraiser application dossier and its compact index row."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import tempfile
from datetime import datetime, timezone


TERMINAL = {"submitted_verified", "submit_unknown"}


def fail(message: str) -> None:
    raise SystemExit(f"record-application: {message}")


def required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{name} must be non-empty text")
    return value.strip()


def canonical_identity(data: dict) -> tuple[str, str]:
    parts = [
        required_text(data.get("organization"), "organization"),
        required_text(data.get("program"), "program"),
        required_text(data.get("cohort_window"), "cohort_window"),
        required_text(data.get("account"), "account"),
    ]
    identity = " | ".join(part.casefold() for part in parts)
    return identity, hashlib.sha256(identity.encode()).hexdigest()


def read_rows(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--applications-dir", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    draft_path = pathlib.Path(args.draft)
    data = json.loads(draft_path.read_text(encoding="utf-8"))
    identity, identity_hash = canonical_identity(data)
    official_url = required_text(data.get("official_url"), "official_url")
    submitted_at = required_text(data.get("submitted_at"), "submitted_at")
    try:
        datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
    except ValueError:
        fail("submitted_at must be ISO-8601")

    contact = data.get("contact")
    if not isinstance(contact, dict):
        fail("contact must be an object")
    required_text(contact.get("method"), "contact.method")
    required_text(contact.get("destination"), "contact.destination")

    answers = data.get("question_answers")
    if not isinstance(answers, list) or not answers:
        fail("question_answers must contain every submitted field")
    for index, item in enumerate(answers):
        if not isinstance(item, dict):
            fail(f"question_answers[{index}] must be an object")
        required_text(item.get("question"), f"question_answers[{index}].question")
        if "answer" not in item or item["answer"] is None:
            fail(f"question_answers[{index}].answer is required")

    if not isinstance(data.get("context_used"), dict) or not data["context_used"]:
        fail("context_used must record the actual claims/sources used")

    evidence = data.get("evidence")
    if not isinstance(evidence, dict):
        fail("evidence must be an object")
    png = pathlib.Path(required_text(evidence.get("completion_png"), "evidence.completion_png"))
    if not png.is_absolute() or not png.is_file():
        fail("completion_png must be an existing absolute file")
    msgid = evidence.get("telegram_photo_message_id")
    if not isinstance(msgid, int) or msgid <= 0:
        fail("telegram_photo_message_id must be a positive integer")
    required_text(evidence.get("provider_readback"), "evidence.provider_readback")

    ledger = pathlib.Path(args.ledger)
    for row in read_rows(ledger):
        if row.get("receipt_identity_hash") == identity_hash and row.get("status") in TERMINAL:
            fail(f"duplicate terminal application: {identity_hash}")

    applications_dir = pathlib.Path(args.applications_dir)
    applications_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(applications_dir, 0o700)
    dossier_path = applications_dir / f"{identity_hash}.json"
    if dossier_path.exists():
        fail(f"dossier already exists: {dossier_path}")

    dossier = dict(data)
    dossier.update({
        "schema_version": 1,
        "run_id": args.run_id,
        "receipt_identity": identity,
        "receipt_identity_hash": identity_hash,
        "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    encoded = (json.dumps(dossier, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    with tempfile.NamedTemporaryFile(dir=applications_dir, delete=False) as handle:
        handle.write(encoded)
        temp_path = pathlib.Path(handle.name)
    os.chmod(temp_path, 0o600)
    os.replace(temp_path, dossier_path)
    dossier_sha = hashlib.sha256(encoded).hexdigest()

    ledger.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    row = {
        "run_id": args.run_id,
        "receipt_identity": identity,
        "receipt_identity_hash": identity_hash,
        "organization": data["organization"],
        "program": data["program"],
        "cohort_window": data["cohort_window"],
        "official_url": official_url,
        "status": "submitted_verified",
        "utc_timestamp": submitted_at,
        "provider_readback": evidence["provider_readback"],
        "completion_png": str(png),
        "telegram_photo_message_id": msgid,
        "application_record_path": str(dossier_path),
        "application_record_sha256": dossier_sha,
    }
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    os.chmod(ledger, 0o600)
    print(json.dumps({"recorded": True, "receipt_identity_hash": identity_hash,
                      "application_record_path": str(dossier_path)}))


if __name__ == "__main__":
    main()
