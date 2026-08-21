#!/usr/bin/env python3
"""Check/write deterministic per-language quality-phase completion markers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from quality_self_heal import language_quality


def read_json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("check", "write"))
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--lang", required=True, choices=("ja", "en"))
    parser.add_argument("--markdown-file", required=True)
    args = parser.parse_args()
    run_dir = Path(args.run_dir)
    markdown = Path(args.markdown_file)
    marker = run_dir / "gates" / f"quality-terminal-{args.lang}.json"

    if args.command == "write":
        quality = language_quality(run_dir, args.lang, markdown)
        continuous = os.environ.get("ARTICLE_PUBLICATION_POLICY") == "continuous"
        identity = read_json(run_dir / "gates" / f"identity-{args.lang}.json")
        identity_pass = bool(
            identity
            and identity.get("verdict") == "PASS"
            and identity.get("article_sha256") == sha256(markdown)
        )
        reasons = [] if continuous else list(quality["reasons"])
        if not identity_pass:
            reasons.append("identity_not_current_pass")
        if reasons:
            print(
                "quality phase cannot become terminal: "
                + ",".join(reasons)
            )
            return 2
        atomic_write(marker, {
            "status": "terminal",
            "lang": args.lang,
            "article_sha256": sha256(markdown),
            "editorial_gate": "PASS" if quality["editorial"] == "PASS" else "ADVISORY",
            "reader_gate": "PASS" if quality["reader"] == "PASS" else "ADVISORY",
            "identity_gate": "PASS",
            "safety_gate": "ALLOW",
        })
        return 0

    current = read_json(marker)
    if (
        current
        and current.get("status") == "terminal"
        and current.get("editorial_gate") in {"PASS", "ADVISORY"}
        and current.get("reader_gate") in {"PASS", "ADVISORY"}
        and current.get("identity_gate") == "PASS"
        and current.get("safety_gate") == "ALLOW"
    ):
        if current.get("article_sha256") == sha256(markdown):
            print(f"quality phase terminal for {args.lang} (hash match)")
            return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
