"""APPLY-REPORT-3: no Apply lane may reach for a binary a cloned repository does not have.

The Apply reporters used to exec an external CLI at an absolute Homebrew path. That is two defects
at once: a stranger who clones this repository has no such binary, and launchd gives a job no PATH,
so the exec fails as `process_not_started` while the lane exits 0 — which is how CrowdWorks
reported nothing for a full day. Both were fixed by hand; this file is what stops them returning.

An allow-list of files rather than a repository-wide scan: the Paid and Storefront lanes still hold
their own copies (`PAID-REPORT-1`, `STOREFRONT-REPORT-1`) and belong to other owners who are
editing them right now. Add their files here as those atoms close.

Run: python3 -m pytest skills/_shared/marketplace-core/tests/test_apply_transport_portability.py
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]

# The Apply reporting path of each marketplace: what decides a message and what sends it.
APPLY_SOURCES = (
    "skills/earn/gig/scripts/apply_telegram_report.py",
    "skills/earn/gig/scripts/application_direct.py",
    "skills/earn/lancers/scripts/application_tick.py",
    "skills/earn/lancers/scripts/telegram_report.py",
    "skills/earn/crowdworks/scripts/account.py",
    "skills/earn/crowdworks/scripts/application_tick.py",
    "skills/earn/crowdworks/scripts/telegram_report.py",
)

# A cloned repository has none of these. Each one is a lane that cannot run outside this Mac.
FORBIDDEN = ("openclaw", "/opt/homebrew", "/usr/local/bin/")


def openclaw_dependency_record() -> dict:
    """The same shape earn/marketing-engine/intel/verify_gate9.py records, for the Apply lanes."""
    offenders = {
        source: [term for term in FORBIDDEN if term in _read(source).lower()]
        for source in APPLY_SOURCES
    }
    offenders = {source: terms for source, terms in offenders.items() if terms}
    return {
        "checked_sources": len(APPLY_SOURCES),
        "openclaw_dependency": bool(offenders),
        "offenders": offenders,
    }


def _read(relative: str) -> str:
    path = REPO_ROOT / relative
    assert path.is_file(), f"{relative} is on the allow-list but does not exist"
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("source", APPLY_SOURCES)
def test_apply_source_has_no_external_binary_dependency(source):
    text = _read(source).lower()
    found = [term for term in FORBIDDEN if term in text]
    assert not found, (
        f"{source} reaches for {found}. A cloned repository does not have it, and launchd gives "
        f"a job no PATH. Send through skills/_shared/marketplace-core/scripts/telegram_delivery.py."
    )


def test_every_allow_listed_source_still_exists():
    """A renamed file must not silently drop out of the gate."""
    missing = [s for s in APPLY_SOURCES if not (REPO_ROOT / s).is_file()]
    assert not missing, f"allow-listed Apply sources are gone: {missing}"


def test_dependency_record_is_clean():
    record = openclaw_dependency_record()
    assert record == {
        "checked_sources": len(APPLY_SOURCES),
        "openclaw_dependency": False,
        "offenders": {},
    }
