"""The DM writer that never existed, tested everywhere except the browser boundary.

Shapes are taken from the real capture of order 91000002 / thread 90000007 on 2026-08-07:
two PNG attachments of 2,433,925 and 2,784,148 bytes, which were the material for the
whole job. No test opens a browser; ``collect`` is exercised with a fake reader so the
discovery order, the single-tab read and the refusal paths are still pinned.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "coconala_dm_collect.py"
SPEC = importlib.util.spec_from_file_location("coconala_dm_collect", SCRIPT)
dm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dm)

OWN = "/users/1234567"
BUYER = "/users/7654321"
PNG_ONE = b"\x89PNG\r\n\x1a\n" + b"first" * 100
PNG_TWO = b"\x89PNG\r\n\x1a\n" + b"second" * 100


def _dom(messages=None, **overrides):
    base = {
        "url": "https://coconala.com/mypage/direct_message/90000007",
        "title": "メッセージ詳細",
        "container_present": True,
        "not_found_present": False,
        "error_present": False,
        "own_user_path": OWN,
        "messages": messages if messages is not None else [
            {
                "message_id": "m1", "author_path": BUYER, "author_name": "買い手B",
                "sent_at": "2026-08-06 15:20:00", "body": "焼き方の写真を送ります",
                "attachments": [
                    {"url": "https://coconala.com/attachment/AA000001.png",
                     "filename": "AA000001-1111-4AAA-9AAA-AAAAAAAA0001.png"},
                    {"url": "https://coconala.com/attachment/BB000002.png",
                     "filename": "BB000002-2222-4BBB-9BBB-BBBBBBBB0002.png"},
                ],
            },
            {
                "message_id": "m2", "author_path": OWN, "author_name": "anicca",
                "sent_at": "2026-08-06 15:46:00",
                "body": "本日中〜明日には初稿をお送りします", "attachments": [],
            },
        ],
    }
    base.update(overrides)
    return base


def _fetch_results(payloads=((PNG_ONE, "AA000001"), (PNG_TWO, "BB000002"))):
    return [
        {
            "url": f"https://coconala.com/attachment/{name}.png",
            "status": 200,
            "content_type": "image/png",
            "bytes": len(payload),
            "data_base64": base64.b64encode(payload).decode("ascii"),
        }
        for payload, name in payloads
    ]


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "projects" / "91000002"
    (root / "source").mkdir(parents=True)
    return root


def test_the_thread_document_separates_our_words_from_theirs(tmp_path):
    document = dm.dm_thread_document(_dom(), "90000007", "2026-08-07T11:00:00+00:00")
    assert [message["side"] for message in document["messages"]] == ["buyer", "seller"]
    assert document["participants"] == [{"user_path": BUYER, "name": "買い手B"}]
    # Our own promise is part of the record. On 2026-08-06 15:46 we promised this buyer a
    # first draft within a day and then could not see that we had.
    assert "初稿" in document["messages"][1]["text"]


def test_attachment_fetch_uses_the_authenticated_session():
    expression = dm.attachment_fetch_expression(["https://coconala.com/attachment/a.png"])
    assert "credentials:'include'" in expression.replace(" ", "")
    assert "await fetch" in expression


def test_attachments_are_written_with_their_bytes_and_indexed(tmp_path):
    root = _project(tmp_path)
    document = dm.dm_thread_document(_dom(), "90000007", "2026-08-07T11:00:00+00:00")
    requests = dm.attachment_requests(document)
    index = dm.store_attachments(root, _fetch_results(), requests)
    assert [row["bytes"] for row in index] == [len(PNG_ONE), len(PNG_TWO)]
    for row, payload in zip(index, (PNG_ONE, PNG_TWO)):
        assert Path(row["path"]).read_bytes() == payload
        assert row["sha256"] == hashlib.sha256(payload).hexdigest()
        assert row["side"] == "buyer"
        assert Path(row["path"]).stat().st_mode & 0o777 == 0o600


def test_a_login_page_is_recorded_as_an_error_not_saved_as_material(tmp_path):
    root = _project(tmp_path)
    document = dm.dm_thread_document(_dom(), "90000007", "2026-08-07T11:00:00+00:00")
    requests = dm.attachment_requests(document)
    results = _fetch_results()
    results[0] = {**results[0], "status": 302, "data_base64": None}
    results[1] = {"url": results[1]["url"], "error": "TypeError: Failed to fetch"}
    index = dm.store_attachments(root, results, requests)
    assert [row["error"] for row in index] == ["http_302", "TypeError: Failed to fetch"]
    assert not list((root / "source" / "dm" / "attachments").glob("*")) if (
        root / "source" / "dm" / "attachments"
    ).is_dir() else True


def test_persist_writes_thread_full_json_and_is_idempotent(tmp_path):
    root = _project(tmp_path)
    document = dm.dm_thread_document(_dom(), "90000007", "2026-08-07T11:00:00+00:00")
    index = dm.store_attachments(root, _fetch_results(), dm.attachment_requests(document))
    first = dm.persist_thread(root, document, index)
    path = Path(first["path"])
    assert path.name == "thread-90000007-full.json"
    assert first["written"] is True
    assert first["attachments_stored"] == 2
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    later = dm.dm_thread_document(_dom(), "90000007", "2026-08-07T12:00:00+00:00")
    second = dm.persist_thread(root, later, index)
    assert second["written"] is False
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before


def test_a_stored_thread_is_found_again_without_re_walking_the_inbox(tmp_path):
    root = _project(tmp_path)
    assert dm.known_thread_id(root) is None
    document = dm.dm_thread_document(_dom(), "90000007", "2026-08-07T11:00:00+00:00")
    dm.persist_thread(root, document, [])
    assert dm.known_thread_id(root) == "90000007"


def test_the_buyer_is_matched_on_identity_not_on_message_text():
    assert dm.thread_matches_buyer(_dom(), "買い手B") is True
    assert dm.thread_matches_buyer(_dom(), "7654321") is True
    assert dm.thread_matches_buyer(_dom(), "someone-else") is False
    # Our own account never counts as the buyer, even when the handle matches.
    assert dm.thread_matches_buyer(_dom(), "1234567") is False


def test_an_unavailable_thread_is_refused_rather_than_stored_empty():
    with pytest.raises(dm.DmCollectError):
        dm.dm_thread_document(_dom(not_found_present=True), "90000007", "")
    with pytest.raises(dm.DmCollectError):
        dm.dm_thread_document(_dom(container_present=False), "90000007", "")
    with pytest.raises(dm.DmCollectError):
        dm.dm_thread_document(_dom(messages=[]), "90000007", "")
    with pytest.raises(dm.DmCollectError):
        dm.dm_thread_document(_dom(own_user_path=""), "90000007", "")


def test_a_filename_cannot_escape_the_project(tmp_path):
    root = _project(tmp_path)
    document = dm.dm_thread_document(_dom(messages=[{
        "message_id": "m1", "author_path": BUYER, "author_name": "買い手B",
        "sent_at": "2026-08-06 15:20:00", "body": "x",
        "attachments": [{"url": "https://coconala.com/attachment/a.png",
                         "filename": "../../../etc/passwd"}],
    }]), "90000007", "")
    index = dm.store_attachments(root, _fetch_results(((PNG_ONE, "a"),)), dm.attachment_requests(document))
    stored = Path(index[0]["path"]).resolve()
    assert stored.is_relative_to((root / "source" / "dm" / "attachments").resolve())


def test_an_attachment_we_never_fetched_is_named_rather_than_omitted(tmp_path):
    """Silence would read as "the buyer sent nothing else"."""
    root = _project(tmp_path)
    document = dm.dm_thread_document(_dom(), "90000007", "")
    index = dm.store_attachments(root, [], dm.attachment_requests(document))
    assert [row["error"] for row in index] == ["not_fetched", "not_fetched"]
    assert [row["filename"] for row in index] == [
        "AA000001-1111-4AAA-9AAA-AAAAAAAA0001.png",
        "BB000002-2222-4BBB-9BBB-BBBBBBBB0002.png",
    ]


def test_collect_walks_the_inbox_only_until_it_finds_the_buyer(tmp_path, monkeypatch):
    root = _project(tmp_path)
    visited: list[str] = []

    def fake_read_dom(helper, url, expression, owner):
        visited.append(url)
        if url == dm.INBOX_URL:
            return {"cards": [
                {"talkroom_url": "https://coconala.com/mypage/direct_message/999", "title": "x"},
                {"talkroom_url": "https://coconala.com/mypage/direct_message/90000007", "title": "y"},
                {"talkroom_url": "https://coconala.com/mypage/direct_message/777", "title": "z"},
            ]}
        if url.endswith("/999"):
            return _dom(messages=[{
                "message_id": "a", "author_path": "/users/9", "author_name": "someone",
                "sent_at": "2026-08-01 10:00:00", "body": "hello", "attachments": [],
            }])
        return _dom()

    monkeypatch.setattr(dm, "_read_dom", fake_read_dom)
    monkeypatch.setattr(dm.collector_module(), "inquiries_from_dom", lambda dom_value: [
        {"talkroom_id": card["talkroom_url"].rsplit("/", 1)[-1]} for card in dom_value["cards"]
    ])
    monkeypatch.setattr(dm, "_read_thread", lambda *a, **k: (_dom(), _fetch_results(), {}))
    result = dm.collect(
        helper=Path("/nonexistent"), project_root=root, buyer="買い手B",
        thread_id=None, observed_at="2026-08-07T11:00:00+00:00",
    )
    assert result["ok"] is True
    assert result["thread_id"] == "90000007"
    assert result["attachments_stored"] == 2
    # The third thread was never opened: discovery stops at the match.
    assert not any(url.endswith("/777") for url in visited)


def test_collect_reports_how_it_looked_when_no_thread_matches(tmp_path, monkeypatch):
    root = _project(tmp_path)
    monkeypatch.setattr(dm, "_read_dom", lambda helper, url, expression, owner: (
        {"cards": [{"talkroom_url": "https://coconala.com/mypage/direct_message/999"}]}
        if url == dm.INBOX_URL else _dom(messages=[{
            "message_id": "a", "author_path": "/users/9", "author_name": "someone",
            "sent_at": "2026-08-01 10:00:00", "body": "hello", "attachments": [],
        }])
    ))
    monkeypatch.setattr(dm.collector_module(), "inquiries_from_dom", lambda dom_value: [
        {"talkroom_id": "999"}
    ])
    result = dm.collect(
        helper=Path("/nonexistent"), project_root=root, buyer="買い手B",
        thread_id=None, observed_at="",
    )
    assert result == {
        "ok": False, "error": "dm_thread_not_found", "buyer": "買い手B",
        "threads_inspected": ["999"],
    }


def test_an_attachment_already_on_disk_is_not_downloaded_again(tmp_path):
    """Five megabytes of PNGs do not need re-fetching every hour to learn nothing."""
    root = _project(tmp_path)
    document = dm.dm_thread_document(_dom(), "90000007", "2026-08-07T11:00:00+00:00")
    requests = dm.attachment_requests(document)
    index = dm.store_attachments(root, _fetch_results(), requests)
    dm.persist_thread(root, document, index)

    stored = dm.already_stored(root, "90000007")
    assert set(stored) == {row["url"] for row in requests}

    # Nothing is fetched this time; the carried rows keep the index whole and in order.
    carried_index = dm.store_attachments(root, [], requests, stored)
    assert [row["sha256"] for row in carried_index] == [row["sha256"] for row in index]
    assert [row["filename"] for row in carried_index] == [row["filename"] for row in index]

    # A file deleted from disk stops being carried, so it is fetched again.
    Path(index[0]["path"]).unlink()
    assert set(dm.already_stored(root, "90000007")) == {requests[1]["url"]}


def test_a_redacted_thread_is_never_rewritten_from_the_live_page(tmp_path):
    """buyer-attachments took a password out of this file; do not put it back."""
    root = _project(tmp_path)
    path = root / "source" / "dm" / "thread-90000007-full.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "version": 1, "thread_id": "90000007", "messages": [
            {"side": "buyer", "text": "パスワードは {{VAULT:pw-a68fae15fdde}} です"},
        ],
    }, ensure_ascii=False), encoding="utf-8")
    before = path.read_bytes()
    document = dm.dm_thread_document(_dom(), "90000007", "2026-08-07T11:00:00+00:00")
    result = dm.persist_thread(root, document, [])
    assert result["refused"] == "vaulted_document_present"
    assert result["written"] is False
    assert path.read_bytes() == before


def test_a_hand_made_capture_is_kept_beside_the_machine_one(tmp_path):
    """90000004's file was written by a human in another shape before this writer existed."""
    root = _project(tmp_path)
    path = root / "source" / "dm" / "thread-90000007-full.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"url": "...", "text": "manual", "files": []}), encoding="utf-8")
    document = dm.dm_thread_document(_dom(), "90000007", "2026-08-07T11:00:00+00:00")
    assert dm.persist_thread(root, document, [])["written"] is True
    assert json.loads(path.read_text(encoding="utf-8"))["message_count"] == 2
    legacy = json.loads(
        (root / "source" / "dm" / "thread-90000007-full.legacy.json").read_text(encoding="utf-8")
    )
    assert legacy["text"] == "manual"


def test_the_index_follows_the_thread_when_one_file_is_new_and_one_is_carried(tmp_path):
    root = _project(tmp_path)
    document = dm.dm_thread_document(_dom(), "90000007", "")
    requests = dm.attachment_requests(document)
    first = dm.store_attachments(root, _fetch_results(), requests)
    carried = {first[0]["url"]: first[0]}
    mixed = dm.store_attachments(root, [_fetch_results()[1]], requests, carried)
    assert [row["filename"] for row in mixed] == [row["filename"] for row in first]


if __name__ == "__main__":  # pragma: no cover - convenience
    raise SystemExit(pytest.main([__file__, "-p", "no:randomly", "-q"]))
