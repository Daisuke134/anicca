"""PROP-D1 + PROP-I2 static grep over run.sh (this skill's own shim).

Forbidden patterns (human-touch surfaces) + tmux-kill ban.

Moved here 2026-07-06 from Daisuke134/anicca (skills/_shared/__tests__/) when
skills/human-funded was isolated to this repo (.vcsdd/features/anicca-agent-economy
SPEC.md §3 P0) — the run.sh-specific half of that test travels with the code it
exercises. The shared-infra half (proactive_observe.py) stayed in anicca.
"""
from __future__ import annotations
import re
from pathlib import Path
import pytest

RUN_SH = Path(__file__).resolve().parents[1] / "run.sh"

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


def test_no_human_touch():
    txt = _read(RUN_SH)
    for pat in HUMAN_TOUCH_PATTERNS:
        m = re.search(pat, txt, flags=re.IGNORECASE)
        assert not m, f"forbidden pattern {pat!r} in {RUN_SH}: {m.group(0)}"


def test_no_tmux_kill_in_run_sh():
    """PROP-I2 / parent INV-1: shim MUST NOT kill the LAYER C tmux core."""
    txt = _read(RUN_SH)
    forbidden = [r"tmux\s+kill", r"--restart", r"--stop", r"--kill"]
    for pat in forbidden:
        m = re.search(pat, txt)
        assert not m, f"PROP-I2 violation: run.sh contains {pat!r}: {m.group(0)}"
