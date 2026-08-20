#!/usr/bin/env python3
"""Build a redacted evidence index for every failed Writer trace span."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR / "_shared"))
from pii_scan import scan  # noqa: E402
from writer_observability_trace import TraceError, build_trace  # noqa: E402


SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|authorization|bearer|cookie|password|secret|token)"
    r"(\s*[:=]\s*|\s+)[^\s,;]+"
)
MAX_EXCERPT_CHARS = 1200


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _release(run_dir: Path) -> str | None:
    path = run_dir / "git-hash.txt"
    if path.is_symlink() or not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("harness_git_hash="):
            return line.partition("=")[2].strip() or None
    return None


def _log_candidates(run_dir: Path, phase: str) -> list[Path]:
    stem = phase.removeprefix("gate:")
    gates = run_dir / "gates"
    candidates = [gates / f"{stem}{suffix}" for suffix in (".stderr", ".log")]
    if phase.startswith("destination:"):
        candidates.append(gates / "platform-dispatch-results.jsonl")
    return [path for path in candidates if path.is_file() and not path.is_symlink()]


def _log_excerpt(path: Path, phase: str) -> str:
    if path.name != "platform-dispatch-results.jsonl":
        return path.read_text(encoding="utf-8", errors="replace")[-MAX_EXCERPT_CHARS:]
    pair = phase.removeprefix("destination:")
    platform, lang = pair.split("/", 1)
    aliases = {"x-article": "x", "zenn-article": "zenn"}
    platform = aliases.get(platform, platform)
    matched = ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        row_platform = row.get("platform")
        if pair.startswith("substack/"):
            platform_match = row_platform in {"substack", f"substack-{lang}"}
        else:
            platform_match = row_platform == platform
        if platform_match and row.get("lang") == lang:
            matched = str(row.get("raw_output") or row.get("reason") or "")
    return matched[-MAX_EXCERPT_CHARS:]


def _safe_logs(run_dir: Path, phase: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in _log_candidates(run_dir, phase):
        raw = _log_excerpt(path, phase)
        redacted = SECRET_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", raw)
        findings = scan(redacted, blocklist=("__writer_evidence_never_match__",), source=str(path))
        row: dict[str, Any] = {
            "path": str(path.relative_to(run_dir)),
            "sha256": _sha256(path),
            "excerpt": None,
            "omitted_reason": None,
        }
        if findings:
            row["omitted_reason"] = "pii_detected"
            row["finding_rules"] = sorted({finding.rule_id for finding in findings})
        else:
            row["excerpt"] = redacted
        rows.append(row)
    return rows


def _browser_evidence(run_dir: Path, phase: str) -> list[dict[str, str]]:
    stem = phase.removeprefix("gate:").replace(":", "-").replace("/", "-")
    rows: list[dict[str, str]] = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        lowered = path.name.lower()
        evidence_kind = next(
            (kind for kind in ("screenshot", "dom", "network", "trace", "accessibility")
             if kind in lowered),
            None,
        )
        if evidence_kind is None or (stem not in lowered and phase not in {"publication", "readback"}):
            continue
        rows.append({
            "kind": evidence_kind,
            "path": str(path.relative_to(run_dir)),
            "sha256": _sha256(path),
        })
    return rows


def build_evidence_index(run_dir: Path, observed_at: str) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    trace = build_trace(run_dir, observed_at)
    last_success: dict[str, Any] | None = None
    incidents: list[dict[str, Any]] = []
    release = _release(run_dir)
    for span in trace["spans"]:
        if span["state"] == "observed":
            last_success = {"phase": span["phase"], "span_id": span["span_id"]}
            continue
        if span["state"] != "error":
            continue
        source = span.get("source_receipt")
        incidents.append({
            "incident_id": hashlib.sha256(
                f"{trace['run_id']}\0{span['phase']}\0{span['reason']}".encode()
            ).hexdigest(),
            "phase": span["phase"],
            "reason": span["reason"],
            "trace_id": span["trace_id"],
            "span_id": span["span_id"],
            "source_receipt": source,
            "evidence_status": "indexed" if source else "source_receipt_missing",
            "safe_logs": _safe_logs(run_dir, span["phase"]),
            "browser_evidence": _browser_evidence(run_dir, span["phase"]),
            "source_release": span.get("release_commit") or release,
            "last_successful_sibling": last_success,
        })
    return {
        "schema": "writer.observability.evidence-index",
        "version": 1,
        "run_id": trace["run_id"],
        "observed_at": observed_at,
        "incident_count": len(incidents),
        "incidents": incidents,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--run-dir", required=True, type=Path)
    build.add_argument("--observed-at", required=True)
    build.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        index = build_evidence_index(args.run_dir, args.observed_at)
    except (TraceError, OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    encoded = json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.out.with_name(f".{args.out.name}.{os.getpid()}.tmp")
        temporary.write_text(encoded, encoding="utf-8")
        os.replace(temporary, args.out)
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
