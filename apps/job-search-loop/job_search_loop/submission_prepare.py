from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from .ledger import Ledger


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_submission(
    *,
    ledger_path: Path,
    application_id: str,
    japan_day: str,
    portfolio_bucket: str,
    resume_path: Path,
    snapshot_path: Path,
    fill_receipt_path: Path,
    answers_path: Path,
) -> dict[str, Any]:
    resume_path = Path(resume_path).expanduser().resolve()
    snapshot_path = Path(snapshot_path).expanduser().resolve()
    fill_receipt_path = Path(fill_receipt_path).expanduser().resolve()
    answers_path = Path(answers_path).expanduser().resolve()
    for label, path in (
        ("resume", resume_path),
        ("snapshot", snapshot_path),
        ("fill receipt", fill_receipt_path),
        ("answers", answers_path),
    ):
        if not path.is_file():
            raise ValueError(f"{label} is not a file")
    answers = json.loads(answers_path.read_text(encoding="utf-8"))
    if not isinstance(answers, list):
        raise ValueError("answers must be an array")
    payload_hash = hashlib.sha256(
        json.dumps(
            {
                "application_id": application_id,
                "resume_sha256": _sha256(resume_path),
                "snapshot_sha256": _sha256(snapshot_path),
                "fill_receipt_sha256": _sha256(fill_receipt_path),
                "answers": answers,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    ledger = Ledger(Path(ledger_path))
    try:
        intent = ledger.claim_submission(
            application_id,
            japan_day,
            payload_hash,
            resume_path=resume_path,
            resume_sha256=_sha256(resume_path),
            ats_snapshot_path=snapshot_path,
            ats_snapshot_sha256=_sha256(snapshot_path),
            fill_receipt_path=fill_receipt_path,
            fill_receipt_sha256=_sha256(fill_receipt_path),
            portfolio_bucket=portfolio_bucket,
        )
        if intent is None:
            raise RuntimeError("application is not eligible for a new submit intent")
        materials = ledger.record_submission_materials(
            intent_id=intent.intent_id,
            fence=intent.fence,
            resume_path=resume_path,
            resume_sha256=_sha256(resume_path),
            cover_letter=None,
            employer_answers=answers,
        )
        return {
            "version": 1,
            "status": "prepared",
            "application_id": application_id,
            "intent_id": intent.intent_id,
            "fence": intent.fence,
            "click_phase": ledger.submission_click_phase(intent.intent_id, intent.fence),
            "transport_phase": ledger.submission_transport_phase(intent.intent_id, intent.fence),
            "materials_payload_sha256": materials["payload_sha256"],
        }
    finally:
        ledger.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--application-id", required=True)
    parser.add_argument("--japan-day", required=True)
    parser.add_argument("--portfolio-bucket", required=True)
    parser.add_argument("--resume", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--fill-receipt", required=True, type=Path)
    parser.add_argument("--answers", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = prepare_submission(
            ledger_path=args.ledger,
            application_id=args.application_id,
            japan_day=args.japan_day,
            portfolio_bucket=args.portfolio_bucket,
            resume_path=args.resume,
            snapshot_path=args.snapshot,
            fill_receipt_path=args.fill_receipt,
            answers_path=args.answers,
        )
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f"submission prepare: {error}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(args.output, 0o600)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
