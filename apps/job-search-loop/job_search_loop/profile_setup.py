from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from .config import ConfigError, validate_profile


PLACEHOLDERS = {
    "replace_me",
    "replace me",
    "todo",
    "tbd",
    "unknown",
    "example",
}


class ProfileSetupError(RuntimeError):
    pass


AUTHORITATIVE_DOCUMENT_KINDS = {"cv", "linkedin", "diploma", "reference"}
TAILORED_DOCUMENT_KINDS = {
    "application_resume",
    "cover_letter",
    "application_answer",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _required_text(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProfileSetupError(f"document fact requires {field}")
    return value.strip()


def ingest_document_facts(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ground extracted facts in immutable source documents and fail on conflicts."""
    accepted: list[dict[str, Any]] = []
    values_by_field: dict[str, tuple[str, str]] = {}

    for document in documents:
        kind = _required_text(document.get("kind"), field="kind")
        if kind in TAILORED_DOCUMENT_KINDS:
            raise ProfileSetupError(
                f"tailored application output cannot become profile truth: {kind}"
            )
        if kind not in AUTHORITATIVE_DOCUMENT_KINDS:
            raise ProfileSetupError(f"unsupported authoritative document kind: {kind}")

        path = _required_text(document.get("path"), field="path")
        sha256 = _required_text(document.get("sha256"), field="sha256").lower()
        if not SHA256_PATTERN.fullmatch(sha256):
            raise ProfileSetupError("document sha256 must be 64 lowercase hex characters")
        raw_facts = document.get("facts")
        if not isinstance(raw_facts, list):
            raise ProfileSetupError("document facts must be a list")

        for raw_fact in raw_facts:
            if not isinstance(raw_fact, dict):
                raise ProfileSetupError("document fact must be an object")
            fact_id = _required_text(raw_fact.get("id"), field="id")
            field = _required_text(raw_fact.get("field"), field="field")
            value = _required_text(raw_fact.get("value"), field="value")
            claim = _required_text(raw_fact.get("claim"), field="claim")
            source_span = _required_text(
                raw_fact.get("source_span"), field="source_span"
            )

            normalized = value.casefold()
            previous = values_by_field.get(field)
            if previous is not None and previous[0] != normalized:
                raise ProfileSetupError(
                    f"conflict for {field}: {previous[1]!r} versus {value!r}"
                )
            values_by_field[field] = (normalized, value)
            accepted.append(
                {
                    "id": fact_id,
                    "claim": claim,
                    "evidence": f"{path}: {source_span}",
                    "field": field,
                    "value": value,
                    "provenance": {
                        "kind": kind,
                        "path": path,
                        "sha256": sha256,
                        "source_span": source_span,
                    },
                }
            )
    return accepted


def _contains_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in PLACEHOLDERS or normalized.startswith("replace_me_")
    if isinstance(value, list):
        return any(_contains_placeholder(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_placeholder(item) for item in value.values())
    return False


def prepare_profile(value: Any) -> dict[str, Any]:
    if _contains_placeholder(value):
        raise ProfileSetupError("profile contains a placeholder value")
    try:
        profile = validate_profile(value)
    except ConfigError as error:
        raise ProfileSetupError(str(error)) from error
    candidate = profile["candidate"]
    email = candidate.get("application_email")
    if (
        not isinstance(email, str)
        or "@" not in email
        or any(character.isspace() for character in email)
    ):
        raise ProfileSetupError(
            "profile.candidate.application_email must be a valid email"
        )
    return profile


def collect_interactive() -> dict[str, Any]:
    name = input("Full name: ").strip()
    email = input("Application email: ").strip()
    facts: list[dict[str, str]] = []
    while True:
        claim = input("Verified fact claim (blank when finished): ").strip()
        if not claim:
            break
        evidence = input("Evidence for this fact: ").strip()
        if not evidence:
            raise ProfileSetupError("each fact requires evidence")
        facts.append(
            {
                "id": f"fact-{len(facts) + 1:03d}",
                "claim": claim,
                "evidence": evidence,
            }
        )
    if not facts:
        raise ProfileSetupError("at least one verified fact is required")
    return prepare_profile(
        {
            "version": 1,
            "candidate": {
                "name": name,
                "application_email": email,
            },
            "facts": facts,
        }
    )


def _load_answers(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProfileSetupError(f"invalid answers file: {error}") from error
    return prepare_profile(value)


def _load_documents(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProfileSetupError(f"invalid documents file: {error}") from error
    if not isinstance(value, dict):
        raise ProfileSetupError("documents file must be an object")
    candidate = value.get("candidate")
    documents = value.get("documents")
    if not isinstance(candidate, dict):
        raise ProfileSetupError("documents file requires candidate")
    if not isinstance(documents, list):
        raise ProfileSetupError("documents file requires documents list")
    return prepare_profile(
        {
            "version": 1,
            "candidate": candidate,
            "facts": ingest_document_facts(documents),
        }
    )


def write_profile(
    value: dict[str, Any],
    *,
    output: Path,
    replace: bool,
) -> dict[str, Any]:
    if output.exists() and not replace:
        raise ProfileSetupError(
            f"private profile already exists: {output}; use --replace to replace it"
        )
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output.parent, 0o700)
    temporary = output.with_name(f".{output.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary, 0o600)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "version": 1,
        "profile_path": str(output),
        "fact_count": len(value["facts"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--answers", type=Path)
    source.add_argument("--documents", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--replace", action="store_true")
    parsed = parser.parse_args(argv)
    try:
        if parsed.answers is not None:
            value = _load_answers(parsed.answers)
        elif parsed.documents is not None:
            value = _load_documents(parsed.documents)
        else:
            value = collect_interactive()
        receipt = write_profile(value, output=parsed.output, replace=parsed.replace)
    except (ProfileSetupError, EOFError) as error:
        print(f"job-search profile setup: {error}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
