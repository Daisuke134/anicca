"""A dead Coconala session must heal itself, for all four gig lanes at once.

Measured 2026-09-01..07: the session expired, `keepalive` detected it correctly on every one of 159
ticks, and nothing could act on it — `keepalive` only extends a session that is still alive, and the
only re-login path in this file was `relogin_x`. Coconala applied to nothing for five days.

Apply, Paid, Storefront and Reply all share one browser (`coconala:kosuke`) and one session, so a
single re-login restores all four.

Run: python3 -m pytest skills/browser/tests/test_coconala_relogin.py
"""

import ast
from pathlib import Path

import pytest

VAULT = Path(__file__).resolve().parents[1] / "scripts" / "session_vault.py"
TICK = Path(__file__).resolve().parents[1] / "scripts" / "session_vault_tick.sh"
SOURCE = VAULT.read_text(encoding="utf-8")
TICK_SOURCE = TICK.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
FUNCS = {n.name for n in ast.walk(TREE) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def test_coconala_has_a_relogin_path_at_all():
    """Before this, only x.com did -- which is why five days of correct alarms changed nothing."""
    assert "relogin_coconala" in FUNCS
    assert "_relogin_coconala" in FUNCS


def test_it_is_reachable_from_the_command_line():
    assert '"relogin_coconala": relogin_coconala' in SOURCE


@pytest.mark.parametrize("marker", [
    "COCONALA_RELOGIN_MARKER",
    "RELOGIN_COOLDOWN_SEC",
])
def test_it_is_rate_limited_like_the_x_path(marker):
    """Repeated automated logins get accounts flagged; the marker is written before the attempt."""
    body = SOURCE.split("def relogin_coconala():", 1)[1].split("def relogin_x():", 1)[0]
    assert marker in body


def test_the_cooldown_marker_is_written_before_the_attempt():
    body = SOURCE.split("def relogin_coconala():", 1)[1].split("def relogin_x():", 1)[0]
    assert body.index("handle.write(str(now))") < body.index("_relogin_coconala()")


def test_success_is_proven_on_a_page_only_a_logged_in_account_renders():
    """Coconala sends anonymous users to the top page, so 'not /login' is not proof of login."""
    body = SOURCE.split("async def _relogin_coconala", 1)[1].split("def relogin_coconala", 1)[0]
    assert "/mypage/dashboard" in body
    assert '"/mypage/dashboard" in url' in body


def test_a_successful_relogin_is_banked_immediately():
    """The lanes seed from the vault, not from this tab: a login that is not dumped is invisible."""
    body = SOURCE.split("def relogin_coconala():", 1)[1].split("def relogin_x():", 1)[0]
    assert 'result["dump"] = dump()' in body


def test_the_tick_heals_instead_of_only_alerting():
    gig = TICK_SOURCE.split("gig browser (coconala:kosuke)", 1)[1].split("per-account clip browsers", 1)[0]
    assert "relogin_coconala" in gig
    assert gig.index("ALERT: gig browser session dead") < gig.index("relogin_coconala")


def test_the_tick_reports_both_outcomes():
    gig = TICK_SOURCE.split("gig browser (coconala:kosuke)", 1)[1].split("per-account clip browsers", 1)[0]
    assert "logged back in automatically" in gig
    assert "automatic relogin did not restore it" in gig
