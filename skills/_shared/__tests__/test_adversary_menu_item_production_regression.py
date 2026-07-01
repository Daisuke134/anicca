"""Sprint-3 #35: adversary-daily as menu item — production regression tests.

Ensures the adversary-daily item stays present in the canonical gig menu.json
with the correct 86400s cadence + zero-ROI recognition, and that sprint-1
adversary-daily.sh remains absent from active cron (INV-3 of architecture spec).
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest


darwin_only = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="production regression tests are Darwin-only (launchctl + ~/loops/gig)"
)


# ─── #35 REQ: production gig menu.json has adversary-daily item ───
@darwin_only
def test_production_gig_menu_has_adversary_daily_item():
    menu_path = Path.home() / "loops" / "gig" / "menu.json"
    if not menu_path.exists():
        pytest.skip("~/loops/gig/menu.json not yet installed (pre-#27 state)")
    menu = json.loads(menu_path.read_text())
    cats = menu.get("categories", [])
    adv = [c for c in cats if c.get("category") == "adversary"]
    assert len(adv) >= 1, "REQ-#35: at least one adversary category item expected"
    item = adv[0]
    assert item.get("min_cadence_seconds") == 86400, \
        f"REQ-EDGE-S7: adversary cadence must be 86400s, got {item.get('min_cadence_seconds')}"
    # Sprint-3 documents zero ROI as intentional — sprint-4 adds forced-pick
    # priority when cadence elapses.
    assert item.get("roi_estimate_jpy", 0) == 0, \
        "sprint-3 #35: adversary item ships with roi=0; sprint-4 adds cadence-forced-pick"


# ─── INV-3: sprint-1 adversary-daily.sh NOT in launchd (architecture spec §4) ─
@darwin_only
def test_sprint1_adversary_daily_sh_not_in_launchd():
    r = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=5)
    assert r.returncode == 0
    # No entry named like adversary-daily (sprint-1 script). Note: the
    # proactive-loop plist itself may schedule adversary indirectly via
    # menu.json — that's OK. This test bans the sprint-1 SH script wrapper
    # only.
    forbidden_patterns = ["adversary-daily.sh", "ai.anicca.adversary-daily"]
    for pat in forbidden_patterns:
        assert pat not in r.stdout, \
            f"INV-3 violation: sprint-1 pattern {pat!r} found in launchctl list"


# ─── sprint-2 EDGE-S7 cadence test is present + green (regression) ─
def test_edge_s7_regression_still_covers_adversary_cadence():
    """The sprint-2 EDGE-S7 test file must still exist and reference the
    adversary-daily menu item with cadence. Guard against accidental
    deletion during sprint-3 refactors."""
    test_file = Path(__file__).resolve().parent / "test_edge_cases_sprint2.py"
    assert test_file.exists(), "sprint-2 EDGE-S7 test file missing"
    txt = test_file.read_text()
    assert "EDGE-S7" in txt
    assert "adversary" in txt.lower()
    assert "86400" in txt or "min_cadence_seconds" in txt
