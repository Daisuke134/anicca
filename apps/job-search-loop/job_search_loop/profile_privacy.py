from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


SENSITIVE_FIELDS = (
    "application_email",
    "phone",
    "date_of_birth",
    "mailing_address",
)


class ProfileLeakError(RuntimeError):
    pass


def _values(value: Any, prefix: str) -> list[tuple[str, str]]:
    if isinstance(value, dict):
        result: list[tuple[str, str]] = []
        for key, item in value.items():
            result.extend(_values(item, f"{prefix}.{key}" if prefix else str(key)))
        return result
    if isinstance(value, list):
        result = []
        for index, item in enumerate(value):
            result.extend(_values(item, f"{prefix}[{index}]"))
        return result
    text = str(value or "").strip()
    return [(prefix, text)] if len(text) >= 4 else []


def scan_provider_log(
    *, profile_path: Path, log_path: Path, receipt_path: Path
) -> dict[str, Any]:
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        log_bytes = log_path.read_bytes()
    except (OSError, json.JSONDecodeError) as error:
        raise ProfileLeakError("privacy scan input is invalid") from error
    candidate = profile.get("candidate")
    if not isinstance(candidate, dict):
        raise ProfileLeakError("private candidate profile is missing")
    sensitive: list[tuple[str, str]] = []
    for field in SENSITIVE_FIELDS:
        if field in candidate:
            sensitive.extend(_values(candidate[field], field))
    text = log_bytes.decode("utf-8", errors="replace")
    folded = text.casefold()
    leaked_fields = sorted(
        {name for name, value in sensitive if value.casefold() in folded}
    )
    receipt = {
        "version": 1,
        "status": "leak_detected" if leaked_fields else "clean",
        "log_sha256": hashlib.sha256(log_bytes).hexdigest(),
        "scanned_field_count": len(sensitive),
        "leaked_fields": leaked_fields,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = receipt_path.with_name(f".{receipt_path.name}.tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    temporary.replace(receipt_path)
    if leaked_fields:
        raise ProfileLeakError("provider transcript contains private profile values")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("scan")
    scan.add_argument("--profile", type=Path, required=True)
    scan.add_argument("--log", type=Path, required=True)
    scan.add_argument("--output", type=Path, required=True)
    parsed = parser.parse_args(argv)
    try:
        scan_provider_log(
            profile_path=parsed.profile,
            log_path=parsed.log,
            receipt_path=parsed.output,
        )
    except ProfileLeakError as error:
        print(f"job-search privacy: {error}", file=__import__("sys").stderr)
        return 76
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
