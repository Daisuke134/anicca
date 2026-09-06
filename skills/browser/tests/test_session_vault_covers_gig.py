"""The keepalive must warm the browser the gig lanes actually use.

Measured 2026-09-07: `/mypage` and `/offers/add/<id>` both redirected to Coconala's top page on the
gig browser while :9222 stayed logged in. The keepalive only ever warmed :9222, so it reported
healthy for four days while Coconala applied to nothing. :9222 and the gig browser were once one
process behind a proxy, so warming one warmed both; when they were split, nothing extended this
roster.

The lane itself said what was wrong on every listing -- 「公式ページで募集受付中の応募フォームを
確認できなかったためです」-- but nothing tied that sentence to the session.

Run: python3 -m pytest skills/browser/tests/test_session_vault_covers_gig.py
"""

from pathlib import Path

import pytest

TICK = Path(__file__).resolve().parents[1] / "scripts" / "session_vault_tick.sh"
SOURCE = TICK.read_text(encoding="utf-8")


def test_the_gig_browser_is_warmed_at_all():
    assert "coconala:kosuke" in SOURCE, (
        "the gig lanes work in their own browser; warming only :9222 leaves that session to rot"
    )


def test_it_warms_the_leased_port_not_a_hardcoded_one():
    """browser-guard owns the port. Hardcoding one is how :9222 and the gig browser drifted apart."""
    gig = SOURCE.split("gig browser (coconala:kosuke)", 1)[1]
    assert 'SESSION_VAULT_PORT="$GIG_PORT"' in gig
    assert ":9223" not in gig.split("per-account clip browsers", 1)[0].replace("(coconala:kosuke :9223", "")


def test_it_takes_the_lease_and_gives_it_back():
    gig = SOURCE.split("gig browser (coconala:kosuke)", 1)[1].split("per-account clip browsers", 1)[0]
    assert "acquire coconala:kosuke" in gig
    assert "release coconala:kosuke" in gig


def test_a_busy_lease_is_skipped_rather_than_forced():
    """BUSY means a gig lane is driving that browser, which is itself traffic."""
    gig = SOURCE.split("gig browser (coconala:kosuke)", 1)[1].split("per-account clip browsers", 1)[0]
    assert "BUSY" in gig and "skipping" in gig


def test_a_dead_gig_session_alerts_and_says_what_it_costs():
    gig = SOURCE.split("gig browser (coconala:kosuke)", 1)[1].split("per-account clip browsers", 1)[0]
    assert "telegram_notify" in gig
    assert "GIG browser" in gig
    assert "every Coconala application stops" in gig


@pytest.mark.parametrize("url", ["https://coconala.com/mypage/dashboard"])
def test_it_checks_a_page_that_requires_login(url):
    """A public page cannot tell logged in from logged out: Coconala sends anonymous users to /."""
    gig = SOURCE.split("gig browser (coconala:kosuke)", 1)[1].split("per-account clip browsers", 1)[0]
    assert url in gig
