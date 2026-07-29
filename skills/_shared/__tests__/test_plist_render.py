"""PROP-A1..A4, PROP-B1, PROP-D1, PROP-E2 unit tests for lib.plist_render.

PURE helpers: validate_slot, render_plist, plist_digest, parse_loaded_plist_path.
Cross-platform — no launchctl, no disk. Phase 2a RED for install-proactive-plist.
"""
from __future__ import annotations
from pathlib import Path
import pytest

# These imports must FAIL during RED phase (= module doesn't exist yet)
from lib.plist_render import (
    validate_slot,
    render_plist,
    plist_digest,
    parse_loaded_plist_path,
    SlotValidationError,
    CANONICAL_ANICCA_HOME,
)


# ─── PROP-A4 / EDGE-E4: injection guard ───────────────────────────
class TestValidateSlot:
    @pytest.mark.parametrize("slot", ["gig", "clip", "x402_sell", "hl-trade", "a", "a-1_2"])
    def test_accepts_well_formed_slot(self, slot):
        assert validate_slot(slot) is None  # no raise

    @pytest.mark.parametrize("slot", [
        "gig; rm -rf /",
        "gig`whoami`",
        "$(echo hi)",
        "../etc/passwd",
        "gig/clip",
        "gig clip",
        "GIG",
        "gig.proactive",
        "",
        "a" * 33,  # > 32 chars
    ])
    def test_rejects_meta_or_empty_or_oversize(self, slot):
        with pytest.raises(SlotValidationError):
            validate_slot(slot)


# ─── PROP-A1, PROP-A2, PROP-A3: render template ────────────────────
class TestRenderPlist:
    def test_render_returns_xml_with_required_keys(self):
        out = render_plist(
            slot="gig",
            anicca_home=CANONICAL_ANICCA_HOME,
            log_dir="/tmp/life-manager/logs",
            plist_path="/home/life-manager/Library/LaunchAgents/ai.anicca.gig-proactive.plist",
        )
        # REQ-A2a: Label, StartInterval, RunAtLoad
        assert "<string>ai.anicca.gig-proactive</string>" in out
        assert "<key>StartInterval</key>" in out and "<integer>300</integer>" in out
        assert "<key>RunAtLoad</key>" in out and "<false/>" in out
        # REQ-A2: ProgramArguments
        assert "<string>/bin/bash</string>" in out
        assert f"<string>{CANONICAL_ANICCA_HOME}/skills/_shared/proactive-loop.sh</string>" in out
        assert "<string>gig</string>" in out
        # REQ-A3: literal absolute paths, NOT $HOME tokens
        assert "<string>/tmp/life-manager/logs/gig-proactive.out</string>" in out
        assert "<string>/tmp/life-manager/logs/gig-proactive.err</string>" in out

    def test_render_NEVER_emits_HOME_token(self):
        # PROP-A1: $HOME does not expand in launchd plists.
        out = render_plist(
            slot="gig",
            anicca_home=CANONICAL_ANICCA_HOME,
            log_dir="/tmp/life-manager/logs",
            plist_path="/home/life-manager/Library/LaunchAgents/ai.anicca.gig-proactive.plist",
        )
        assert "$HOME" not in out
        assert "${HOME}" not in out
        assert "~/" not in out

    def test_render_rejects_bad_slot_at_render_time(self):
        # Defense in depth — render also calls validate_slot
        with pytest.raises(SlotValidationError):
            render_plist(
                slot="gig; rm -rf /",
                anicca_home=CANONICAL_ANICCA_HOME,
                log_dir="/tmp/life-manager/logs",
                plist_path="/home/life-manager/Library/LaunchAgents/x.plist",
            )

    def test_render_is_deterministic_for_same_inputs(self):
        # PROP-B1: idempotent — same inputs → byte-identical output
        kwargs = dict(
            slot="clip",
            anicca_home=CANONICAL_ANICCA_HOME,
            log_dir="/tmp/life-manager/logs",
            plist_path="/home/life-manager/Library/LaunchAgents/ai.anicca.clip-proactive.plist",
        )
        assert render_plist(**kwargs) == render_plist(**kwargs)

    def test_render_differs_when_slot_differs(self):
        kwargs = dict(
            anicca_home=CANONICAL_ANICCA_HOME,
            log_dir="/tmp/life-manager/logs",
        )
        a = render_plist(slot="gig", plist_path="/x/a.plist", **kwargs)
        b = render_plist(slot="clip", plist_path="/x/b.plist", **kwargs)
        assert a != b


# ─── PROP-B1: plist_digest stable hash for idempotency ─────────────
class TestPlistDigest:
    def test_digest_same_for_identical_content(self):
        s = "<plist version=\"1.0\"><dict/></plist>"
        assert plist_digest(s) == plist_digest(s)

    def test_digest_changes_with_whitespace(self):
        # Idempotency check must catch byte-for-byte differences.
        a = "<plist><dict/></plist>"
        b = "<plist>\n  <dict/>\n</plist>"
        assert plist_digest(a) != plist_digest(b)

    def test_digest_is_hex(self):
        d = plist_digest("hello")
        assert all(c in "0123456789abcdef" for c in d)
        assert len(d) >= 16


# ─── PROP-E2: parse_loaded_plist_path() collision detector ─────────
class TestParseLoadedPlistPath:
    def test_extracts_path_from_launchctl_print(self):
        sample = """
ai.anicca.gig-proactive = {
	active count = 0
	path = /home/life-manager/Library/LaunchAgents/ai.anicca.gig-proactive.plist
	state = waiting
}
""".strip()
        assert parse_loaded_plist_path(sample) == \
            "/home/life-manager/Library/LaunchAgents/ai.anicca.gig-proactive.plist"

    def test_returns_none_when_no_path_line(self):
        sample = "ai.anicca.x = { active count = 0 }"
        assert parse_loaded_plist_path(sample) is None

    def test_handles_path_with_spaces(self):
        sample = "\tpath = /home/life-manager/My Folder/ai.anicca.gig-proactive.plist"
        assert parse_loaded_plist_path(sample) == \
            "/home/life-manager/My Folder/ai.anicca.gig-proactive.plist"

    def test_trims_trailing_whitespace(self):
        sample = "\tpath = /home/life-manager/x.plist   \n"
        assert parse_loaded_plist_path(sample) == "/home/life-manager/x.plist"


# ─── REQ-A2 pin: canonical anicca home constant ────────────────────
class TestCanonicalHome:
    def test_pin_is_anicca_oss_repo_not_products(self):
        assert CANONICAL_ANICCA_HOME == str(Path(__file__).resolve().parents[3])
