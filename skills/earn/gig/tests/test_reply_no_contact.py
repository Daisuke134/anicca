import asyncio
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "gig_reply_no_contact_test", ROOT / "scripts/reply_detector.py",
)
assert SPEC and SPEC.loader
detector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(detector)
OUTBOX_SPEC = importlib.util.spec_from_file_location(
    "gig_no_contact_real_outbox_test", ROOT / "scripts/connector_outbox.py",
)
assert OUTBOX_SPEC and OUTBOX_SPEC.loader
connector = importlib.util.module_from_spec(OUTBOX_SPEC)
OUTBOX_SPEC.loader.exec_module(connector)
TELEGRAM_SPEC = importlib.util.spec_from_file_location(
    "gig_no_contact_telegram_test", ROOT / "scripts/telegram_report.py",
)
assert TELEGRAM_SPEC and TELEGRAM_SPEC.loader
telegram = importlib.util.module_from_spec(TELEGRAM_SPEC)
TELEGRAM_SPEC.loader.exec_module(telegram)


class FakeOutbox:
    def __init__(self):
        self.actions = {}
        self.closed = []
        self.revived = []

    def enqueue(self, *, event_key, thread_id, thread_url, observed_at):
        duplicate = next(
            (action for action in self.actions.values() if action["event_key"] == event_key),
            None,
        )
        if duplicate is not None:
            return duplicate
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
        self.actions[action_id]["dlq_at"] = now
        self.actions[action_id]["dlq_reason"] = f"nothing_to_say:{reason}"
        self.closed.append({
            "action_id": action_id, "owner": owner,
            "fencing_token": fencing_token, "reason": reason, "now": now,
        })

    def requeue_closed_action(self, action_id, *, now, require_no_intent=False):
        action = self.actions[action_id]
        action["dlq_at"] = None
        self.revived.append({
            "action_id": action_id, "now": now,
            "require_no_intent": require_no_intent,
        })
        return action

    def action_lifecycle_for_event(self, event_key, thread_id):
        action = next(
            (action for action in self.actions.values()
             if action["event_key"] == event_key and action["thread_id"] == thread_id),
            None,
        )
        if action is None:
            return None
        return {
            "state": action["state"], "dlq_at": action.get("dlq_at"),
            "reason": action.get("dlq_reason"),
        }


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


def test_head_policy_revives_matching_dlq_event_before_durable_closure(tmp_path):
    outbox = FakeOutbox()
    action = outbox.enqueue(
        event_key="coconala:inbox:v1:90001:sha256_v1:" + "a" * 64,
        thread_id="90001",
        thread_url="https://coconala.com/mypage/direct_message/90001",
        observed_at=900,
    )
    action["dlq_at"] = 950

    result = detector.partition_no_contact_rows([{
        "talkroom_id": "90001",
        "last_message_identity_sha256": "a" * 64,
    }], registry_path=_registry(tmp_path), outbox=outbox, now=1000)

    assert result["ignored"][0]["status"] == "ignore_policy"
    assert outbox.revived == [{
        "action_id": 1, "now": 1000, "require_no_intent": True,
    }]
    assert outbox.closed[0]["reason"] == "ignore_policy:operator-owned-1"


def test_policy_report_identity_is_unique_and_contains_no_counterparty_data():
    result = detector.no_contact_report({
        "status": "ignore_policy", "policy_id": "operator-owned-1", "action_id": 42,
    }, now=1000)

    assert result["run_id"] == "ignore-policy-operator-owned-1-42"
    assert result["closed_without_send"] == 1
    assert result["effect"] == 0
    assert result["official_readback"] == 0
    assert "thread_id" not in result
    assert "counterparty" not in json.dumps(result)
    _event_key, message = telegram.reply_wake_message(result)
    assert "private no-contact policyにより1件を送信せず終了しました" in message
    assert "未確認" not in message
    assert telegram.report_kinds_for_command("reply-wake") == (
        "reply_verified", "reply_wake", "reply_dlq",
    )


def test_same_policy_event_is_replay_zero_after_first_closure(tmp_path):
    outbox = FakeOutbox()
    rows = [{
        "talkroom_id": "90001",
        "last_message_identity_sha256": "a" * 64,
    }]
    first = detector.partition_no_contact_rows(
        rows, registry_path=_registry(tmp_path), outbox=outbox, now=1000,
    )
    second = detector.partition_no_contact_rows(
        rows, registry_path=_registry(tmp_path), outbox=outbox, now=1030,
    )

    assert first["ignored"][0]["status"] == "ignore_policy"
    assert second["ignored"][0]["status"] == "ignore_policy_replay"
    assert len(outbox.closed) == 1
    assert outbox.revived == []


def test_real_outbox_policy_closure_is_replay_zero(tmp_path):
    outbox = connector.ConnectorOutbox(
        tmp_path / "outbox.sqlite3",
        ROOT / "config/connectors/coconala.json",
    )
    rows = [{
        "talkroom_id": "90001",
        "last_message_identity_sha256": "a" * 64,
    }]

    first = detector.partition_no_contact_rows(
        rows, registry_path=_registry(tmp_path), outbox=outbox, now=1000,
    )
    second = detector.partition_no_contact_rows(
        rows, registry_path=_registry(tmp_path), outbox=outbox, now=1030,
    )

    assert first["ignored"][0]["status"] == "ignore_policy"
    assert second["ignored"][0]["status"] == "ignore_policy_replay"
    closures = outbox.closed_actions(closure="nothing_to_say")
    assert len(closures) == 1
    assert closures[0]["reason"] == "nothing_to_say:ignore_policy:operator-owned-1"


def test_supervisor_routes_head_policy_closure_to_reporter(tmp_path, monkeypatch):
    stop = asyncio.Event()
    reports = []
    workers = []
    args = SimpleNamespace(
        database=tmp_path / "outbox.sqlite3",
        manifest=ROOT / "config/connectors/coconala.json",
        no_contact_registry=_registry(tmp_path),
        poll_seconds=1, workers=2, reconcile_seconds=300,
    )
    monkeypatch.setattr(detector, "disk_headroom_ok", lambda: True)

    async def probe():
        stop.set()
        return {"inquiries": [{
            "talkroom_id": "90001",
            "last_message_identity_sha256": "a" * 64,
        }]}

    async def worker(work):
        workers.append(work)
        return {}

    async def reconcile():
        return {}

    async def report(path, result):
        reports.append((path, result))

    asyncio.run(detector.supervise_replies(
        args, probe=probe, worker=worker, reconcile=reconcile, stop=stop,
        report_root=tmp_path / "evidence", report=report,
    ))

    assert workers == []
    assert len(reports) == 1
    assert reports[0][1]["status"] == "ignore_policy"
    assert "policy-reports" in str(reports[0][0])


def test_telegram_report_does_not_call_zero_effect_command_sent(monkeypatch, tmp_path):
    monkeypatch.setattr(detector.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=0, stdout='{"sent":0,"delivery_unknown":0}\n', stderr="",
    ))
    args = SimpleNamespace(
        telegram_report_script=tmp_path / "telegram_report.py",
        database=tmp_path / "connector.sqlite3",
        telegram_database=tmp_path / "telegram.sqlite3",
        runner_config=tmp_path / "runner.json",
        telegram_target="target",
    )

    status = detector._telegram_report(args, tmp_path / "result.json", "reply-wake")

    assert status == "deferred"
