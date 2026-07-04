"""PROP-D1 + PROP-I2 static grep over the shim sources.

Forbidden patterns (human-touch surfaces) + tmux-kill ban.
"""
from __future__ import annotations
import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_SH = REPO_ROOT / "skills" / "human-funded" / "gig" / "run.sh"
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


@pytest.mark.parametrize("src", [RUN_SH, OBSERVE_PY])
def test_no_human_touch(src):
    txt = _read(src)
    for pat in HUMAN_TOUCH_PATTERNS:
        m = re.search(pat, txt, flags=re.IGNORECASE)
        assert not m, f"forbidden pattern {pat!r} in {src}: {m.group(0)}"


def test_no_tmux_kill_in_run_sh():
    """PROP-I2 / parent INV-1: shim MUST NOT kill the LAYER C tmux core."""
    txt = _read(RUN_SH)
    forbidden = [r"tmux\s+kill", r"--restart", r"--stop", r"--kill"]
    for pat in forbidden:
        m = re.search(pat, txt)
        assert not m, f"PROP-I2 violation: run.sh contains {pat!r}: {m.group(0)}"
