"""promote.py — writes a promoted candidate's whole-file program text into the live/paper baseline
strategy file and commits it (REQ-RH4). Mirrors skills/earn/lib/evolve.mjs::promote's
write-then-path-scoped-git-commit shape, adapted from a JSON genome to a whole-file strategy
program.

Invoked ONLY by the orchestration layer, and ONLY after `gate_math.stage_gate(...)` returns True
(REQ-RH4's ordered gate: stage2 walk-forward PASS -> trip-wire clear -> fresh adversary PASS).
NEVER invoked by evaluate()/evaluate_stage1()/evaluate_stage2() directly (REQ-EV7 — fitness
computation and promotion/ledger-adjacent mutation are structurally separate code paths).

`subprocess` is deliberately confined to THIS module. It must never appear inside an
EVOLVE-BLOCK — scope_guard.py's DENYLIST_MODULES blocks the literal string "subprocess" from ever
appearing there — and this file itself sits entirely outside the EVOLVE-BLOCK/evaluator boundary
(REQ-RH3).
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Optional


def candidate_id(candidate_code: str) -> str:
    """Short deterministic content hash for the promoted candidate — mirrors
    genome.mjs::genomeId's role for version/P&L attribution."""
    return hashlib.sha256(candidate_code.encode("utf-8")).hexdigest()[:12]


def promote(candidate_code: str, baseline_path: str, *, cwd: Optional[str] = None, commit: bool = True) -> dict:
    """Write `candidate_code` to `baseline_path` and (optionally) git-commit it, path-scoped
    (`git commit -- <path>`, exactly like evolve.mjs::promote) so a promotion can never sweep
    unrelated changes into its commit. `commit=False` writes the file only (for dry-run tooling);
    tests exercising the promotion GATE never call this with `commit=True` against a real repo —
    they mock this function entirely (see tests/test_adversary_disapprove.py)."""
    path = Path(baseline_path)
    path.write_text(candidate_code, encoding="utf-8")
    result = {"candidate_id": candidate_id(candidate_code), "path": str(path), "committed": False}
    if commit:
        repo_root = cwd or str(path.resolve().parent)
        subprocess.run(["git", "add", "--", str(path)], cwd=repo_root, check=True)
        subprocess.run(
            [
                "git",
                "-c", "user.name=Anicca Self-Improve",
                "-c", "user.email=self-improve@anicca.local",
                "commit",
                "-m", f"feat(self-improve): promote candidate {result['candidate_id']}",
                "--", str(path),
            ],
            cwd=repo_root,
            check=True,
        )
        rev = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True
        )
        result["committed"] = True
        result["commit"] = rev.stdout.strip()
    return result
