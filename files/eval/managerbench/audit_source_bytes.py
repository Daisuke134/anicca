#!/usr/bin/env python3
"""Read-only SHA-256 integrity check of frozen ManagerBench source file bytes.

Hashes repository-relative files registered in sources_sha256. Never trains,
infers, accesses network services, or modifies frozen receipts.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import re
from pathlib import Path

from audit_baseline_lineage import AuditError, load_strict_json


class SourceBytesError(AuditError):
    """Source bytes cannot be safely verified against a frozen SHA-256 digest."""


def verify_sources(snapshot, root):
    """Return the number of files whose raw-byte SHA-256 matches the receipt.

    Missing/unreadable/escaping files are errors, not zero or success.
    """
    if type(snapshot) is not dict:
        raise SourceBytesError("baseline must be a JSON object")
    sources = snapshot.get("sources_sha256")
    if type(sources) is not dict or not sources:
        raise SourceBytesError("sources_sha256 must be a nonempty JSON object")
    try:
        repo_root = Path(root).resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise SourceBytesError(f"cannot resolve root: {exc}") from exc
    if not repo_root.is_dir():
        raise SourceBytesError("root is not a directory")

    verified = 0
    seen_targets = {}
    seen_inodes = {}
    for name, expected in sources.items():
        if type(name) is not str or not name.strip():
            raise SourceBytesError("source filename must be nonempty text")
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise SourceBytesError(f"source path outside repository: {name!r}")
        if type(expected) is not str or re.fullmatch(r"[0-9a-fA-F]{64}", expected) is None:
            raise SourceBytesError(f"invalid SHA-256 digest for {name!r}")
        try:
            target = (repo_root / relative).resolve(strict=True)
            if not target.is_relative_to(repo_root) or not target.is_file():
                raise SourceBytesError(f"source path escapes root or is not a file: {name!r}")
            if target in seen_targets:
                raise SourceBytesError(
                    f"duplicate resolved source target: {name!r} aliases {seen_targets[target]!r}"
                )
            seen_targets[target] = name
            digest = hashlib.sha256()
            with target.open("rb") as source:
                stat = os.fstat(source.fileno())
                if stat.st_ino == 0:
                    raise SourceBytesError(f"source file identity unavailable: {name!r}")
                identity = (stat.st_dev, stat.st_ino)
                if identity in seen_inodes:
                    raise SourceBytesError(
                        f"duplicate physical source inode: {name!r} aliases {seen_inodes[identity]!r}"
                    )
                seen_inodes[identity] = name
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
        except (OSError, RuntimeError, ValueError) as exc:
            raise SourceBytesError(f"cannot read source {name!r}: {exc}") from exc
        if not hmac.compare_digest(digest.hexdigest(), expected.lower()):
            raise SourceBytesError(f"source raw-byte SHA-256 mismatch: {name!r}")
        verified += 1
    return verified


def main(argv=None):
    folder = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=folder / "baseline-2026-11-15.json")
    parser.add_argument("--root", type=Path, default=folder.parents[2])
    args = parser.parse_args(argv)
    try:
        count = verify_sources(load_strict_json(args.baseline), args.root)
    except (AuditError, SourceBytesError) as exc:
        parser.exit(2, f"SOURCE_BYTES_BLOCKED: {exc}\n")
    print(f"SOURCE_BYTES_PASS: verified_sources={count}")
    print("SCOPE: local source bytes only; no model inference or human outcome evidence")


if __name__ == "__main__":
    main()
