"""lib/promotion_history.py — REQ-RL12: the "current promoted generation's operating window"
start timestamp, derived from git history. `subprocess` is deliberately confined to THIS module
(mirrors `lib/promote.py`'s own "subprocess deliberately confined to THIS module" convention).

The commit-message prefix below MUST stay in sync with `lib/promote.py::promote`'s own literal
commit message (`f"feat(self-improve): promote candidate {candidate_id}"`) — see
behavioral-spec.md's UNVERIFIED section for this disclosed manual-sync obligation.
"""
from __future__ import annotations

import subprocess
from typing import Optional

PROMOTION_COMMIT_MESSAGE_PREFIX = "feat(self-improve): promote candidate"


def last_promotion_ts(path: str, cwd: Optional[str] = None) -> Optional[int]:
    """REQ-RL12/EDGE-RL3: UNIX timestamp (`%ct`) of the MOST RECENT commit whose subject matches
    `PROMOTION_COMMIT_MESSAGE_PREFIX`, scoped to `path` (`git log -1` already returns the latest
    match first — no further sorting needed). Returns `None` when no such commit exists OR the git
    invocation itself fails for any reason (e.g. `path` outside `cwd`'s repository, no repository
    at all) — fail-closed, mirrors `resolve_ledger_path`'s own "never guess, never raise"
    convention. `None` here means REQ-RL10/RL11's `sufficient` gate is `False` for that reason
    alone (EDGE-RL3: no current generation to measure a trend against yet)."""
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                "-1",
                "--format=%ct",
                "--fixed-strings",
                f"--grep={PROMOTION_COMMIT_MESSAGE_PREFIX}",
                "--",
                path,
            ],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    out = result.stdout.strip()
    if not out:
        return None
    try:
        return int(out)
    except ValueError:
        return None
