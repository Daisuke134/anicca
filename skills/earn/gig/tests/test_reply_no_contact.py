import asyncio
import hashlib
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
QUEUE_SPEC = importlib.util.spec_from_file_location(
    "gig_no_contact_reply_queue_test", ROOT / "scripts/reply_queue.py",
)
assert QUEUE_SPEC and QUEUE_SPEC.loader
reply_queue = importlib.util.module_from_spec(QUEUE_SPEC)
QUEUE_SPEC.loader.exec_module(reply_queue)
LANE_SPEC = importlib.util.spec_from_file_location(
    "gig_no_contact_reply_lane_test", ROOT / "scripts/reply_lane.py",
)
assert LANE_SPEC and LANE_SPEC.loader
reply_lane = importlib.util.module_from_spec(LANE_SPEC)
LANE_SPEC.loader.exec_module(reply_lane)
BROWSER_SPEC = importlib.util.spec_from_file_location(
    "gig_no_contact_reply_browser_test", ROOT / "scripts/coconala_reply_browser.py",
)
assert BROWSER_SPEC and BROWSER_SPEC.loader
reply_browser = importlib.util.module_from_spec(BROWSER_SPEC)
BROWSER_SPEC.loader.exec_module(reply_browser)


def test_targeted_seller_debt_bridge_binds_verified_reply_to_target_event():
    inquiry = {
        "last_message_side": "seller",
        "seller_sent_at": "2026-08-22T12:31:47+00:00",
        "reply_required": True,
        "next_action": "reply",
        "semantic_reply_body": "X用投稿案：全文\nWeibo用投稿案：全文",
        "semantic_receipt": {
            "prompt_version": "reply-negotiate-v27",
            "judgement": {"next_action": "reply"},
        },
    }
    target = {
        "action_id": 378,
        "thread_id": "10082097",
        "inbox_event_key": "coconala:inbox:v1:10082097:sha256_v1:" + "a" * 64,
    }
    queue = {"status": "ready", "items": [{"event_key": "old", "covered_event_keys": ["old"]}]}

    assert detector._targeted_seller_debt_reply(inquiry) is True
    rebound = detector._bind_targeted_seller_debt_queue(queue, target)
    assert rebound["items"][0]["event_key"] == target["inbox_event_key"]
    assert rebound["items"][0]["covered_event_keys"] == [target["inbox_event_key"]]


def test_targeted_obsolete_estimate_closes_exact_action_without_send(tmp_path):
    database = tmp_path / "outbox.sqlite3"
    manifest = ROOT / "config/connectors/coconala.json"
    outbox = connector.ConnectorOutbox(database, manifest)
    event_key = connector.coconala_estimate_event_key("90001", "buyer-purchased")
    action = outbox.enqueue(
        event_key=event_key, thread_id="90001",
        thread_url="https://coconala.com/mypage/direct_message/90001",
        observed_at=1000,
    )

    closed = detector._targeted_close_obsolete_estimate(
        database=database, manifest=manifest,
        action_id=int(action["action_id"]), thread_id="90001",
        event_key=event_key, expected_revision=1, run_id="test",
    )

    assert closed == {"action_id": action["action_id"], "revision": 1,
                      "status": "nothing_to_say"}
    assert outbox.dlq_actions() == []
    closure = outbox.closed_actions(closure="nothing_to_say")[0]
    assert closure["reason"] == "nothing_to_say:estimate_no_longer_required"


def test_reply_queue_builds_verified_seller_debt_without_relabeling_official_side():
    queue = reply_queue.build_queue({
        "captured_at": "2026-08-22T12:32:00+00:00",
        "semantic_ssot": True,
        "orders": [],
        "inquiries": [{
            "talkroom_id": "10082097",
            "talkroom_url": "https://coconala.com/mypage/direct_message/10082097",
            "last_message_side": "seller",
            "seller_sent_at": "2026-08-22T12:31:47+00:00",
            "reply_required": True,
            "next_action": "reply",
            "semantic_seller_debt_reply": True,
            "semantic_reply_body": "X用投稿案：全文\nWeibo用投稿案：全文",
            "semantic_context_sha256": "b" * 64,
            "semantic_receipt": {"version": 1},
            "stable_ordinal": 0,
            "message_sha256": "c" * 64,
        }],
    })

    assert queue["status"] == "ready"
    assert queue["items"][0]["semantic_reply_body"].startswith("X用投稿案：")
    assert queue["items"][0]["semantic_seller_debt_reply"] is True


def test_semantic_composer_allows_only_verified_seller_debt_after_seller_last():
    composer = reply_lane.SemanticReceiptComposer()
    seller_last = {"conversation": [{"role": "seller"}]}
    verified_debt = {
        **seller_last,
        "semantic_seller_debt_reply": True,
        "semantic_reply_body": "X用投稿案：全文\nWeibo用投稿案：全文",
    }

    assert composer.nothing_to_say_reason(seller_last) == "seller_last"
    assert composer.nothing_to_say_reason(verified_debt) is None


def test_semantic_freshness_accepts_verified_debt_only_when_seller_still_last():
    rows = [{
        "message_id": "message-1", "role": "seller",
        "sent_at": "2026-08-22T12:31:47+00:00", "body": "preview promised",
    }]
    expected = hashlib.sha256(json.dumps(
        rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    browser = reply_browser.CoconalaCdpReplyBrowser.__new__(
        reply_browser.CoconalaCdpReplyBrowser,
    )
    browser.semantic_context_sha256 = expected
    browser.semantic_expected_last_sender = "seller"
    browser._read = lambda: (
        {"conversation": rows}, {"last_sender": "seller"},
    )

    browser.verify_semantic_freshness()


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


def test_busy_reply_wake_reports_lock_contention_without_unknown_metrics():
    _event_key, message = telegram.reply_wake_message({
        "run_id": "busy-1", "status": "busy",
        "observed": None, "actionable": None, "effect": None,
    })

    assert "前回の確認処理が継続中" in message
    assert "重複起動せず" in message
    assert "この確認では返信・見積りを送信していません" in message
    assert "未確認" not in message
    assert "通常返信の処理対象" not in message


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
    call = {}
    def fake_run(*args, **kwargs):
        call.update(kwargs)
        return SimpleNamespace(
            returncode=0, stdout='{"sent":0,"delivery_unknown":0}\n', stderr="",
        )
    monkeypatch.setattr(detector.subprocess, "run", fake_run)
    args = SimpleNamespace(
        telegram_report_script=tmp_path / "telegram_report.py",
        database=tmp_path / "connector.sqlite3",
        telegram_database=tmp_path / "telegram.sqlite3",
        runner_config=tmp_path / "runner.json",
        telegram_target="target",
    )

    status = detector._telegram_report(args, tmp_path / "result.json", "reply-wake")

    assert status == "deferred"
    assert call["timeout"] == 240


def test_supervisor_runs_first_full_reconciliation_after_one_poll(tmp_path, monkeypatch):
    stop = asyncio.Event()
    reconciliations = []
    registry = tmp_path / "no-contact.json"
    registry.write_text('{"version":1,"entries":[]}', encoding="utf-8")
    args = SimpleNamespace(
        database=tmp_path / "outbox.sqlite3",
        manifest=ROOT / "config/connectors/coconala.json",
        no_contact_registry=registry,
        poll_seconds=0.01, workers=2, reconcile_seconds=300,
    )
    monkeypatch.setattr(detector, "disk_headroom_ok", lambda: True)

    async def probe():
        return {"inquiries": []}

    async def worker(_work):
        raise AssertionError("empty inbox must not create work")

    async def reconcile():
        reconciliations.append(True)
        stop.set()
        return {}

    asyncio.run(asyncio.wait_for(detector.supervise_replies(
        args, probe=probe, worker=worker, reconcile=reconcile, stop=stop,
        report_root=tmp_path / "evidence",
    ), timeout=1))

    assert reconciliations == [True]


class _BacklogController:
    """A controller with a durable backlog and no reconciliations in flight.

    Every backlog thread routes through the "no exact event" early return in
    process_one (pending_action_for_thread -> None, then a lifecycle lookup that
    raises), so the test never has to fake a browser or a compose function.
    """

    def __init__(self, backlog):
        self._backlog = backlog
        self.outbox = SimpleNamespace(
            action_lifecycle_for_event=lambda event_key, thread_id: (_ for _ in ()).throw(
                ValueError("no exact event for test")
            )
        )

    def reconciliation_actions(self):
        return {}

    def pending_actions(self):
        return self._backlog

    def pending_action_for_thread(self, thread_id):
        return None


def test_durable_backlog_is_processed_even_when_the_fresh_scan_finds_items():
    """Bug measured 2026-09-04: 97 threads sat pending up to 30 days because the
    backlog fallback only ran when the fresh scan found literally nothing this
    pass. A busy shop's fresh scan almost never finds nothing, so the backlog
    was starved. The fold-in must fire whenever this is not a targeted single-
    thread call (semantic_ssot is not True), independent of the fresh scan.
    """
    backlog = [
        {
            "thread_id": "10103725", "event_key": "coconala:message:v1:10103725:1",
            "event_observed_at": 1000, "thread_url": "https://coconala.com/talkrooms/10103725",
        },
        {
            "thread_id": "10153363", "event_key": "coconala:message:v1:10153363:1",
            "event_observed_at": 2000, "thread_url": "https://coconala.com/talkrooms/10153363",
        },
    ]
    controller = _BacklogController(backlog)
    queue = {
        "status": "ready",
        "items": [{
            "event_key": "coconala:message:v1:99999999:1",
            "covered_event_keys": ["coconala:message:v1:99999999:1"],
            "talkroom_id": "99999999",
            "talkroom_url": "https://coconala.com/talkrooms/99999999",
            "origin_at": "2026-09-04T00:00:00+00:00",
        }],
    }

    summary = reply_lane.process_queue(
        controller=controller, queue=queue, compose=lambda context: "unused",
        browser_factory=lambda action, item: None, owner_prefix="test",
        clock=lambda: 1, paid_talkroom_ids=lambda: set(),
    )

    decided_threads = {entry["talkroom_id"] for entry in summary["errors"]}
    assert decided_threads == {"99999999", "10103725", "10153363"}
