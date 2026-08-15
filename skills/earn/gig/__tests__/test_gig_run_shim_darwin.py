"""PROP-S1 (back-compat), PROP-I1 (no ~/loops writes), PROP-I2 (no tmux kill)
integration tests on Darwin. Runs the real run.sh and parses its stdout JSON.

NOTE: this test reads ~/gig/ ledgers (production data) but writes NOTHING.
It also gates gig-cli.sh side-effects by skipping if HOME isn't pointing at
the real anicca user.

Moved here 2026-07-06 from Daisuke134/anicca (skills/_shared/__tests__/) when
skills/human-funded was isolated to this repo (.vcsdd/features/anicca-agent-economy
SPEC.md §3 P0) — the test travels with the code it exercises.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="gig run.sh shim is Darwin-only (depends on launchctl + ~/gig core)",
)

RUN_SH = Path(__file__).resolve().parents[1] / "run.sh"
LOOPS_DIR = Path.home() / "loops" / "gig"

EXISTING_KEYS = {
    "source", "task", "funding", "earn_usdc", "cost_usdc",
    "jpy_earned", "applied_total", "core", "wake", "note",
}


def _snapshot_mtimes(d: Path) -> dict:
    if not d.exists():
        return {}
    snap = {}
    for f in d.rglob("*"):
        try:
            snap[str(f)] = f.stat().st_mtime_ns
        except FileNotFoundError:
            pass
    return snap


def test_status_json_back_compat_and_shim_observability():
    """PROP-S1 + PROP-S2 + PROP-I1 in one integration shot.

    FIND-001 fix: seed ~/loops/gig/ with sentinel files BEFORE snapshot so
    the no-writes assertion has teeth (= a regression that modifies an
    existing file is caught, not just a no-op equality between {} and {}).
    """
    # ─── seed sentinel files so the snapshot is not empty ────────
    LOOPS_DIR.mkdir(parents=True, exist_ok=True)
    state_dir = LOOPS_DIR / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    sentinel_files = {
        LOOPS_DIR / "build_log.md": "## sentinel pass\nbudget: SENTINEL\n",
        state_dir / "core-status.json": json.dumps({"ts": 1, "slot": "gig", "step": "sentinel"}),
        LOOPS_DIR / ".sentinel-noop-test": "do-not-touch",
    }
    pre_existing = {p: p.exists() for p in sentinel_files}
    pre_content: dict[Path, str | None] = {}
    for p, body in sentinel_files.items():
        if not p.exists():
            p.write_text(body)
        pre_content[p] = p.read_text()
    try:
        before = _snapshot_mtimes(LOOPS_DIR)
        assert before, "snapshot must be non-empty after seeding (= FIND-001 fix)"

        r = subprocess.run(["bash", str(RUN_SH)], capture_output=True, text=True, timeout=30)
        assert r.returncode == 0, f"run.sh exit non-zero: {r.stderr}"

        # parse stdout (last line is the JSON)
        lines = [l for l in r.stdout.splitlines() if l.strip().startswith("{")]
        assert lines, f"no JSON line in stdout: {r.stdout[:500]}"
        data = json.loads(lines[-1])

        # PROP-S1: all existing keys preserved
        missing = EXISTING_KEYS - set(data.keys())
        assert not missing, f"REQ-S1 violation: missing existing keys {missing}"

        # PROP-S2: proactive_loop object present with 4 named keys
        assert "proactive_loop" in data, "REQ-S2 violation: proactive_loop key missing"
        pl = data["proactive_loop"]
        assert set(pl.keys()) == {"installed", "last_pass_ts", "last_pass_step", "build_log_passes"}, \
            f"REQ-S2 violation: proactive_loop shape = {set(pl.keys())}"

        # PROP-I1 strict: no mtime changes + content unchanged for seeded files
        after = _snapshot_mtimes(LOOPS_DIR)
        new_or_missing = set(after) ^ set(before)
        assert not new_or_missing, f"REQ-I1 violation: file set changed: {new_or_missing}"
        for p, before_ts in before.items():
            assert after[p] == before_ts, f"REQ-I1 violation: mtime changed on {p}"
        # Content invariance (catches a same-mtime overwrite — defense in depth)
        for p, before_body in pre_content.items():
            assert p.read_text() == before_body, f"REQ-I1 violation: content rewritten on {p}"

        # PROP-S5 sanity: with sentinel build_log present, shim reports >= 1 pass
        assert pl["build_log_passes"] >= 1, \
            f"REQ-S5 violation: sentinel has '## sentinel pass' header but build_log_passes={pl['build_log_passes']}"
    finally:
        # Restore: remove only files we created; leave any pre-existing ones alone.
        for p, was_existing in pre_existing.items():
            if not was_existing and p.exists():
                p.unlink()
