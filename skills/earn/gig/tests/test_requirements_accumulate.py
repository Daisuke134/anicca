"""A fact the buyer stated once must still be a requirement ten passes later.

Order 91000002, 2026-08-07: ``persist_latest_paid_buyer_reply`` rewrote
``requirements/live-buyer-reply.json`` from a single DOM snapshot every pass, and after
our first delivery it only looked at messages *after* our own last attachment. Everything
the buyer had said before that point stopped counting as a requirement -- while the judge,
reading the whole talkroom ledger, still saw it. These tests pin the accumulation that
closes the gap, and the two properties it must not break: no sidecar is invented for an
order that has none, and an unchanged poll still does not rewrite the file.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "coconala_queue_snapshot.py"
SPEC = importlib.util.spec_from_file_location("coconala_queue_snapshot", SCRIPT)
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)

PASS_ONE_FACT = "デッキは4枚構成でお願いします"
PASS_TWO_FACT = "タイトルの色を濃くしてください"


def _talkroom(messages: list[dict[str, object]]) -> dict[str, object]:
    return {
        "url": "https://coconala.com/talkrooms/90000002",
        "transaction_state": "取引中",
        "messages": messages,
    }


def _sidecar(projects: Path, project_id: str = "91000002") -> dict[str, object]:
    path = projects / project_id / "requirements" / "live-buyer-reply.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _accumulated_text(payload: dict[str, object]) -> str:
    rows = payload.get("accumulated_requirements")
    assert isinstance(rows, list)
    return "\n".join(str(row.get("text") or "") for row in rows)


def test_a_fact_from_pass_one_survives_the_delivery_that_narrows_the_window(tmp_path):
    projects = tmp_path / "projects"
    pass_one = _talkroom([
        {"side": "buyer", "text": PASS_ONE_FACT, "attachments": []},
    ])
    first = collector.persist_latest_paid_buyer_reply(
        pass_one, "91000002", projects, "2026-08-06T01:00:00+00:00",
    )
    assert first is not None
    assert PASS_ONE_FACT in _sidecar(projects)["feedback_text"]

    # We deliver, and the buyer says something new. The current *request* is the new
    # message -- that windowing is correct and stays. What must not happen is the older
    # fact disappearing from the requirements.
    pass_two = _talkroom([
        {"side": "buyer", "text": PASS_ONE_FACT, "attachments": []},
        {"side": "seller", "text": "v1です", "attachments": [{"filename": "v1.pptx"}]},
        {"side": "buyer", "text": PASS_TWO_FACT, "attachments": []},
    ])
    second = collector.persist_latest_paid_buyer_reply(
        pass_two, "91000002", projects, "2026-08-07T01:00:00+00:00",
    )
    assert second is not None
    payload = _sidecar(projects)
    assert payload["buyer_feedback_stage"] == "revision"
    assert PASS_TWO_FACT in payload["feedback_text"]
    assert PASS_ONE_FACT not in payload["feedback_text"]
    accumulated = _accumulated_text(payload)
    assert PASS_ONE_FACT in accumulated
    assert PASS_TWO_FACT in accumulated


def test_the_first_fact_is_still_there_at_pass_ten_when_the_dom_has_forgotten_it(tmp_path):
    """Coconala lazy-loads older messages, so a long room stops rendering them at all."""
    projects = tmp_path / "projects"
    collector.persist_latest_paid_buyer_reply(
        _talkroom([{"side": "buyer", "text": PASS_ONE_FACT, "attachments": []}]),
        "91000002", projects, "2026-08-06T01:00:00+00:00",
    )
    for index in range(2, 11):
        # From pass 2 on, the capture window contains neither the first message nor our
        # own attachment: exactly the shape that used to erase the requirement.
        collector.persist_latest_paid_buyer_reply(
            _talkroom([
                {"side": "seller", "text": f"v{index}です", "attachments": [{"filename": f"v{index}.pptx"}]},
                {"side": "buyer", "text": f"確認します {index}", "attachments": []},
            ]),
            "91000002", projects, f"2026-08-07T{index:02d}:00:00+00:00",
        )
    payload = _sidecar(projects)
    assert PASS_ONE_FACT in _accumulated_text(payload)
    assert "確認します 10" in payload["feedback_text"]


def _capture_that_lost_our_attachment() -> dict[str, object]:
    # 納品確認待ち: the marketplace says we delivered, but our attachment scrolled
    # out of the capture window, so the stage cannot be derived from this poll.
    return {
        "url": "https://coconala.com/talkrooms/90000002",
        "transaction_state": "納品確認待ち",
        "formal_delivery_control_checked": True,
        "messages": [{"side": "buyer", "text": PASS_TWO_FACT, "attachments": []}],
    }


def test_accumulation_keeps_a_fact_when_the_capture_window_loses_our_attachment(tmp_path):
    """A truncated capture must neither rewrite the request nor drop a statement."""
    projects = tmp_path / "projects"
    collector.persist_latest_paid_buyer_reply(
        _talkroom([{"side": "buyer", "text": PASS_ONE_FACT, "attachments": []}]),
        "91000002", projects, "2026-08-06T01:00:00+00:00",
    )
    collector.persist_latest_paid_buyer_reply(
        _capture_that_lost_our_attachment(), "91000002", projects, "2026-08-07T01:00:00+00:00",
    )
    payload = _sidecar(projects)
    # The current-request fields are untouched...
    assert PASS_ONE_FACT in payload["feedback_text"]
    # ...and the new statement is still recorded rather than dropped.
    assert PASS_TWO_FACT in _accumulated_text(payload)


def test_a_truncated_capture_still_names_the_request_the_sidecar_holds(tmp_path):
    """Order 90000004, 2026-08-07: reporting nothing here is not "no news".

    The same truncated window still reports ``buyer_feedback_pending_artifact``,
    so an order carrying no ``buyer_feedback_sha256`` reads downstream as
    unprocessed buyer feedback -- a blocker no amount of building can clear. It
    rebuilt v15, v16 and v17 on consecutive hours behind exactly that. The
    sidecar already on disk names the current request; saying so again is a read,
    not an invention.
    """
    projects = tmp_path / "projects"
    collector.persist_latest_paid_buyer_reply(
        _talkroom([{"side": "buyer", "text": PASS_ONE_FACT, "attachments": []}]),
        "91000002", projects, "2026-08-06T01:00:00+00:00",
    )
    before = _sidecar(projects)
    named = collector.persist_latest_paid_buyer_reply(
        _capture_that_lost_our_attachment(), "91000002", projects, "2026-08-07T01:00:00+00:00",
    )
    assert named == {
        "requirements_path": str(
            projects / "91000002" / "requirements" / "live-buyer-reply.json"
        ),
        "feedback_sha256": before["feedback_sha256"],
        "stage": before["buyer_feedback_stage"],
    }
    # The current request is reported, never re-derived from the truncated window.
    assert _sidecar(projects)["feedback_sha256"] == before["feedback_sha256"]


def test_a_truncated_capture_reports_nothing_when_no_sidecar_names_a_request(tmp_path):
    """With no durable record to re-surface, the honest answer is still None."""
    projects = tmp_path / "projects"
    assert collector.persist_latest_paid_buyer_reply(
        _capture_that_lost_our_attachment(), "91000002", projects, "2026-08-07T01:00:00+00:00",
    ) is None
    assert not (projects / "91000002" / "requirements" / "live-buyer-reply.json").exists()


def test_no_sidecar_is_invented_for_an_order_that_has_none(tmp_path):
    """Accumulation never creates a requirements file the caller reports as absent."""
    projects = tmp_path / "projects"
    result = collector.persist_latest_paid_buyer_reply(
        _talkroom([
            {"side": "buyer", "text": "先の依頼", "attachments": []},
            {"side": "seller", "text": "v2", "attachments": [{"filename": "v2.zip"}]},
        ]),
        "42", projects, "2026-08-07T01:00:00+00:00",
    )
    assert result is None
    assert not (projects / "42").exists()


def test_an_unchanged_poll_still_rewrites_nothing(tmp_path):
    projects = tmp_path / "projects"
    room = _talkroom([
        {"side": "seller", "text": "v1", "attachments": [{"filename": "v1.zip"}]},
        {"side": "buyer", "text": PASS_TWO_FACT, "attachments": []},
    ])
    collector.persist_latest_paid_buyer_reply(room, "91000002", projects, "2026-08-07T01:00:00+00:00")
    path = projects / "91000002" / "requirements" / "live-buyer-reply.json"
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    collector.persist_latest_paid_buyer_reply(room, "91000002", projects, "2026-08-07T02:00:00+00:00")
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before


def test_an_attachment_only_message_counts_as_a_statement(tmp_path):
    projects = tmp_path / "projects"
    collector.persist_latest_paid_buyer_reply(
        _talkroom([
            {"side": "buyer", "text": "", "attachments": [{"filename": "素材.png"}]},
            {"side": "buyer", "text": PASS_ONE_FACT, "attachments": []},
        ]),
        "91000002", projects, "2026-08-06T01:00:00+00:00",
    )
    rows = _sidecar(projects)["accumulated_requirements"]
    assert ["素材.png"] in [row["attachments"] for row in rows]


def test_accumulated_rows_are_sanitized_like_the_current_request(tmp_path):
    projects = tmp_path / "projects"
    collector.persist_latest_paid_buyer_reply(
        _talkroom([{
            "side": "buyer",
            "text": "資料です secret@example.com https://example.com/x?token=TOPSECRET",
            "attachments": [],
        }]),
        "91000002", projects, "2026-08-06T01:00:00+00:00",
    )
    raw = (projects / "91000002" / "requirements" / "live-buyer-reply.json").read_text(encoding="utf-8")
    assert "TOPSECRET" not in raw
    assert "secret@example.com" not in raw


def test_the_first_accumulation_is_seeded_from_the_talkroom_ledger(tmp_path):
    """An order that has already run for days does not start its ledger empty."""
    projects = tmp_path / "projects"
    ledger = projects / "91000002" / "source" / "talkroom" / "messages.jsonl"
    ledger.parent.mkdir(parents=True)
    ledger.write_text("\n".join([
        json.dumps({"side": "buyer", "sent_at": "2026-08-06T10:00", "text": PASS_ONE_FACT},
                   ensure_ascii=False),
        json.dumps({"side": "seller", "sent_at": "2026-08-06T11:00", "text": "v1です"},
                   ensure_ascii=False),
    ]) + "\n", encoding="utf-8")
    # This snapshot's window has already moved past the first fact.
    collector.persist_latest_paid_buyer_reply(
        _talkroom([
            {"side": "seller", "text": "v1です", "attachments": [{"filename": "v1.pptx"}]},
            {"side": "buyer", "text": PASS_TWO_FACT, "attachments": []},
        ]),
        "91000002", projects, "2026-08-07T01:00:00+00:00",
    )
    accumulated = _accumulated_text(_sidecar(projects))
    assert PASS_ONE_FACT in accumulated
    assert PASS_TWO_FACT in accumulated
    # Our own words are not requirements.
    assert "v1です" not in accumulated


if __name__ == "__main__":  # pragma: no cover - convenience
    raise SystemExit(pytest.main([__file__, "-p", "no:randomly", "-q"]))
