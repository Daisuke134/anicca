from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


PROVIDERS = Path(__file__).resolve().parents[1] / "scripts/providers"
if str(PROVIDERS) not in sys.path:
    sys.path.insert(0, str(PROVIDERS))
import upwork_negotiate as negotiate  # noqa: E402


def _head():
    return {
        "kind": "message_room",
        "resource_id": "room-1", "resource_url": "https://www.upwork.com/ab/messages/rooms/room-1",
        "event_id": "a" * 64, "head_sha256": "b" * 64, "revision": 2,
        "observed_at": "2026-08-23T00:00:00+00:00", "rendered_text": "Client needs API work",
    }


def _capacity(available=True):
    return {"active_contract_count": 0 if available else 3, "concurrent_job_cap": 3,
            "capacity_available": available, "minimum_margin_bps": 2500}


def _decision(action="accept_terms"):
    head = _head()
    return {
        "decision": action, "reason_codes": [],
        "source": {"room_id": head["resource_id"], "room_url": head["resource_url"],
                   "event_id": head["event_id"], "head_sha256": head["head_sha256"], "revision": 2},
        "message": {"body": "I can deliver this exact API scope by the agreed deadline.",
                    "scope": "Integrate one documented REST API endpoint.", "price_usd": 100,
                    "expected_cost_usd": 50, "margin_bps": 5000, "deadline": "2026-09-01"},
    }


def test_exact_current_head_capacity_and_margin_seal_intent():
    result = negotiate.validate_decision(_decision(), _head(), _capacity())
    assert len(result["intent_sha256"]) == 64


@pytest.mark.parametrize("mutate,error", [
    (("source", "head_sha256", "c" * 64), "source_mismatch"),
    (("message", "margin_bps", 2500), "economics_invalid"),
    (("message", "deadline", "2026-01-01"), "deadline_invalid"),
])
def test_stale_identity_wrong_economics_or_expired_deadline_rejected(mutate, error):
    decision = _decision()
    decision[mutate[0]][mutate[1]] = mutate[2]
    with pytest.raises(ValueError, match=error):
        negotiate.validate_decision(decision, _head(), _capacity())


def test_capacity_race_rejects_accept_and_counter():
    with pytest.raises(ValueError, match="economics_invalid"):
        negotiate.validate_decision(_decision(), _head(), _capacity(False))


def test_near_duplicate_reply_is_rejected():
    decision = _decision()
    with pytest.raises(ValueError, match="near_duplicate"):
        negotiate.validate_decision(decision, _head(), _capacity(), [decision["message"]["body"] + " "])


def test_no_reply_requires_reason_and_has_no_message():
    decision = _decision("no_reply")
    decision["reason_codes"] = ["owner_is_latest_sender"]
    decision["message"] = None
    assert negotiate.validate_decision(decision, _head(), _capacity())["decision"] == "no_reply"


def test_latest_private_room_revision_is_selected(tmp_path):
    path = tmp_path / "inbox.jsonl"
    older, latest = _head(), {**_head(), "revision": 3, "event_id": "d" * 64, "head_sha256": "e" * 64}
    path.write_text(json.dumps(older) + "\n" + json.dumps(latest) + "\n")
    path.chmod(0o600)
    assert negotiate.latest_room_head(path, "room-1")["revision"] == 3


def test_sealed_intent_is_private_immutable_and_supplies_duplicate_history(tmp_path):
    root = tmp_path / "intents"
    intent = negotiate.validate_decision(_decision(), _head(), _capacity())
    path = negotiate.write_intent(intent, root)
    assert root.stat().st_mode & 0o777 == 0o700
    assert path.stat().st_mode & 0o777 == 0o600
    assert negotiate.previous_bodies(root) == [intent["message"]["body"]]
    assert negotiate.existing_intent(_head(), _capacity(), root) == intent
    changed = {**intent, "reason_codes": ["changed"]}
    with pytest.raises(ValueError, match="immutable"):
        negotiate.write_intent(changed, root)
