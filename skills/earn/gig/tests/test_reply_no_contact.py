import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "gig_reply_no_contact_test", ROOT / "scripts/reply_detector.py",
)
assert SPEC and SPEC.loader
detector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(detector)


class FakeOutbox:
    def __init__(self):
        self.actions = {}
        self.closed = []

    def enqueue(self, *, event_key, thread_id, thread_url, observed_at):
        action = {
            "action_id": len(self.actions) + 1, "event_key": event_key,
            "thread_id": thread_id, "thread_url": thread_url, "state": "pending",
        }
        self.actions[action["action_id"]] = action
        return action

    def get_action(self, action_id):
        return self.actions[action_id]

    def claim(self, *, owner, now, lease_seconds, action_id):
        action = self.actions[action_id]
        return {**action, "owner": owner, "fencing_token": 1}

    def close_nothing_to_say(self, action_id, *, owner, fencing_token, reason, now):
        self.closed.append({
            "action_id": action_id, "owner": owner,
            "fencing_token": fencing_token, "reason": reason, "now": now,
        })


def _registry(tmp_path):
    path = tmp_path / "no-contact.json"
    path.write_text(json.dumps({
        "version": 1,
        "entries": [{
            "policy_id": "operator-owned-1",
            "counterparty_user_id": "12345",
            "thread_path": "/mypage/direct_message/90001",
        }],
    }), encoding="utf-8")
    return path


def test_head_policy_creates_identity_then_closes_before_semantic_work(tmp_path):
    outbox = FakeOutbox()
    result = detector.partition_no_contact_rows([
        {
            "talkroom_id": "90001",
            "talkroom_url": "https://coconala.com/mypage/direct_message/90001",
            "counterparty_name": "must-not-leak",
            "last_message_identity_sha256": "a" * 64,
        },
        {
            "talkroom_id": "90002",
            "talkroom_url": "https://coconala.com/mypage/direct_message/90002",
            "last_message_identity_sha256": "b" * 64,
        },
    ], registry_path=_registry(tmp_path), outbox=outbox, now=1000)
    assert [row["talkroom_id"] for row in result["available"]] == ["90002"]
    assert result["ignored"] == [{
        "status": "ignore_policy", "policy_id": "operator-owned-1", "action_id": 1,
    }]
    assert outbox.closed[0]["reason"] == "ignore_policy:operator-owned-1"
    assert "must-not-leak" not in json.dumps(result)


def test_effect_fence_closes_stale_queued_action_without_calling_worker(tmp_path):
    outbox = FakeOutbox()
    action = outbox.enqueue(
        event_key="coconala:inbox:v1:90001:sha256_v1:" + "a" * 64,
        thread_id="90001",
        thread_url="https://coconala.com/mypage/direct_message/90001",
        observed_at=1000,
    )
    result = detector.close_no_contact_work(
        {"action_id": action["action_id"], "thread_id": "90001"},
        registry_path=_registry(tmp_path), outbox=outbox, now=1001,
    )
    assert result["status"] == "ignore_policy"
    assert len(outbox.closed) == 1
