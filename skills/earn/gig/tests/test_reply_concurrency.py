"""Contract tests for fast, durable Coconala inbox discovery."""

from __future__ import annotations

import importlib.util
import json
import sys
import argparse
import textwrap
import time
from pathlib import Path

import pytest


GIG_ROOT = Path(__file__).resolve().parents[1]
OUTBOX_PATH = GIG_ROOT / "scripts" / "connector_outbox.py"
SNAPSHOT_PATH = GIG_ROOT / "scripts" / "coconala_queue_snapshot.py"
DETECTOR_PATH = GIG_ROOT / "scripts" / "reply_detector.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


outbox = _load_module("gig_connector_outbox_reply_concurrency_test", OUTBOX_PATH)
snapshot = _load_module("gig_queue_snapshot_reply_concurrency_test", SNAPSHOT_PATH)
detector = _load_module("gig_reply_detector_reply_concurrency_test", DETECTOR_PATH)


def _fake_targeted_scripts(tmp_path, *, next_action="reply", semantic_failure=None):
    script = tmp_path / "fake_targeted_stage.py"
    calls = tmp_path / "calls.jsonl"
    marker = tmp_path / "lane-count"
    connector_path = GIG_ROOT / "scripts" / "connector_outbox.py"
    script.write_text(textwrap.dedent(f"""
        import importlib.util, json, os, sys, time
        from pathlib import Path
        spec = importlib.util.spec_from_file_location("fake_outbox", {str(connector_path)!r})
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        argv = sys.argv[1:]
        with open({str(calls)!r}, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(argv) + "\\n")
        def value(flag):
            return Path(argv[argv.index(flag) + 1])
        if argv and argv[0] == "build":
            snapshot = json.loads(value("--snapshot").read_text())
            row = snapshot["inquiries"][0] if snapshot.get("inquiries") else None
            items = []
            if row and row.get("reply_required") is True:
                item = {{
                    "platform": "coconala", "priority": "P1", "event_type": "buyer_message",
                    "event_key": "coconala:message:v1:123:buyer-2",
                    "coordination_key": "coconala:123",
                    "covered_event_keys": ["coconala:message:v1:123:buyer-2"],
                    "talkroom_id": "123", "talkroom_url": "https://coconala.com/mypage/direct_message/123",
                    "origin_at": row["buyer_sent_at"], "detected_at": snapshot["captured_at"],
                    "next_action": row.get("next_action", "reply"),
                }}
                if row.get("semantic_reply_body"):
                    item["semantic_reply_body"] = row["semantic_reply_body"]
                    item["semantic_context_sha256"] = row["semantic_context_sha256"]
                items.append(item)
            value("--output").write_text(json.dumps({{
                "status": "ready" if items else "queue_empty", "errors": [], "items": items,
                "semantic_ssot": snapshot.get("semantic_ssot") is True,
            }}))
        elif argv and argv[0] == "enqueue":
            queue = json.loads(value("--queue").read_text())
            db = module.ConnectorOutbox(value("--database"), value("--manifest"))
            for item in queue.get("items", []):
                db.enqueue(event_key=item["event_key"], thread_id=item["talkroom_id"],
                           thread_url=item["talkroom_url"], observed_at=int(time.time()))
        elif "--queue" in argv and "--output" in argv:
            db = module.ConnectorOutbox(value("--database"), value("--manifest"))
            count_path = Path({str(marker)!r})
            count = int(count_path.read_text()) if count_path.exists() else 0
            count_path.write_text(str(count + 1))
            action = db.pending_action_for_thread("123")
            action_id = int(action["action_id"]) if action else 1
            fences = Path(value("--fences"))
            registry = json.loads(fences.read_text()) if fences.exists() else None
            paid = any(
                str(row.get("identities", {{}}).get("talkroom_id")) == "123"
                and row.get("state") == "open"
                for row in (registry or {{}}).get("fences", [])
                if isinstance(row, dict)
            )
            if paid:
                lane = {{
                    "status": "completed", "replied": 0, "reconciled": 0,
                    "pending_verify": 0, "reconcile_pending": 0, "already_delivered": 0,
                    "nothing_to_say": 0, "failed": 0, "blocked": 1, "deferred": 0, "dlq": 0,
                    "errors": ["paid_talkroom_write_refused"], "events": [], "dlq_events": [],
                }}
            elif count == 0 and {next_action!r} == "reply" and {semantic_failure!r} is None:
                lane = {{
                    "status": "completed", "replied": 1, "reconciled": 0,
                    "pending_verify": 0, "reconcile_pending": 0, "already_delivered": 0,
                    "nothing_to_say": 0, "failed": 0, "blocked": 0, "deferred": 0, "dlq": 0,
                    "errors": [], "events": [{{
                        "status": "replied", "action_id": action_id, "revision": 1,
                        "talkroom_id": "123", "origin_at": "2026-08-19T00:01:00+00:00",
                        "seller_sent_at": "2026-08-19T00:02:00+00:00",
                    }}], "dlq_events": [],
                }}
            else:
                lane = {{
                    "status": "completed", "replied": 0, "reconciled": 0,
                    "pending_verify": 0, "reconcile_pending": 0, "already_delivered": 1,
                    "nothing_to_say": 0, "failed": 0, "blocked": 0, "deferred": 0, "dlq": 0,
                    "errors": [], "events": [], "dlq_events": [],
                }}
            value("--output").write_text(json.dumps(lane))
        elif "--mode" in argv:
            output = value("--output")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps({{
                "version": 1, "collector_mode": "direct-thread-only", "semantic_ssot": True,
                "captured_at": "2026-08-19T00:01:00+00:00", "read_only": True,
                "orders": [], "source_receipt": {{"source": "direct_thread"}},
                "inquiries": [{{
                    "talkroom_id": "123", "talkroom_url": "https://coconala.com/mypage/direct_message/123",
                    "last_message_side": "buyer", "reply_required": {next_action!r} == "reply",
                    "next_action": {next_action!r}, "buyer_sent_at": "2026-08-19T00:01:00+00:00",
                    "message_id": "buyer-2",
                    "semantic_receipt": {{"judgement": {{"next_action": {next_action!r}}}}},
                    "semantic_failure": {semantic_failure!r},
                    "semantic_context_sha256": "a" * 64,
                    "semantic_reply_body": "回答です" if {next_action!r} == "reply" else None,
                }}],
            }}))
    """), encoding="utf-8")
    return script, calls


def _targeted_args(tmp_path, script):
    fences = tmp_path / "fences.json"
    fences.write_text(json.dumps({"version": 1, "fences": []}), encoding="utf-8")
    return argparse.Namespace(
        snapshot_script=script, queue_script=script, lane_script=script,
        fence_script=script, fences=fences, database=tmp_path / "outbox.sqlite3",
        manifest=GIG_ROOT / "config" / "connectors" / "coconala.json",
        runner=GIG_ROOT / "agent-runner" / "agent_runner.py",
        semantic_schema=GIG_ROOT / "schemas" / "reply_semantic_judgement.schema.json",
        estimate_schema=GIG_ROOT / "schemas" / "estimate_category_selection.schema.json",
        schema=GIG_ROOT / "schemas" / "reply_composition.schema.json",
        cdp_helper=GIG_ROOT / "scripts" / "cdp_default_tab.py",
        semantic_effects_enabled=True,
    )


def _seed_inbox_action(args):
    database = outbox.ConnectorOutbox(args.database, args.manifest)
    database.enqueue(
        event_key=outbox.coconala_inbox_event_key("123", "b" * 64),
        thread_id="123",
        thread_url="https://coconala.com/mypage/direct_message/123",
        observed_at=int(time.time()),
    )


def test_targeted_thread_reaches_official_readback(tmp_path):
    script, calls = _fake_targeted_scripts(tmp_path)
    args = _targeted_args(tmp_path, script)
    _seed_inbox_action(args)
    result = detector.run_targeted_thread(
        args, thread_id="123", evidence=tmp_path / "evidence", run_id="run-1",
    )
    assert result["status"] == "completed"
    assert result["replied"] == 1
    assert result["thread_id"] == "123"
    assert result["official_readback"] == 1
    recorded = [json.loads(line) for line in calls.read_text().splitlines()]
    collect = [argv for argv in recorded if "--mode" in argv]
    assert collect and all("123" in argv for argv in collect)
    evidence = tmp_path / "evidence"
    saved_snapshot = json.loads((evidence / "marketplace-snapshot.json").read_text())
    saved_queue = json.loads((evidence / "reply-queue.json").read_text())
    saved_lane = json.loads((evidence / "reply-lane-result.json").read_text())
    assert saved_snapshot["collector_mode"] == "direct-thread-only"
    assert saved_snapshot["semantic_ssot"] is True
    assert [item["talkroom_id"] for item in saved_snapshot["inquiries"]] == ["123"]
    assert saved_queue["status"] == "ready"
    assert len(saved_queue["items"]) == 1
    assert saved_queue["items"][0]["talkroom_id"] == "123"
    assert saved_lane["status"] == "completed"
    assert saved_lane["replied"] == 1


def test_targeted_replay_has_zero_second_effect(tmp_path):
    script, _calls = _fake_targeted_scripts(tmp_path)
    args = _targeted_args(tmp_path, script)
    _seed_inbox_action(args)
    first = detector.run_targeted_thread(
        args, thread_id="123", evidence=tmp_path / "evidence-1", run_id="run-1",
    )
    second = detector.run_targeted_thread(
        args, thread_id="123", evidence=tmp_path / "evidence-2", run_id="run-2",
    )
    assert first["official_readback"] == 1
    assert second["replied"] == 0
    assert second["duplicate_effect"] == 0


def test_intentional_no_send_closes_exact_claim_without_reply(tmp_path):
    script, _calls = _fake_targeted_scripts(tmp_path, next_action="wait")
    args = _targeted_args(tmp_path, script)
    _seed_inbox_action(args)
    result = detector.run_targeted_thread(
        args, thread_id="123", evidence=tmp_path / "evidence", run_id="run-wait",
    )
    assert result["replied"] == 0
    assert result["closed_without_send"] == 1
    assert outbox.ConnectorOutbox(args.database, args.manifest).pending_actions() == []


def test_semantic_failure_stays_pending_without_send(tmp_path):
    script, _calls = _fake_targeted_scripts(
        tmp_path, semantic_failure="runner_failed",
    )
    args = _targeted_args(tmp_path, script)
    _seed_inbox_action(args)
    result = detector.run_targeted_thread(
        args, thread_id="123", evidence=tmp_path / "evidence", run_id="run-failed",
    )
    assert result["status"] == "pending"
    assert result["replied"] == 0
    assert result["pending"] == 1
    assert result["closed_without_send"] == 0
    assert outbox.ConnectorOutbox(args.database, args.manifest).pending_actions()


def test_targeted_paid_fence_refuses_effect(tmp_path):
    script, _calls = _fake_targeted_scripts(tmp_path)
    args = _targeted_args(tmp_path, script)
    _seed_inbox_action(args)
    args.fences.write_text(json.dumps({
        "version": 1,
        "fences": [{
            "id": "paid-conversation-write:coconala:123",
            "state": "open", "platform": "coconala",
            "identities": {"talkroom_id": "123"},
            "capabilities": ["conversation_write"],
            "reason": "paid room", "opened_at": "2026-08-19T00:00:00+00:00",
            "release": {"kind": "event", "event": "paid_order_closed:123"},
        }],
    }), encoding="utf-8")
    result = detector.run_targeted_thread(
        args, thread_id="123", evidence=tmp_path / "evidence", run_id="run-paid",
    )
    assert result["replied"] == 0
    assert result["blocked"] == 1
    assert result["official_readback"] == 0


def test_inbox_event_key_is_thread_bound_and_rejects_non_sha_identity():
    assert outbox.coconala_inbox_event_key("123", "a" * 64) == (
        "coconala:inbox:v1:123:sha256_v1:" + "a" * 64
    )
    assert outbox.validate_coconala_event_key(
        "coconala:inbox:v1:123:sha256_v1:" + "a" * 64, "123"
    ).startswith("coconala:inbox:v1:123:")
    with pytest.raises(ValueError):
        outbox.coconala_inbox_event_key("123", "not-a-sha")
    with pytest.raises(ValueError):
        outbox.validate_coconala_event_key(
            "coconala:inbox:v1:123:sha256_v1:" + "a" * 64, "999"
        )


def test_head_expression_reads_one_page_without_changing_full_expression():
    assert snapshot.direct_inbox_coverage_expression() == snapshot.DIRECT_INBOX_COVERAGE_EXPRESSION
    head = snapshot.direct_inbox_coverage_expression(1)
    assert "pageLimit=1" in head
    assert "pageLimit=10" not in head
    with pytest.raises(ValueError):
        snapshot.direct_inbox_coverage_expression(0)


def test_head_only_snapshot_is_bounded_read_only_and_semantic_free(tmp_path, monkeypatch, capsys):
    output = tmp_path / "head.json"
    evidence = tmp_path / "evidence"
    opened = []
    seen = {}
    forbidden_fields = {
        "body", "preview", "preview_text", "raw_preview", "seller_id",
        "seller_name", "seller_user_id", "user_id", "user_name", "user_identity",
    }
    forbidden_sentinels = {
        "BUYER_BODY_SENTINEL", "BUYER_PREVIEW_SENTINEL", "SELLER_ID_SENTINEL",
        "SELLER_NAME_SENTINEL", "SELLER_USER_ID_SENTINEL", "USER_ID_SENTINEL",
        "USER_NAME_SENTINEL", "USER_IDENTITY_SENTINEL",
    }

    class FakeTab:
        ws = "ws://head-only"

        def __init__(self, helper, url, *, hidden=False, **kwargs):
            seen["tab"] = (helper, url, hidden, kwargs)

        def __enter__(self):
            opened.append(True)
            return self

        def __exit__(self, *args):
            return None

    async def fake_inspect_message_page(ws_url, expression, expected_url, **kwargs):
        seen["inspect"] = (ws_url, expression, expected_url, kwargs)
        return {
            "url": snapshot.MESSAGES_URL,
            "title": "メッセージ",
            "container_present": True,
            "cards": [{
                "talkroom_url": "https://coconala.com/mypage/direct_message/123",
                "title": "purchase_preorder_message",
                "last_message_side": "",
                "unread": True,
                "preview_sha256": "a" * 64,
                "last_message_identity_sha256": "b" * 64,
                "body": "BUYER_BODY_SENTINEL",
                "preview": "BUYER_PREVIEW_SENTINEL",
                "preview_text": "BUYER_PREVIEW_SENTINEL",
                "raw_preview": "BUYER_PREVIEW_SENTINEL",
                "seller_id": "SELLER_ID_SENTINEL",
                "seller_name": "SELLER_NAME_SENTINEL",
                "seller_user_id": "SELLER_USER_ID_SENTINEL",
                "user_id": "USER_ID_SENTINEL",
                "user_name": "USER_NAME_SENTINEL",
                "user_identity": "USER_IDENTITY_SENTINEL",
            }],
            "cards_count": 1,
            "coverage_complete": True,
            "termination_reason": "pagination_end",
        }

    def unsafe_inquiries_from_dom(dom):
        card = dom["cards"][0]
        return [{
            "talkroom_id": "123",
            "talkroom_url": card["talkroom_url"],
            "title": "purchase_preorder_message",
            "reply_required": True,
            "next_action": "reply",
            "preview_sha256": card["preview_sha256"],
            "last_message_identity_sha256": card["last_message_identity_sha256"],
            "body": card["body"],
            "preview": card["preview"],
            "preview_text": card["preview_text"],
            "raw_preview": card["raw_preview"],
            "seller_id": card["seller_id"],
            "seller_name": card["seller_name"],
            "seller_user_id": card["seller_user_id"],
            "user_id": card["user_id"],
            "user_name": card["user_name"],
            "user_identity": card["user_identity"],
        }]

    def semantic_must_not_load():
        raise AssertionError("head-only must not initialize SemanticJudge")

    monkeypatch.setattr(snapshot, "DefaultTab", FakeTab)
    monkeypatch.setattr(snapshot, "inspect_message_page", fake_inspect_message_page)
    monkeypatch.setattr(snapshot, "inquiries_from_dom", unsafe_inquiries_from_dom)
    monkeypatch.setattr(snapshot, "load_connector_manifest", lambda: {})
    monkeypatch.setattr(snapshot, "_requested_estimate_module", semantic_must_not_load)
    monkeypatch.setattr(
        sys, "argv", [
            "coconala_queue_snapshot.py",
            "--output", str(output),
            "--evidence-dir", str(evidence),
            "--mode", "direct-inbox-head-only",
        ],
    )

    assert snapshot.main() == 0
    cli_output = capsys.readouterr().out
    cli = json.loads(cli_output)
    saved = json.loads(output.read_text(encoding="utf-8"))
    evidence_payloads = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in evidence.rglob("*.json")
    ]

    assert cli["collector_mode"] == "direct-inbox-head-only"
    assert isinstance(cli["captured_at"], str) and cli["captured_at"]
    assert cli["inquiries"] == 1
    assert cli["head_only"] is True
    assert cli["read_only"] is True
    assert saved["collector_mode"] == "direct-inbox-head-only"
    assert saved["head_only"] is True
    assert saved["semantic_ssot"] is False
    assert saved["read_only"] is True
    assert saved["source_receipt"]["source"] == "direct_inbox"
    assert saved["source_receipt"]["coverage_complete"] is False
    assert seen["tab"][1] == snapshot.MESSAGES_URL
    assert seen["inspect"][3]["coverage_expression"] == snapshot.direct_inbox_coverage_expression(1)
    assert seen["inspect"][3]["validate_coverage"] is False
    assert len(opened) == 1
    persisted = [saved, *evidence_payloads]
    serialized = json.dumps(persisted, ensure_ascii=False)
    assert not forbidden_sentinels.intersection(serialized.split('"'))
    assert not forbidden_sentinels.intersection(cli_output.split('"'))

    def assert_allowed_keys(value):
        if isinstance(value, dict):
            assert not forbidden_fields.intersection(value)
            for child in value.values():
                assert_allowed_keys(child)
        elif isinstance(value, list):
            for child in value:
                assert_allowed_keys(child)

    for payload in persisted:
        assert_allowed_keys(payload)
    assert_allowed_keys(cli)


def test_direct_thread_only_owns_exact_url_and_emits_one_semantic_inquiry(
    tmp_path, monkeypatch, capsys,
):
    output = tmp_path / "thread.json"
    evidence = tmp_path / "evidence"
    opened = []

    class FakeTab:
        ws = "ws://thread-only"

        def __init__(self, helper, url, *, hidden=False, **kwargs):
            opened.append((helper, url, hidden, kwargs))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    class FakeSemanticModule:
        class SemanticJudge:
            def __init__(self, **kwargs):
                pass

    async def fake_inspect_message_page(ws_url, expression, expected_url, **kwargs):
        return {
            "url": expected_url, "title": "メッセージ詳細",
            "container_present": True, "own_user_path": "/users/seller",
            "messages": [{
                "message_id": "buyer-2", "author_path": "/users/buyer",
                "sent_at": "2026-08-19T00:01:00+00:00", "body": "質問です",
            }],
        }

    monkeypatch.setattr(snapshot, "DefaultTab", FakeTab)
    monkeypatch.setattr(snapshot, "inspect_message_page", fake_inspect_message_page)
    monkeypatch.setattr(snapshot, "load_connector_manifest", lambda: {})
    monkeypatch.setattr(snapshot, "_requested_estimate_module", lambda: FakeSemanticModule)
    monkeypatch.setattr(snapshot, "direct_message_event", lambda dom, url, **kwargs: {
        "last_message_side": "buyer", "reply_required": True, "next_action": "reply",
        "buyer_sent_at": "2026-08-19T00:01:00+00:00", "message_id": "buyer-2",
        "semantic_receipt": {"judgement": {"next_action": "reply"}},
        "semantic_context_sha256": "a" * 64, "semantic_reply_body": "回答です",
    })
    monkeypatch.setattr(
        sys, "argv", [
            "coconala_queue_snapshot.py", "--output", str(output),
            "--evidence-dir", str(evidence), "--mode", "direct-thread-only",
            "--talkroom-id", "123", "--semantic-effects-enabled",
        ],
    )

    assert snapshot.main() == 0
    cli = json.loads(capsys.readouterr().out)
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert cli["collector_mode"] == "direct-thread-only"
    assert cli["semantic_ssot"] is True
    assert saved["semantic_ssot"] is True
    assert len(saved["inquiries"]) == 1
    assert saved["inquiries"][0]["talkroom_url"] == (
        "https://coconala.com/mypage/direct_message/123"
    )
    assert opened and opened[0][1] == saved["inquiries"][0]["talkroom_url"]

    monkeypatch.setattr(
        sys, "argv", [
            "coconala_queue_snapshot.py", "--output", str(output),
            "--evidence-dir", str(evidence), "--mode", "direct-thread-only",
            "--talkroom-id", "../123",
        ],
    )
    assert snapshot.main() == 1
    invalid = json.loads(capsys.readouterr().out)
    assert invalid["error"] == "invalid_talkroom_id"
