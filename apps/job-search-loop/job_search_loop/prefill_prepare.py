from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .ledger import Ledger


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_prefill(
    *,
    ledger_path: Path,
    company: str,
    title: str,
    official_url: str,
    resume_path: Path,
    posting_path: Path,
    answers_path: Path,
) -> dict[str, Any]:
    paths = {
        "resume": Path(resume_path).expanduser().resolve(),
        "posting": Path(posting_path).expanduser().resolve(),
        "answers": Path(answers_path).expanduser().resolve(),
    }
    for label, path in paths.items():
        if not path.is_file():
            raise ValueError(f"{label} is not a file")
        if path.stat().st_mode & 0o077:
            raise ValueError(f"{label} must be private")
    answers = json.loads(paths["answers"].read_text(encoding="utf-8"))
    answer_map = answers.get("answers") if isinstance(answers, dict) else None
    if (
        answers.get("status") != "ready"
        or answers.get("missing_required") != []
        or not isinstance(answer_map, dict)
        or not answer_map
    ):
        raise ValueError("answers artifact is not ready")
    fact_ids = sorted(
        {
            fact_id
            for answer in answer_map.values()
            if isinstance(answer, dict)
            for fact_id in answer.get("fact_ids", [])
            if isinstance(fact_id, str) and fact_id
        }
    )
    if not fact_ids:
        raise ValueError("answers artifact has no grounded fact IDs")
    posting = json.loads(paths["posting"].read_text(encoding="utf-8"))
    if posting.get("status") != "inspected" or not isinstance(posting.get("fields"), list):
        raise ValueError("posting inspection artifact is invalid")
    ledger = Ledger(Path(ledger_path))
    try:
        application_id = ledger.add_application(company, title, official_url)
        posting_sha256 = _sha256(paths["posting"])
        ledger.register_application_route(
            application_id,
            route_kind="canonical_ats",
            endpoint=official_url,
            ordinal=1,
            source_url=official_url,
            source_sha256=posting_sha256,
            recipient_acceptance="not_applicable",
        )
        artifacts = [
            ledger.record_application_artifact(
                application_id=application_id,
                kind="posting",
                path=paths["posting"],
                sha256=posting_sha256,
                fact_ids=[],
                source_urls=[official_url],
            ),
            ledger.record_application_artifact(
                application_id=application_id,
                kind="resume_draft",
                path=paths["resume"],
                sha256=_sha256(paths["resume"]),
                fact_ids=fact_ids,
                source_urls=[],
            ),
            ledger.record_application_artifact(
                application_id=application_id,
                kind="answers_draft",
                path=paths["answers"],
                sha256=_sha256(paths["answers"]),
                fact_ids=fact_ids,
                source_urls=[official_url],
            ),
        ]
        state = ledger.current_state(application_id)
        if state == "discovered":
            ledger.transition(application_id, "qualified")
            state = "qualified"
        if state == "qualified":
            ledger.transition(application_id, "materials_ready")
            state = "materials_ready"
        if state != "materials_ready":
            raise RuntimeError(f"application is not prefill-ready: {state}")
        return {
            "version": 1,
            "status": "prefill_materials_ready",
            "application_id": application_id,
            "artifact_ids": artifacts,
            "posting_sha256": posting_sha256,
            "resume_sha256": _sha256(paths["resume"]),
            "answers_sha256": _sha256(paths["answers"]),
            "submit_intent_id": None,
        }
    finally:
        ledger.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize Job Hunter pre-fill artifacts")
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--official-url", required=True)
    parser.add_argument("--resume", type=Path, required=True)
    parser.add_argument("--posting", type=Path, required=True)
    parser.add_argument("--answers", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare_prefill(
        ledger_path=args.ledger,
        company=args.company,
        title=args.title,
        official_url=args.official_url,
        resume_path=args.resume,
        posting_path=args.posting,
        answers_path=args.answers,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(args.output, 0o600)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
