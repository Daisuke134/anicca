"""Contract tests for fast, durable Coconala inbox discovery."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


GIG_ROOT = Path(__file__).resolve().parents[1]
OUTBOX_PATH = GIG_ROOT / "scripts" / "connector_outbox.py"
SNAPSHOT_PATH = GIG_ROOT / "scripts" / "coconala_queue_snapshot.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


outbox = _load_module("gig_connector_outbox_reply_concurrency_test", OUTBOX_PATH)
snapshot = _load_module("gig_queue_snapshot_reply_concurrency_test", SNAPSHOT_PATH)


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
            }],
            "cards_count": 1,
            "coverage_complete": True,
            "termination_reason": "pagination_end",
        }

    def semantic_must_not_load():
        raise AssertionError("head-only must not initialize SemanticJudge")

    monkeypatch.setattr(snapshot, "DefaultTab", FakeTab)
    monkeypatch.setattr(snapshot, "inspect_message_page", fake_inspect_message_page)
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
    cli = json.loads(capsys.readouterr().out)
    saved = json.loads(output.read_text(encoding="utf-8"))

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
    for inquiry in saved["inquiries"]:
        assert not {"body", "preview", "preview_text", "raw_preview"}.intersection(inquiry)
