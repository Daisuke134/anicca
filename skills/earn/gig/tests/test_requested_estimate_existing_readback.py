from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path


GIG_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


requested_estimate = _load(
    "gig_requested_estimate_existing_readback_test",
    GIG_ROOT / "scripts" / "requested_estimate.py",
)
outbox = _load(
    "gig_connector_outbox_existing_estimate_test",
    GIG_ROOT / "scripts" / "connector_outbox.py",
)


def test_existing_official_estimate_closes_before_opening_an_invalid_form(tmp_path):
    thread_id = "123"
    thread_url = f"https://coconala.com/mypage/direct_message/{thread_id}"
    request_identity = "buyer-request"
    request_at = datetime(2026, 8, 21, 0, 30, tzinfo=timezone.utc)
    now = int(datetime(2026, 8, 21, 1, 40, tzinfo=timezone.utc).timestamp())
    title = "候補者リストアップ"
    content = "候補者を100件確認し、50件へ連絡します。"
    database = outbox.ConnectorOutbox(
        tmp_path / "outbox.sqlite3",
        GIG_ROOT / "config" / "connectors" / "coconala.json",
    )

    class Browser:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read_thread_context(self):
            return {"last_message_identity_sha256": "a" * 64}, {
                "own_user_path": "/users/seller",
                "structured_offers": [{
                    "message_kind": "見積り提案をしました",
                    "sender_side": "seller",
                    "author_path": "/users/seller",
                    "title": title,
                    "content": f"{content}\n完了予定日：2026-08-25（4日後）",
                    "price_jpy": 9000,
                    "completion_date": "2026-08-25",
                    "offer_url": "/mypage/direct_offers/456",
                    "sent_at": "2026-08-21T01:07:45+00:00",
                }],
            }

        def open_form(self):
            raise AssertionError("an existing official estimate must win before form navigation")

    result = requested_estimate.execute_requested_estimate(
        {
            "talkroom_id": thread_id,
            "talkroom_url": thread_url,
            "estimate_url": "https://coconala.com/direct_offers/add/999",
            "estimate_request_identity": request_identity,
            "estimate_request_sent_at": request_at.isoformat(),
            "source_inbox_identity_sha256": "a" * 64,
            "semantic_estimate_terms": {
                "title": title,
                "content": content,
                "price_jpy": 9000,
                "delivery_days": 4,
                "purchase_plan": "single",
            },
        },
        database=database,
        composer=object(),
        browser_factory=lambda *_args: Browser(),
        helper=None,
        owner="test",
        now=now,
    )

    event_key = outbox.coconala_estimate_event_key(thread_id, request_identity)
    assert result["status"] == "already_delivered", result
    assert result["official_readback"] == 1
    assert result["event_key"] == event_key, result
    assert database.action_lifecycle_for_event(event_key, thread_id)["state"] == "replied"
    assert database.verified_estimate_after_request(
        thread_id, int(request_at.timestamp()),
    )["event_key"] == event_key
