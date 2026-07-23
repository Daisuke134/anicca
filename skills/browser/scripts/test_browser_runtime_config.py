"""Configuration seams required for one persistent browser per business loop."""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cdp_context_lease as lease  # noqa: E402


def test_context_lease_uses_loop_specific_cdp_and_state(monkeypatch, tmp_path):
    monkeypatch.setenv("CLOAK_CDP_BASE_URL", "http://127.0.0.1:9223")
    monkeypatch.setenv(
        "CLOAK_CONTEXT_LEASES_FILE", str(tmp_path / "gig-leases.json")
    )
    monkeypatch.setenv(
        "CLOAK_SESSION_VAULT_FILE", str(tmp_path / "gig-auth-state.json")
    )

    assert lease._cdp_base() == "http://127.0.0.1:9223"
    assert lease._leases_path() == str(tmp_path / "gig-leases.json")
    assert lease._vault_path() == str(tmp_path / "gig-auth-state.json")
    assert lease._page_ws("target-1") == (
        "ws://127.0.0.1:9223/devtools/page/target-1"
    )


def test_browser_guard_passes_owner_to_recovery_gc():
    source = (
        Path(__file__).resolve().parents[1] / "ensure_browser.sh"
    ).read_text(encoding="utf-8")

    assert 'CDP="${CLOAK_CDP_BASE_URL:-http://127.0.0.1:9222}"' in source
    assert 'cdp_tab_gc.py" --owner "$CLOAK_BROWSER_OWNER"' in source
