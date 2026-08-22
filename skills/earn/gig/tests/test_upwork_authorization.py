"""Public Upwork action matrix and private receipt boundary tests."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


GIG_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = GIG_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from provider_authorization import AuthorizationState, authorize


MATRIX = GIG_ROOT / "config" / "upwork-actions.public.json"
EXPECTED_ACTIONS = {
    "search", "inspect", "propose", "message", "accept_offer",
    "deliver_milestone", "read_payments", "read_payouts",
}
EXPECTED_SOURCES = dict((
    ("automation_policy", "9e1b0b9465587bd319ff1ddd644b2954dd382d95164db01e536bac8b058e7ba5"),
    ("api_" + "scopes", "a2a6f529fb2ac4aa7b781c27966e6c7baa7874d3614854b35b741b16d897e186"),
    ("graphql_schema", "ddb2a4fa8adde8ead2a1707594e51d90276c028ab286d7a727d68413ad5c776f"),
    ("terms", "956c737f4360bcb2372b49a3ef0af358547a5443be6b9db652758a310d6a3dce"),
))


def _matrix() -> dict:
    return json.loads(MATRIX.read_text(encoding="utf-8"))


def test_public_matrix_declares_exact_actions_with_safe_unknown_default():
    matrix = _matrix()

    assert matrix["provider"] == "upwork"
    assert matrix["default_state"] == "unknown"
    assert set(matrix["actions"]) == EXPECTED_ACTIONS
    for action in matrix["actions"].values():
        assert action == {
            "state": "unknown",
            "candidate_transports": ["official_api", "cloak_browser"],
            "evidence_sources": [
                "automation_policy", "api_scopes", "graphql_schema", "terms",
            ],
        }
    assert "delete_account" not in matrix["actions"]


def test_evidence_is_official_https_and_bound_to_retrieved_content_hashes():
    sources = _matrix()["sources"]

    assert {source["id"] for source in sources} == set(EXPECTED_SOURCES)
    for source in sources:
        assert source["url"].startswith(("https://support.upwork.com/", "https://www.upwork.com/"))
        assert source["retrieved_sha256"] == EXPECTED_SOURCES[source["id"]]
        assert source["retrieved_at"] == "2026-08-22T00:00:00+00:00"


def _write_receipts(path: Path, *, account: str = "owner@example.test") -> None:
    receipts = []
    for action in sorted(EXPECTED_ACTIONS):
        receipts.append({
            "provider": "upwork",
            "account": account,
            "action": action,
            "transport": "cloak_browser",
            "state": "approved_browser",
            "jurisdiction": "JP",
            "terms_version": "special-approval-v1",
            "evidence_hash": "a" * 64,
            "issued_at": "2026-08-22T00:00:00+00:00",
            "expires_at": "2026-09-22T00:00:00+00:00",
        })
    path.write_text(json.dumps({"version": 1, "receipts": receipts}), encoding="utf-8")
    path.chmod(0o600)


def test_private_receipt_authorizes_only_exact_account_action_and_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    store = tmp_path / "authorizations.json"
    _write_receipts(store)
    monkeypatch.setenv("GIG_AUTHORIZATION_PATH", str(store))
    now = datetime(2026, 8, 23, tzinfo=timezone.utc)

    approved = authorize("upwork", "owner@example.test", "propose", "cloak_browser", now)
    assert approved.state is AuthorizationState.APPROVED_BROWSER
    assert approved.receipt_hash is not None
    assert authorize(
        "upwork", "other@example.test", "propose", "cloak_browser", now
    ).state is AuthorizationState.UNKNOWN
    assert authorize(
        "upwork", "owner@example.test", "delete_account", "cloak_browser", now
    ).state is AuthorizationState.UNKNOWN
    assert authorize(
        "upwork", "owner@example.test", "propose", "official_api", now
    ).state is AuthorizationState.UNKNOWN


def test_expired_private_receipt_returns_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    store = tmp_path / "authorizations.json"
    _write_receipts(store)
    monkeypatch.setenv("GIG_AUTHORIZATION_PATH", str(store))

    decision = authorize(
        "upwork", "owner@example.test", "propose", "cloak_browser",
        datetime(2026, 9, 22, tzinfo=timezone.utc),
    )

    assert decision.state is AuthorizationState.UNKNOWN
    assert decision.reason == "matching_receipt_expired"
