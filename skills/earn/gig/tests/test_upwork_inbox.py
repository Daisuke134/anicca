from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path

import pytest


PROVIDERS = Path(__file__).resolve().parents[1] / "scripts/providers"
if str(PROVIDERS) not in sys.path:
    sys.path.insert(0, str(PROVIDERS))
from upwork_inbox import append_changed_heads, normalize_observation, parse_terms  # noqa: E402


def _observation(text="Client: Can you deliver this by Friday?", **changes):
    value = {
        "kind": "message_room", "resource_id": "room-1",
        "resource_url": "https://www.upwork.com/ab/messages/rooms/room-1",
        "rendered_text": text, "source_evidence_sha256": "a" * 64,
        "observed_at": "2026-08-23T00:00:00+00:00",
    }
    value.update(changes)
    return normalize_observation(**value)


def test_same_room_head_is_appended_once_and_copy_stays_private(tmp_path):
    path = tmp_path / "private" / "inbox.jsonl"
    first = append_changed_heads(path, [_observation()])
    replay = append_changed_heads(path, [_observation()])
    assert (first["appended"], replay["appended"]) == (1, 0)
    assert first["heads"][0]["revision"] == replay["heads"][0]["revision"] == 1
    assert "Can you deliver" not in json.dumps(first)
    assert "Can you deliver" in path.read_text()
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700


def test_changed_head_creates_next_revision_but_old_duplicate_does_not(tmp_path):
    path = tmp_path / "inbox.jsonl"
    old = _observation()
    new = _observation("Client: Deadline changed to Monday.")
    assert append_changed_heads(path, [old])["heads"][0]["revision"] == 1
    assert append_changed_heads(path, [new])["heads"][0]["revision"] == 2
    assert append_changed_heads(path, [old])["appended"] == 0
    assert len(path.read_text().splitlines()) == 2


def test_room_local_clock_does_not_create_a_new_head():
    first = _observation("Client message 2:45 PM local time Final answer")
    later = _observation("Client message 2:49 PM local time Final answer")
    assert first["head_sha256"] == later["head_sha256"]
    assert first["rendered_text"] != later["rendered_text"]


def test_legacy_clock_hash_replays_zero_under_canonical_identity(tmp_path):
    path = tmp_path / "inbox.jsonl"
    legacy = _observation("Client message 2:45 PM local time Final answer")
    legacy["head_sha256"] = hashlib.sha256(legacy["rendered_text"].encode()).hexdigest()
    legacy["event_id"] = hashlib.sha256(
        f"upwork:inbox:v1:message_room:room-1:{legacy['head_sha256']}".encode()
    ).hexdigest()
    legacy["revision"] = 7
    path.write_text(json.dumps(legacy) + "\n")

    replay = append_changed_heads(
        path, [_observation("Client message 2:49 PM local time Final answer")],
    )
    assert replay["appended"] == 0
    assert replay["heads"][0]["revision"] == 7
    assert len(path.read_text().splitlines()) == 1


def test_offer_terms_normalize_money_fee_milestone_deadline_and_state():
    terms = parse_terms(
        "Accept offer Fixed price $1,200. Service fee 10%. "
        "Milestone 1 funded $600. Deadline 2026-09-15."
    )
    assert terms == {
        "amounts_usd_minor": [120000, 60000], "fee_bps": 1000,
        "milestones_usd_minor": [60000], "deadline": "2026-09-15",
        "contract_state": "offered",
    }


def test_stable_official_identity_is_mandatory():
    with pytest.raises(ValueError, match="upwork_inbox_identity_invalid"):
        _observation(resource_url="https://evil.example/room-1")
    with pytest.raises(ValueError, match="upwork_inbox_identity_invalid"):
        _observation(resource_url="https://www.upwork.com/ab/messages/rooms/other")


def test_room_binds_only_official_related_job_proposal_and_contract_ids():
    observation = normalize_observation(
        kind="message_room", resource_id="room-1",
        resource_url="https://www.upwork.com/ab/messages/rooms/room-1",
        rendered_text="Client message", source_evidence_sha256="a" * 64,
        observed_at="now", rendered_links=[
            {"href": "https://www.upwork.com/jobs/API-task_~0123/"},
            {"href": "https://www.upwork.com/ab/proposals/proposal-9"},
            {"href": "https://www.upwork.com/ab/w/workroom/contract-7"},
            {"href": "https://evil.example/jobs/~fake"},
        ],
    )
    assert observation["related_ids"] == {
        "job_ids": ["~0123"], "proposal_ids": ["proposal-9"],
        "contract_ids": ["contract-7"],
    }


def test_empty_inventory_creates_no_ledger(tmp_path):
    path = tmp_path / "inbox.jsonl"
    assert append_changed_heads(path, []) == {"observed": 0, "appended": 0, "heads": []}
    assert not path.exists()
