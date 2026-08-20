#!/usr/bin/env python3
"""Canonical reader-visible media envelope shared by language drafts."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


START = "<!-- canonical-media:start -->"
END = "<!-- canonical-media:end -->"
HEADLINE = "![](headline-image.png)"
BODY_DIAGRAM = "![](body-diagram.png)"
MERMAID = """```mermaid
flowchart LR
  trigger["TRIGGER / 起動"] --> work["WORK / 実行"]
  work --> verify["VERIFY / 検証"]
  verify -->|PASS| done["DONE / 完了"]
  verify -->|FAIL| retry["SAFE RETRY / 安全な再試行"]
  retry --> trigger
```"""


class MediaContractError(ValueError):
    """The canonical draft does not identify one complete media package."""


def _envelope_match(source: str) -> re.Match[str] | None:
    return re.search(
        rf"(?ms)^{re.escape(START)}\n.*?^{re.escape(END)}\n?",
        source,
    )


def validate_media_contract(source: str) -> None:
    if source.count(START) != 1 or source.count(END) != 1:
        raise MediaContractError("canonical media envelope is missing or duplicated")
    match = _envelope_match(source)
    if match is None:
        raise MediaContractError("canonical media envelope is malformed")
    envelope = match.group(0)
    required = {
        HEADLINE: "headline image",
        BODY_DIAGRAM: "body diagram",
    }
    for value, label in required.items():
        if envelope.count(value) != 1:
            raise MediaContractError(
                f"canonical media envelope requires exactly one {label}"
            )
    if len(re.findall(r"^[ \t]*```[ \t]*mermaid\b", source, flags=re.M | re.I)) < 1:
        raise MediaContractError("canonical draft requires Mermaid source")


def attach_media_contract(source: str, mermaid_source: str | None = None) -> str:
    if START in source or END in source:
        validate_media_contract(source)
        return source
    has_mermaid = re.search(
        r"^[ \t]*```[ \t]*mermaid\b",
        source,
        flags=re.M | re.I,
    )
    authored = ""
    if has_mermaid is None:
        authored = (mermaid_source or MERMAID).strip() + "\n\n"
    envelope = (
        f"{START}\n{HEADLINE}\n\n{authored}{BODY_DIAGRAM}\n{END}\n"
    )
    normalized = source.rstrip() + "\n\n" + envelope
    validate_media_contract(normalized)
    return normalized


def strip_media_contract(source: str) -> str:
    validate_media_contract(source)
    match = _envelope_match(source)
    assert match is not None
    return (source[: match.start()] + source[match.end() :]).rstrip() + "\n"


def _atomic_text(path: Path, value: str) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("attach", "validate"))
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--mermaid-file", type=Path)
    args = parser.parse_args()
    draft = args.file.resolve(strict=True)
    source = draft.read_text(encoding="utf-8")
    if args.command == "attach":
        mermaid = (
            args.mermaid_file.resolve(strict=True).read_text(encoding="utf-8")
            if args.mermaid_file is not None
            else None
        )
        if mermaid is not None and not mermaid.lstrip().startswith("```mermaid"):
            mermaid = f"```mermaid\n{mermaid.strip()}\n```"
        _atomic_text(draft, attach_media_contract(source, mermaid))
    else:
        validate_media_contract(source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
