from __future__ import annotations

import sys
import json
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
PROVIDERS = SCRIPTS / "providers"
for directory in (SCRIPTS, PROVIDERS):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from upwork_browser_provider import (  # noqa: E402
    load_candidates,
    parse_candidate,
    parse_catalog,
    parse_connects,
    parse_contracts,
    parse_inventory,
    parse_messages,
    parse_stable_entities,
    reconcile_terminal_transitions,
)


def test_parses_zero_connects_without_inventing_a_reward():
    state = parse_connects(
        "Connects History\nMy balance\n0 Connects\nNo Connects transactions.\n"
    )
    assert state == {"balance": 0, "transactions_empty": True}


def test_parses_complete_zero_effect_inventory_and_account_task():
    state = parse_inventory(
        "Offers  (0)\nInvites from clients (0)\n0 connects to apply to these jobs\n"
        "Active proposals  (0)\nSubmitted proposals  (0)\n"
        "To do: Take the working style assessment.\n"
    )
    assert state == {
        "offers": 0,
        "invites": 0,
        "active_proposals": 0,
        "submitted_proposals": 0,
        "account_tasks": ["working_style_assessment"],
    }


def test_parses_visible_catalog_inventory_without_inventing_an_order():
    state = parse_catalog(
        "Approved (1)\nUnder Review (0)\nDrafts (0)\n"
        "Views (30 days)\nOrders\nVisible\n"
        "You will get a Python script integrating one documented REST API endpoint\n"
        "0\n0\nMore Project Options\n"
    )
    assert state == {
        "catalog_approved": 1,
        "catalog_under_review": 0,
        "catalog_drafts": 0,
        "catalog_projects": [{
            "title": "You will get a Python script integrating one documented REST API endpoint",
            "visible": True,
            "views_30d": 0,
            "orders": 0,
        }],
    }


def test_parses_zero_contract_and_message_effects_from_official_empty_states():
    assert parse_contracts(
        "Earnings available now: $0.00\nActive contracts\n"
        "There are no active contracts.\n",
        [],
    ) == {"earnings_available_usd_minor": 0, "active_contracts": []}
    assert parse_messages(
        "Messages\nUnread\nFavorites\nConversations will appear here\n",
        [],
    ) == {"message_rooms": [], "unread_message_room_ids": []}


def test_extracts_stable_official_ids_instead_of_titles():
    state = parse_stable_entities(
        invite_links=[{
            "href": "https://www.upwork.com/jobs/python-task-~012ABC",
            "text": "Python task", "context": "Client invited you to apply",
        }],
        proposal_links=[
            {
                "href": "https://www.upwork.com/ab/proposals/offer-77",
                "text": "Offer", "context": "Offers Active offer",
            },
            {
                "href": "https://www.upwork.com/ab/proposals/active-88",
                "text": "Python API", "context": "Active proposals",
            },
            {
                "href": "https://www.upwork.com/ab/proposals/submitted-99",
                "text": "iOS fix", "context": "Submitted proposals",
            },
        ],
    )
    assert state["invitation_entities"][0]["id"] == "~012ABC"
    assert state["proposal_offer_entities"][0]["id"] == "offer-77"
    assert state["active_proposal_entities"][0]["id"] == "active-88"
    assert state["submitted_proposal_entities"][0]["id"] == "submitted-99"


def test_classifies_candidate_only_from_official_job_markers():
    candidate = {"job_id": "~01", "job_url": "https://www.upwork.com/jobs/~01"}
    opened = parse_candidate(
        candidate,
        "Job title\nSend a proposal for: 7 Connects\nAvailable Connects: 0\n",
        "a" * 64,
    )
    assert (opened["status"], opened["connects_required"]) == ("open", 7)
    parked = parse_candidate(
        candidate,
        "Required Connects to submit a proposal: 26\nAvailable Connects: 0\n",
        "e" * 64,
    )
    assert (parked["status"], parked["connects_required"]) == ("open", 26)
    assert parse_candidate(
        candidate, "This job is no longer available.\nHired: 1\n", "b" * 64,
    )["status"] == "closed"
    assert parse_candidate(
        candidate, "This job has been removed from Upwork.", "c" * 64,
    )["status"] == "removed"
    assert parse_candidate(candidate, "Job detail loading", "d" * 64)["status"] == "unknown"


def test_public_candidate_config_has_unique_exact_ids():
    path = SCRIPTS.parent / "config" / "upwork-candidates.public.json"
    candidates = load_candidates(path)
    assert len(candidates) == 3
    assert len({item["job_id"] for item in candidates}) == 3
    assert all(item["job_id"] in item["job_url"] for item in candidates)


def test_terminal_transition_is_fsynced_once_and_replay_is_zero(tmp_path):
    output = tmp_path / "state.json"
    ledger = tmp_path / "transitions.jsonl"
    previous = {
        "observed_at": "2026-08-22T00:00:00+00:00",
        "candidate_jobs": [{
            "job_id": "~01", "status": "closed", "evidence_sha256": "a" * 64,
        }],
    }
    output.write_text(json.dumps(previous), encoding="utf-8")
    current = {
        "observed_at": "2026-08-22T00:05:00+00:00",
        "candidate_jobs": [{
            "job_id": "~01", "status": "closed",
            "official_marker": "no_longer_available", "evidence_sha256": "b" * 64,
        }],
    }
    first = reconcile_terminal_transitions(output, ledger, current)
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert first["terminal_transitions_appended"] == 1
    assert rows[0]["from_status"] == "legacy_observed"
    assert rows[0]["to_status"] == "closed"
    assert rows[0]["official_reason"] == "no_longer_available"
    first_size = ledger.stat().st_size

    replay = reconcile_terminal_transitions(output, ledger, current)
    assert replay["terminal_transitions_appended"] == 0
    assert ledger.stat().st_size == first_size
    assert ledger.stat().st_mode & 0o777 == 0o600


def test_reopen_then_remove_creates_a_distinct_terminal_transition(tmp_path):
    output, ledger = tmp_path / "state.json", tmp_path / "transitions.jsonl"
    opened = {
        "observed_at": "2026-08-22T00:10:00+00:00",
        "candidate_jobs": [{
            "job_id": "~01", "status": "open", "evidence_sha256": "c" * 64,
        }],
    }
    reconcile_terminal_transitions(output, ledger, opened)
    removed = {
        "observed_at": "2026-08-22T00:15:00+00:00",
        "candidate_jobs": [{
            "job_id": "~01", "status": "removed",
            "official_marker": "removed", "evidence_sha256": "d" * 64,
        }],
    }
    result = reconcile_terminal_transitions(output, ledger, removed)
    assert result["terminal_transitions_appended"] == 1
    row = json.loads(ledger.read_text().splitlines()[-1])
    assert (row["from_status"], row["to_status"]) == ("open", "removed")


@pytest.mark.parametrize("parser,text", [
    (parse_connects, "Connects History unavailable"),
    (parse_inventory, "Proposals and Offers loading"),
    (parse_catalog, "Create and manage your services\nProjects loading"),
])
def test_partial_provider_pages_fail_closed(parser, text):
    with pytest.raises(ValueError, match="upwork_readback_incomplete"):
        parser(text)


def test_launchd_job_is_zero_spend_and_runs_every_five_minutes():
    manifest = json.loads((SCRIPTS.parent / "config" / "launchd-jobs.json").read_text())
    job = next(item for item in manifest["jobs"] if item["lane"] == "upwork-free")
    command = " ".join(job["program"]).lower()
    assert job["StartInterval"] == 300
    assert "upwork_browser_provider.py" in command
    assert "upwork-candidates.public.json" in command
    assert "upwork-free-transitions.jsonl" in command
    assert all(term not in command for term in ("buy", "billing", "plus", "boost"))
