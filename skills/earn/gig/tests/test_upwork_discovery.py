"""Fixture contracts for bounded, read-only Upwork job discovery."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


GIG_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = GIG_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
MODULE = SCRIPTS / "providers" / "upwork_adapter.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("gig_upwork_adapter_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


adapter_module = _load_module() if MODULE.is_file() else None
OBSERVED = "2026-08-22T10:00:00+00:00"


def _job(job_id: str = "~0123456789012345678", **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "id": job_id,
        "url": f"https://www.upwork.com/jobs/Test-job_{job_id}/",
        "title": "Build a bounded Python adapter",
        "description": "Implement discovery, validation, and an evidence-backed handoff.",
        "skills": [{"name": "Python"}, {"name": "GraphQL"}],
        "amount": {"rawValue": 750, "currency": "USD"},
        "hourlyBudgetMin": None,
        "hourlyBudgetMax": None,
        "client": {
            "verificationStatus": "VERIFIED",
            "totalSpent": {"rawValue": 125000, "currency": "USD"},
            "totalHires": 31, "totalPostedJobs": 44, "totalReviews": 27,
            "totalFeedback": 4.9,
        },
        "activity": {
            "totalApplicants": 9, "interviewing": 2, "invitesSent": 1,
            "lastClientActivity": "2026-08-22T09:55:00+00:00",
        },
        "connects": 12,
        "jobStatus": "OPEN",
    }
    value.update(overrides)
    return value


def _page(jobs: list[dict[str, object]], *, cursor: str | None = None, more: bool = False):
    return {
        "observedAt": OBSERVED,
        "edges": [{"cursor": f"edge-{i}", "node": job} for i, job in enumerate(jobs)],
        "pageInfo": {"endCursor": cursor, "hasNextPage": more},
    }


class Selector:
    def __init__(self):
        self.actions: list[str] = []

    def for_action(self, action: str):
        self.actions.append(action)
        return type("Selection", (), {"mode": "official_api"})()


def _adapter(pages: dict[str | None, dict[str, object]], *, details=None, **kwargs):
    selector = Selector()
    reads: list[tuple[str, str | None, int]] = []

    def read_page(selection, query, cursor, limit):
        reads.append((selection.mode, cursor, limit))
        return pages[cursor]

    def read_detail(selection, job_id):
        return (details or {})[job_id]

    return adapter_module.UpworkAdapter(
        selector, read_page, read_detail, query="python", **kwargs,
    ), selector, reads


def test_discover_requires_and_preserves_complete_commercial_evidence():
    assert adapter_module is not None, "UpworkAdapter is not implemented"
    job = _job()
    adapter, selector, reads = _adapter({None: _page([job])})

    [found] = adapter.discover()

    assert found.opportunity_id == job["id"]
    assert found.source_url == job["url"]
    assert found.title == job["title"]
    assert found.scope == job["description"]
    assert found.skills == ("Python", "GraphQL")
    assert (found.currency, found.pricing_kind) == ("USD", "fixed")
    assert (found.minimum_minor, found.maximum_minor) == (75_000, 75_000)
    assert dict(found.client_evidence) == {
        "payment_verified": True, "total_spent_minor": 12_500_000,
        "total_hires": 31, "jobs_posted": 44, "reviews": 27, "rating": 4.9,
    }
    assert dict(found.activity)["applicants"] == 9
    assert found.connects_cost == 12
    assert found.observed_at == OBSERVED
    assert selector.actions == ["search"]
    assert reads == [("official_api", None, 20)]


def test_hourly_budget_and_bounded_cursor_pagination_are_canonical():
    first = _job()
    second = _job(
        "~0123456789012345679", amount=None,
        hourlyBudgetMin={"rawValue": 25, "currency": "USD"},
        hourlyBudgetMax={"rawValue": 40, "currency": "USD"},
    )
    adapter, _, reads = _adapter({
        None: _page([first], cursor="next-1", more=True),
        "next-1": _page([second]),
    }, page_size=1, max_pages=2)

    found = adapter.discover()

    assert [job.opportunity_id for job in found] == [first["id"], second["id"]]
    assert (found[1].pricing_kind, found[1].minimum_minor, found[1].maximum_minor) == (
        "hourly", 2_500, 4_000,
    )
    assert reads == [("official_api", None, 1), ("official_api", "next-1", 1)]


@pytest.mark.parametrize(
    "bad_job,reason",
    [
        ({key: value for key, value in _job().items() if key != "description"}, "partial_job"),
        (_job(jobStatus="DELETED"), "job_not_open"),
        (_job(amount={"rawValue": 750, "currency": "EUR"}), "unsupported_currency"),
        (_job(url="https://evil.invalid/jobs/0123456789012345678"), "invalid_job_url"),
    ],
)
def test_partial_deleted_stale_or_unsupported_jobs_are_rejected(bad_job, reason):
    adapter, _, _ = _adapter({None: _page([bad_job])})
    with pytest.raises(adapter_module.DiscoveryContractError, match=reason):
        adapter.discover()


def test_repeated_or_unbounded_cursor_is_rejected_instead_of_looping():
    pages = {None: _page([_job()], cursor="same", more=True)}
    pages["same"] = _page([_job("~0123456789012345679")], cursor="same", more=True)
    adapter, _, _ = _adapter(pages, page_size=1, max_pages=3)
    with pytest.raises(adapter_module.DiscoveryContractError, match="cursor_not_advancing"):
        adapter.discover()


@pytest.mark.parametrize(
    "override,reason",
    [
        ({"client": {**_job()["client"], "totalFeedback": "excellent"}}, "invalid_client_evidence"),
        ({"activity": {**_job()["activity"], "lastClientActivity": "yesterday"}}, "invalid_activity"),
    ],
)
def test_client_and_activity_evidence_must_be_typed(override, reason):
    adapter, _, _ = _adapter({None: _page([_job(**override)])})
    with pytest.raises(adapter_module.DiscoveryContractError, match=reason):
        adapter.discover()


def test_inspect_rejects_stale_identity_and_returns_current_canonical_detail():
    wanted = _job()
    adapter, selector, _ = _adapter(
        {None: _page([])}, details={wanted["id"]: {"observedAt": OBSERVED, "job": wanted}},
    )
    detail = adapter.inspect(wanted["id"])
    assert detail.opportunity.opportunity_id == wanted["id"]
    assert detail.scope == wanted["description"]
    assert selector.actions == ["inspect"]

    stale = _job("~0123456789012345679")
    bad, _, _ = _adapter(
        {None: _page([])}, details={wanted["id"]: {"observedAt": OBSERVED, "job": stale}},
    )
    with pytest.raises(adapter_module.DiscoveryContractError, match="stale_job_identity"):
        bad.inspect(wanted["id"])


def test_discovery_is_stable_and_has_no_proposal_or_message_effects():
    pages = {None: _page([_job()])}
    adapter, selector, _ = _adapter(pages)
    first = adapter.discover()
    second = adapter.discover()
    assert first == second
    assert selector.actions == ["search", "search"]
