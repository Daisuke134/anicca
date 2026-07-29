from __future__ import annotations

import argparse
import json
import os
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
    parser.add_argument("--answers", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--replace", action="store_true")
    parsed = parser.parse_args(argv)
    try:
        value = (
            _load_answers(parsed.answers)
            if parsed.answers is not None
            else collect_interactive()
        )
        receipt = write_profile(value, output=parsed.output, replace=parsed.replace)
    except (ProfileSetupError, EOFError) as error:
        print(f"job-search profile setup: {error}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
