"""The compiler's first tests. It ran every pass for weeks with none, and unread.

``project_context_compiler`` wrote ``context/current.json`` and a receipts ledger on every
pass, and no code in the repository read either file back -- equipped and unwired, the
same shape as the fence. These tests pin what it now compiles (content, not only refs),
what it must never lose (a requirement stated once, our own promise), and the budget that
keeps it affordable in a prompt.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "project_context_compiler.py"
SPEC = importlib.util.spec_from_file_location("project_context_compiler", SCRIPT)
compiler = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compiler)

OLD_FACT = "デッキは4枚構成でお願いします"
NEW_REQUEST = "タイトルの色を濃くしてください"
OUR_PROMISE = "最短でご購入当日から翌日中を目安に初稿をご提出します"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "projects" / "91000002"
    _write(root / "state.json", json.dumps({
        "request_id": "91000002", "talkroom_id": "90000002", "work_state": "WORK_REQUIRED",
    }, ensure_ascii=False))
    _write(root / "events.jsonl", json.dumps({"ts": 1, "event": "observed"}) + "\n")
    _write(root / "source" / "posting" / "request-91000002.json", json.dumps({
        "version": 1, "request_id": "91000002", "title": "Canvaを活用した画像デザイン",
        "url": "https://coconala.com/requests/91000002",
        "body": "枚数\n4枚\n希望イメージ\nシンプル\n納品ファイル形式\nTTPX",
        "body_bytes": 60, "body_sha256": "a" * 64,
    }, ensure_ascii=False))
    _write(root / "source" / "dm" / "thread-90000007-full.json", json.dumps({
        "version": 1, "thread_id": "90000007", "message_count": 2,
        "messages": [
            {"side": "buyer", "sent_at": "2026-08-06 15:44:01", "text": "この画像をCanvaデータに",
             "attachments": [{"url": "https://coconala.com/a.png", "filename": "素材.png"}]},
            {"side": "seller", "sent_at": "2026-08-06 15:46:41", "text": OUR_PROMISE,
             "attachments": []},
        ],
        "attachment_index": [
            {"filename": "素材.png", "bytes": 2433925, "sha256": "b" * 64,
             "path": str(root / "source" / "dm" / "attachments" / "bbbbbbbbbbbb-素材.png")},
        ],
    }, ensure_ascii=False))
    _write(root / "source" / "talkroom" / "messages.jsonl", "\n".join(
        json.dumps(row, ensure_ascii=False) for row in [
            {"side": "buyer", "sent_at": "2026-08-06T10:00", "text": OLD_FACT},
            {"side": "seller", "sent_at": "2026-08-06T11:00", "text": "承知しました。本日中に着手します"},
            {"side": "buyer", "sent_at": "2026-08-07T09:00", "text": NEW_REQUEST},
        ]
    ) + "\n")
    _write(root / "requirements" / "live-buyer-reply.json", json.dumps({
        "version": 1, "buyer_feedback_stage": "revision", "feedback_sha256": "c" * 64,
        "feedback_text": NEW_REQUEST,
        "accumulated_requirements": [
            {"sha256": "d" * 64, "sent_at": "2026-08-06T10:00", "text": OLD_FACT, "attachments": []},
            {"sha256": "e" * 64, "sent_at": "2026-08-07T09:00", "text": NEW_REQUEST, "attachments": []},
        ],
        "accumulated_sha256": "f" * 64,
    }, ensure_ascii=False))
    return root


def _queue(root: Path, tmp_path: Path) -> dict[str, object]:
    evidence = tmp_path / "evidence" / "talkroom-90000002.json"
    _write(evidence, json.dumps({"talkroom_id": "90000002"}))
    return {
        "request_id": "91000002", "talkroom_id": "90000002",
        "queue_class": "buyer_feedback_or_revision", "delivery_action": "work_required",
        "talkroom_evidence_file": str(evidence),
        "buyer_feedback_sha256": "c" * 64,
        "talkroom_observed_at": "2026-08-07T11:00:00+00:00",
    }


def test_all_four_sources_are_compiled_not_just_referenced(tmp_path):
    root = _project(tmp_path)
    compiled = compiler.compile_context(root, _queue(root, tmp_path))
    combined = compiled["combined_context"]
    assert combined["sources_present"] == [
        "dm", "our_commitments", "posting", "requirements", "talkroom",
    ]
    assert "4枚" in combined["posting"]["body"]
    assert combined["dm"]["threads"][0]["thread_id"] == "90000007"
    assert combined["requirements"]["current_request"] == NEW_REQUEST


def test_a_requirement_stated_before_the_last_delivery_is_still_in_the_context(tmp_path):
    root = _project(tmp_path)
    combined = compiler.compile_context(root, _queue(root, tmp_path))["combined_context"]
    stated = [row["text"] for row in combined["requirements"]["everything_the_buyer_has_asked_for"]]
    assert OLD_FACT in stated
    assert NEW_REQUEST in stated


def test_our_own_promise_is_part_of_the_context(tmp_path):
    """2026-08-06 15:46: we promised a draft within a day and then could not see it."""
    root = _project(tmp_path)
    combined = compiler.compile_context(root, _queue(root, tmp_path))["combined_context"]
    promises = [row["text"] for row in combined["our_commitments"]]
    assert OUR_PROMISE in promises
    assert "承知しました。本日中に着手します" in promises
    assert {row["source"] for row in combined["our_commitments"]} == {"dm", "talkroom"}


def test_the_attachment_index_is_carried_and_the_bytes_are_not(tmp_path):
    root = _project(tmp_path)
    combined = compiler.compile_context(root, _queue(root, tmp_path))["combined_context"]
    index = combined["dm"]["threads"][0]["attachment_index"]
    assert index[0]["filename"] == "素材.png"
    assert index[0]["bytes"] == 2433925
    assert index[0]["path"].endswith("bbbbbbbbbbbb-素材.png")


def test_read_these_first_names_every_file_the_builder_must_open(tmp_path):
    root = _project(tmp_path)
    combined = compiler.compile_context(root, _queue(root, tmp_path))["combined_context"]
    named = " ".join(combined["read_these_first"])
    for fragment in ("source/posting", "source/dm/thread-90000007-full.json",
                     "requirements/live-buyer-reply.json", "source/talkroom/messages.jsonl"):
        assert fragment in named


def test_the_digest_stays_inside_its_prompt_budget(tmp_path):
    root = _project(tmp_path)
    # A talkroom that has run for months, and a posting far longer than any real one.
    _write(root / "source" / "talkroom" / "messages.jsonl", "\n".join(
        json.dumps({"side": "buyer" if index % 2 else "seller",
                    "sent_at": f"2026-08-{index % 28 + 1:02d}T10:00",
                    "text": "長文の要望 " * 200}, ensure_ascii=False)
        for index in range(400)
    ) + "\n")
    payload = json.loads((root / "requirements" / "live-buyer-reply.json").read_text(encoding="utf-8"))
    payload["accumulated_requirements"] = [
        {"sha256": f"{index:064d}", "sent_at": "2026-08-06T10:00",
         "text": "要望 " * 500, "attachments": []}
        for index in range(200)
    ]
    _write(root / "requirements" / "live-buyer-reply.json", json.dumps(payload, ensure_ascii=False))
    combined = compiler.compile_context(root, _queue(root, tmp_path))["combined_context"]
    assert combined["bytes"] <= compiler.COMBINED_MAX_BYTES
    # Bounded, not emptied: the newest requirements and the paths survive.
    assert combined["requirements"]["everything_the_buyer_has_asked_for"]
    assert combined["read_these_first"]


def test_a_project_with_nothing_collected_yet_compiles_without_inventing_sources(tmp_path):
    root = tmp_path / "projects" / "91000002"
    _write(root / "state.json", json.dumps({"request_id": "91000002", "talkroom_id": "90000002"}))
    combined = compiler.compile_context(root, _queue(root, tmp_path))["combined_context"]
    assert combined["sources_present"] == []
    assert combined["read_these_first"] == []


def test_identity_is_required_because_a_context_without_an_order_is_not_one(tmp_path):
    root = tmp_path / "projects" / "orphan"
    root.mkdir(parents=True)
    with pytest.raises(ValueError):
        compiler.compile_context(root, {})


def test_compiling_twice_over_unchanged_inputs_gives_the_same_hash(tmp_path):
    root = _project(tmp_path)
    queue = _queue(root, tmp_path)
    assert (
        compiler.compile_context(root, queue)["project_context_sha256"]
        == compiler.compile_context(root, queue)["project_context_sha256"]
    )


def test_the_cli_writes_the_context_and_a_receipt(tmp_path, capsys):
    root = _project(tmp_path)
    queue_path = tmp_path / "queue-item.json"
    queue_path.write_text(json.dumps(_queue(root, tmp_path), ensure_ascii=False), encoding="utf-8")
    output = root / "context" / "current.json"
    exit_code = _run_cli(queue_path, root, output)
    assert exit_code == 0
    report = json.loads(capsys.readouterr().out.strip())
    assert report["combined_sources"] == [
        "dm", "our_commitments", "posting", "requirements", "talkroom",
    ]
    assert report["combined_context_bytes"] == json.loads(
        output.read_text(encoding="utf-8")
    )["combined_context"]["bytes"]
    receipts = (root / "context" / "context-read-receipts.jsonl").read_text(encoding="utf-8")
    assert receipts.count("\n") == 1


def test_an_impossible_digest_collapses_to_paths_instead_of_failing_the_lane(tmp_path):
    """The block travels inside a hard-bounded packet; refusing to build fails PAID_WORK."""
    root = _project(tmp_path)
    threads = root / "source" / "dm"
    for index in range(40):
        _write(threads / f"thread-100561{index:02d}-full.json", json.dumps({
            "version": 1, "thread_id": f"100561{index:02d}", "message_count": 10,
            "messages": [
                {"side": "buyer", "sent_at": "2026-08-06 15:44:01", "text": "要望 " * 400,
                 "attachments": []}
                for _ in range(10)
            ],
            "attachment_index": [],
        }, ensure_ascii=False))
    combined = compiler.compile_context(root, _queue(root, tmp_path))["combined_context"]
    assert combined["bytes"] <= compiler.COMBINED_MAX_BYTES
    assert "collapsed_to_paths" in combined["truncated"]
    assert combined["read_these_first"]
    assert combined["requirements"]["current_request"] == NEW_REQUEST


# ---------------------------------------------------------------------------
# A9. What was ordered.
#
# 91000001, 2026-08-07 23:36: the builder was given 題材『パズルクエストX』 and
# 納品はGoogleドキュメントで and produced a general guide to the game. Measured on that
# pass, `grep -c 企画 PAID_WORK.prompt.txt` == 0 -- the order's own name,
# 「ポケモン動画の企画・台本作成ができる方を募集します」, reached nothing.


def test_the_order_name_comes_from_the_durable_store_not_the_builders_own_tree(tmp_path, monkeypatch):
    """A8's precedence, reused: ~/gig/postings outranks the project's writable copy."""
    root = _project(tmp_path)
    store = tmp_path / "postings"
    store.mkdir()
    (store / "request-91000002.json").write_text(json.dumps({
        "title": "Canvaを使った画像編集・デザイン制作をお願いできる方を募集します",
    }, ensure_ascii=False), encoding="utf-8")
    # The project copy says something else; the store must win.
    _write(root / "source" / "posting" / "request-91000002.json", json.dumps({
        "title": "書き換えられた依頼名", "body": "枚数\n4枚",
    }, ensure_ascii=False))
    monkeypatch.setenv("GIG_POSTING_STORE", str(store))
    order = compiler.compile_context(root, _queue(root, tmp_path))["combined_context"]["order"]
    assert order["title"] == "Canvaを使った画像編集・デザイン制作をお願いできる方を募集します"
    assert order["title_source"] == "posting_store"


def test_a_direct_offer_with_no_posting_still_carries_what_was_ordered(tmp_path, monkeypatch):
    """★The case that caused the incident.★

    B6 measured source/posting/ in 1 of 9 projects. 91000001 arrived as offer:92000015, an
    order we never applied to, so no posting was ever harvested -- for it the marketplace
    order label on the queue item is the only carrier that exists.
    """
    root = tmp_path / "projects" / "91000001"
    _write(root / "state.json", json.dumps({"request_id": "91000001", "talkroom_id": "90000001"}))
    monkeypatch.setenv("GIG_POSTING_STORE", str(tmp_path / "empty-store"))
    queue = {
        **_queue(root, tmp_path),
        "request_id": "91000001", "talkroom_id": "90000001",
        "contract_id": "offer:92000015",
        "title": "ポケモン動画の企画・台本作成ができる方を募集します",
        "price_jpy": 5000,
    }
    order = compiler.compile_context(root, queue)["combined_context"]["order"]
    assert "企画" in order["title"] and "台本" in order["title"]
    assert order["title_source"] == "order_label"
    assert order["price_jpy"] == 5000


def test_when_nothing_says_what_to_build_the_context_records_how_it_looked(tmp_path, monkeypatch):
    """Zero is a claim, not a value: the absence names the places that were checked."""
    root = tmp_path / "projects" / "91000001"
    _write(root / "state.json", json.dumps({"request_id": "91000001", "talkroom_id": "90000001"}))
    monkeypatch.setenv("GIG_POSTING_STORE", str(tmp_path / "empty-store"))
    order = compiler.compile_context(root, _queue(root, tmp_path))["combined_context"]["order"]
    assert order["title"] is None
    assert order["title_source"] == "none"
    looked = " ".join(order["looked_in"])
    assert "empty-store" in looked
    assert "source/posting/request-*.json" in looked
    assert "queue_item.title" in looked


def test_what_was_ordered_survives_the_collapse_to_paths(tmp_path, monkeypatch):
    """The last field worth dropping. A builder with the latest message and no order name
    is exactly the 91000001 state, and this costs ~120 bytes."""
    root = _project(tmp_path)
    monkeypatch.setenv("GIG_POSTING_STORE", str(tmp_path / "empty-store"))
    threads = root / "source" / "dm"
    for index in range(40):
        _write(threads / f"thread-100561{index:02d}-full.json", json.dumps({
            "version": 1, "thread_id": f"100561{index:02d}", "message_count": 10,
            "messages": [
                {"side": "buyer", "sent_at": "2026-08-06 15:44:01", "text": "要望 " * 400,
                 "attachments": []}
                for _ in range(10)
            ],
            "attachment_index": [],
        }, ensure_ascii=False))
    combined = compiler.compile_context(root, _queue(root, tmp_path))["combined_context"]
    assert "collapsed_to_paths" in combined["truncated"]
    assert combined["bytes"] <= compiler.COMBINED_MAX_BYTES
    assert combined["order"]["title"] == "Canvaを活用した画像デザイン"


def test_the_order_is_not_counted_as_one_of_the_four_collected_sources(tmp_path):
    """It is the identity of the work, assembled from whichever source has it."""
    root = _project(tmp_path)
    combined = compiler.compile_context(root, _queue(root, tmp_path))["combined_context"]
    assert "order" not in combined["sources_present"]
    assert combined["order"]["title"]


def test_the_cli_reports_where_the_order_name_came_from(tmp_path, capsys, monkeypatch):
    """So a pass log shows "none" the moment an order arrives naming nothing."""
    root = _project(tmp_path)
    monkeypatch.setenv("GIG_POSTING_STORE", str(tmp_path / "empty-store"))
    queue_path = tmp_path / "queue-item.json"
    queue_path.write_text(json.dumps(_queue(root, tmp_path), ensure_ascii=False), encoding="utf-8")
    assert _run_cli(queue_path, root, root / "context" / "current.json") == 0
    assert json.loads(capsys.readouterr().out.strip())["order_title_source"] == "project_posting"


def _run_cli(queue_path: Path, root: Path, output: Path) -> int:
    import sys
    argv = sys.argv
    sys.argv = [
        "project_context_compiler.py",
        "--project-root", str(root),
        "--queue-item", str(queue_path),
        "--output", str(output),
    ]
    try:
        return compiler.main()
    finally:
        sys.argv = argv


if __name__ == "__main__":  # pragma: no cover - convenience
    raise SystemExit(pytest.main([__file__, "-p", "no:randomly", "-q"]))
