"""Common helpers — extracted in Phase 2c (refactor) per /vcsdd-impl skill.

These helpers consolidate small duplications across lib/* modules. They do NOT
add features, change behavior, or modify the spec — pure refactor.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def is_verdict_pass(verdict: dict) -> bool:
    """Adversary verdict.json has overallVerdict == 'PASS' iff converged.

    Used by: proposal_loop, deliverable_loop, mutation_gate.
    """
    return verdict.get("overallVerdict") == "PASS"


def sha256_file(path: Path) -> str:
    """SHA-256 hex digest of a file's bytes.

    Used by: spawn_pin (REQ-E5 sha-compare layer).
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def append_jsonl(path: Path, row: dict) -> None:
    """Single-line append to a jsonl file with parent-dir auto-create + utf-8.

    Used by: lessons (REQ-C1), mutation_gate (REQ-C3 rejected-mutation log),
    proposal_loop (REQ-I1 stalled lesson), deliverable_loop (REQ-I2 stalled
    lesson), group_j (REQ-F1 self-recover-log + REQ-J7 mother queue).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
