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
APPLICATION_FIELDS = (
    "organization", "program", "cohort_window", "account", "official_url",
    "contact", "question_answers", "attachments", "context_used",
    "context_version", "context_digest",
)


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


def application_digest(data: dict) -> str:
    payload = {key: data.get(key) for key in APPLICATION_FIELDS}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def replace_json(path: pathlib.Path, data: dict) -> None:
    encoded = (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(encoded)
        temporary = pathlib.Path(handle.name)
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", required=True)
    parser.add_argument("--ledger")
    parser.add_argument("--applications-dir")
    parser.add_argument("--run-id")
    parser.add_argument("--expected-context-version", required=True)
    parser.add_argument("--expected-context-digest", required=True)
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()

    draft_path = pathlib.Path(args.draft)
    data = json.loads(draft_path.read_text(encoding="utf-8"))
    identity, identity_hash = canonical_identity(data)
    official_url = required_text(data.get("official_url"), "official_url")
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

    context_version = required_text(data.get("context_version"), "context_version")
    context_digest = required_text(data.get("context_digest"), "context_digest")
    if context_version != args.expected_context_version:
        fail("context_version does not match the current canonical context")
    if context_digest != args.expected_context_digest:
        fail("context_digest does not match the current canonical context")
    digest = application_digest(data)

    if args.prepare:
        if data.get("submitted_at") is not None or data.get("evidence") is not None:
            fail("prepare requires a pre-submit draft without submitted_at or evidence")
        data["application_digest"] = digest
        data["previewed_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        replace_json(draft_path, data)
        print(json.dumps({"prepared": True, "application_digest": digest}))
        return

    for name in ("ledger", "applications_dir", "run_id"):
        if not getattr(args, name):
            fail(f"--{name.replace('_', '-')} is required when recording")
    if required_text(data.get("application_digest"), "application_digest") != digest:
        fail("application_digest does not match the prepared application")
    previewed_at = required_text(data.get("previewed_at"), "previewed_at")
    submitted_at = required_text(data.get("submitted_at"), "submitted_at")
    try:
        previewed_time = datetime.fromisoformat(previewed_at.replace("Z", "+00:00"))
        submitted_time = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
    except ValueError:
        fail("previewed_at and submitted_at must be ISO-8601")
    if submitted_time < previewed_time:
        fail("submitted_at must not precede previewed_at")

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
        "context_version": context_version,
        "context_digest": context_digest,
        "application_digest": digest,
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
