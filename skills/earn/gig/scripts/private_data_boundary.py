"""Keep buyer credentials available to mechanical tools but outside model context."""
from __future__ import annotations

import hashlib
import mimetypes
import re
from pathlib import Path
from typing import Any


_PRIVATE_DIRS = ("source/buyer-attachments/", "source/dm/attachments/")
_CREDENTIAL_NAME = re.compile(
    r"(?i)(credential|password|passwd|passcode|username|login|api[_ -]?key|token|secret|パスワード|認証)"
)
_CREDENTIAL_TEXT = re.compile(
    r"(?i)(?:password|passwd|passcode|api[_ -]?key|access[_ -]?token|secret|bearer|ログイン|パスワード)\s*[:=：]"
)
_VALUE_AFTER_LABEL = re.compile(
    r"(?i)((?:password|passwd|passcode|api[_ -]?key|access[_ -]?token|secret|bearer|ログイン|パスワード)\s*[:=：]\s*)([^\s,;]+)"
)


def is_buyer_attachment(root: Path, path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return False
    return relative.startswith(_PRIVATE_DIRS)


def is_credential_attachment(root: Path, path: Path) -> bool:
    if not is_buyer_attachment(root, path) or _CREDENTIAL_NAME.search(path.name):
        return is_buyer_attachment(root, path) and bool(_CREDENTIAL_NAME.search(path.name))
    try:
        sample = path.read_bytes()[:1024 * 1024]
    except OSError:
        return False
    if b"\x00" in sample:
        return False
    return bool(_CREDENTIAL_TEXT.search(sample.decode("utf-8", errors="ignore")))


def restricted_attachment_paths(root: Path) -> list[Path]:
    rows: list[Path] = []
    for relative in _PRIVATE_DIRS:
        directory = root / relative
        if directory.is_dir():
            rows.extend(path.resolve() for path in directory.rglob("*")
                        if path.is_file() and is_credential_attachment(root, path))
    return sorted(set(rows))


def attachment_metadata(root: Path, path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "content_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "purpose": "buyer-supplied account credential; mechanical authenticated tool only",
        "restricted": True,
    }


def redact_prompt_text(value: Any) -> str:
    return _VALUE_AFTER_LABEL.sub(r"\1[REDACTED]", str(value or ""))
