"""PROP-D1 static grep over shared shim-adjacent sources.

Forbidden patterns (human-touch surfaces).

2026-07-06: this file used to ALSO parametrize over gig's own run.sh (PROP-I2,
tmux-kill ban) — skills/human-funded is now isolated to the private
profitable-claude repo (.vcsdd/features/anicca-agent-economy SPEC.md §3 P0),
which carries its own copy of that gig-specific check. This file keeps ONLY
the shared-infra half (proactive_observe.py, used across all earn slots).
"""
from __future__ import annotations
import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
OBSERVE_PY = REPO_ROOT / "skills" / "_shared" / "lib" / "proactive_observe.py"

HUMAN_TOUCH_PATTERNS = [
    r"\bosascript\b", r"\bterminal-notifier\b",
    r"telegram\.org", r"hooks\.slack\.com", r"\btwilio\b",
    r"\bsudo\b", r"\bSecKeychain\b",
    r"find-generic-password", r"security add-generic-password",
]


def _read(p: Path) -> str:
    if not p.exists():
        pytest.fail(f"required source missing: {p}")
    return p.read_text()


@pytest.mark.parametrize("src", [OBSERVE_PY])
def test_no_human_touch(src):
    txt = _read(src)
    for pat in HUMAN_TOUCH_PATTERNS:
        m = re.search(pat, txt, flags=re.IGNORECASE)
        assert not m, f"forbidden pattern {pat!r} in {src}: {m.group(0)}"
