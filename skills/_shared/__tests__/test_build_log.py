"""PROP-M1 + M2 + M4 — build_log + menu loader.

REQ-M1: build_log.md append-only.
REQ-M2: menu.json malformed → fallback.
REQ-M4: sprint-1 jsonl streams NEVER rewritten.
"""
from __future__ import annotations

import json
import pytest

from lib.build_log import (  # FAIL until 2b
    format_log_section,
    parse_log_section,
    append_pass,
)
from lib.menu import load_menu  # FAIL until 2b


# ─── PROP-M1-append-only ──────────────────────────────────────────
def test_append_pass_does_not_overwrite(tmp_path):
    log_path = tmp_path / "build_log.md"
    log_path.write_text("# existing\n\nold content\n")
    append_pass(log_path, pass_id="p1", ts=1782900000, budget="FULL",
                picked="scan-requests", outcome="ok", next_candidate="nurture")
    content = log_path.read_text()
    # Old content preserved + new section appended
    assert "old content" in content
    assert "p1" in content
    assert content.endswith("\n")


def test_format_log_section_structure():
    section = format_log_section(
        pass_id="p1", ts=1782900000, budget="FULL",
        picked="scan-requests", outcome="ok", next_candidate="nurture",
    )
    assert "## " in section
    assert "p1" in section
    assert "FULL" in section
    assert "scan-requests" in section


def test_parse_log_section_round_trip():
    section = format_log_section(
        pass_id="p1", ts=1782900000, budget="MEDIUM",
        picked="nurture-talk-rooms", outcome="2-rooms-replied", next_candidate="deliver",
    )
    parsed = parse_log_section(section)
    assert parsed["pass_id"] == "p1"
    assert parsed["budget"] == "MEDIUM"
    assert parsed["picked"] == "nurture-talk-rooms"


# ─── PROP-M2-menu-load ────────────────────────────────────────────
def test_load_menu_malformed_falls_back(tmp_path):
    bad = tmp_path / "menu.json"
    bad.write_text("not valid json {{{")
    menu = load_menu(bad)
    assert menu is not None
    assert "categories" in menu
    # Fallback marker visible
    assert any(c.get("name") == "pending" for c in menu["categories"])


def test_load_menu_valid_returns_parsed(tmp_path):
    good = tmp_path / "menu.json"
    good.write_text(json.dumps({
        "schema_version": 1,
        "categories": [{"name": "scan-requests", "roi_estimate_jpy": 1000,
                       "probability_of_landing": 0.1}],
        "novelty_quota_ratio": 0.1,
    }))
    menu = load_menu(good)
    assert menu["categories"][0]["name"] == "scan-requests"


# ─── PROP-M4-jsonl-preserved ──────────────────────────────────────
def test_sprint_1_jsonl_paths_never_appear_in_write_mode():
    """static-analysis: grep proactive_loop + build_log sources for write-mode
    opens on the sprint-1 jsonl streams. Should be zero hits except for the
    canonical append-only callers."""
    from pathlib import Path
    SHARED = Path(__file__).resolve().parent.parent
    PROTECTED_PATHS = ["lessons.jsonl", "earnings.jsonl", "applied.jsonl", "roi.jsonl"]
    SCANNABLE = ["proactive_loop.py", "build_log.py", "menu.py", "quota_tracker.py",
                 "bot2bot.py", "health_check_v2.py"]
    for fname in SCANNABLE:
        fpath = SHARED / "lib" / fname
        if not fpath.exists():
            continue
        src = fpath.read_text()
        for prot in PROTECTED_PATHS:
            if prot in src:
                # Hit found — must be ONLY in read context, not 'w' mode
                # This is a heuristic: open(...prot..., 'w') is the violation
                # Allow append-only patterns 'a' mode
                if f"open({prot}" in src and ", 'w'" in src:
                    pytest.fail(f"{fname} opens {prot} in write mode (forbidden by M4)")
