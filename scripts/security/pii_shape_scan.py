#!/usr/bin/env python3
"""Fail closed on personal-data shapes without printing matched values."""

from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Collection, Iterable, Sequence


SUPPORTED_SUFFIXES = {
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}
IGNORED_PARTS = {".git", ".next", "node_modules"}
FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")

PATTERNS = (
    ("json_phone", re.compile(r'"phone"\s*:\s*"(\+[0-9]+)"')),
    ("home_address", re.compile(r'"home_address"\s*:\s*"[^"]+"')),
    ("jp_postal", re.compile(r"〒[0-9]{3}-[0-9]{4}")),
    ("personal_gmail", re.compile(r"[a-z0-9._%+-]+@gmail\.com", re.IGNORECASE)),
    ("jp_e164", re.compile(r"\+81[0-9]{9,11}")),
    ("jp_national_mobile", re.compile(r"(?<![0-9])0[789]0[0-9]{8}(?![0-9])")),
    ("us_e164", re.compile(r"\+1[0-9]{10}")),
)


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    pattern: str
    fingerprint: str

    def render(self) -> str:
        return f"{self.path}:{self.line}:{self.pattern}"


def fingerprint_for(pattern: str, relative_path: Path, value: str) -> str:
    payload = f"{pattern}\0{relative_path.as_posix()}\0{value}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_allowlist(path: Path) -> frozenset[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return frozenset()
    fingerprints = set()
    for line_number, line in enumerate(lines, start=1):
        candidate = line.partition("#")[0].strip()
        if not candidate:
            continue
        if not FINGERPRINT.fullmatch(candidate):
            raise ValueError(
                f"invalid PII fingerprint at {path}:{line_number}"
            )
        fingerprints.add(candidate)
    return frozenset(fingerprints)


def _is_supported(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES


def discover_paths(roots: Sequence[Path]) -> list[Path]:
    discovered: set[Path] = set()
    for root in roots:
        if _is_supported(root):
            discovered.add(root)
            continue
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if any(part in IGNORED_PARTS for part in path.parts):
                continue
            if _is_supported(path):
                discovered.add(path)
    return sorted(discovered)


def _relative_path(path: Path, root: Path | None) -> Path:
    if root is None:
        return Path(path.name)
    try:
        return path.resolve().relative_to(root.resolve())
    except ValueError:
        return Path(path.name)


def scan_paths(
    paths: Iterable[Path],
    *,
    root: Path | None = None,
    allowed_fingerprints: Collection[str] = (),
) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        relative_path = _relative_path(path, root)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, text in enumerate(lines, start=1):
            json_phone_matches = list(PATTERNS[0][1].finditer(text))
            for pattern_name, pattern in PATTERNS:
                for match in pattern.finditer(text):
                    value = match.group(1) if pattern_name == "json_phone" else match.group(0)
                    if pattern_name in {"jp_e164", "us_e164"} and any(
                        json_match.start() <= match.start() and match.end() <= json_match.end()
                        for json_match in json_phone_matches
                    ):
                        continue
                    fingerprint = fingerprint_for(pattern_name, relative_path, value)
                    if fingerprint in allowed_fingerprints:
                        continue
                    findings.append(
                        Finding(
                            path=relative_path,
                            line=line_number,
                            pattern=pattern_name,
                            fingerprint=fingerprint,
                        )
                    )
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", nargs="*", default=["."])
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=Path(".pii-shape-allowlist"),
    )
    args = parser.parse_args(argv)
    root = Path(".").resolve()
    findings = scan_paths(
        discover_paths([Path(candidate) for candidate in args.roots]),
        root=root,
        allowed_fingerprints=load_allowlist(args.allowlist),
    )
    for finding in findings:
        print(finding.render())
    if findings:
        print(f"PII shape scan found {len(findings)} redacted finding(s)")
        return 1
    print("PII shape scan clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
