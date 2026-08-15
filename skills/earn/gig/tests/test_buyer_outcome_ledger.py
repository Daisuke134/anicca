"""Run directly: python3 skills/earn/gig/tests/test_buyer_outcome_ledger.py
(NEVER pytest -- the rtk shim blocks it, see repo convention in sibling tests)."""
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "buyer_outcome_ledger.py"
SPEC = importlib.util.spec_from_file_location("buyer_outcome_ledger", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _snapshot(orders):
    return {"version": 1, "captured_at": "2026-08-09T00:00:00+00:00", "orders": orders}


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _read_ledger(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_new_buyer_messages_appended_with_null_reaction():
    tmp = Path(tempfile.mkdtemp())
    try:
        snapshot_path = tmp / "evidence" / "marketplace-snapshot.json"
        _write_json(snapshot_path, _snapshot([
            {
                "talkroom_id": "90000002",
                "request_id": "91000002",
                "talkroom_state": "納品確認待ち",
                "buyer_recent_messages": [
                    {"text": "確認させて頂きました！ほぼ思った通りの仕上がりです！", "attachments": []},
                    {"text": "画像を差し替えると周囲の枠まで一緒に動いてしまいます。", "attachments": ["IMG_0001.jpeg"]},
                ],
            }
        ]))
        ledger = tmp / "buyer-outcomes.jsonl"

        summary = MODULE.scan(snapshot_path, tmp / "projects", ledger)

        assert summary["appended"] == 2, summary
        assert summary["skipped_existing"] == 0, summary
        rows = _read_ledger(ledger)
        assert len(rows) == 2
        assert rows[0]["talkroom_id"] == "90000002"
        assert rows[0]["project_id"] == "91000002"
        assert rows[0]["reaction"] is None
        assert rows[1]["attachments_count"] == 1
        assert rows[0]["phase"] == "納品確認待ち"
        print("PASS test_new_buyer_messages_appended_with_null_reaction")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_dedupe_on_second_run_over_same_snapshot():
    tmp = Path(tempfile.mkdtemp())
    try:
        snapshot_path = tmp / "evidence" / "marketplace-snapshot.json"
        _write_json(snapshot_path, _snapshot([
            {
                "talkroom_id": "90000001",
                "request_id": "91000001",
                "talkroom_state": "取引中",
                "buyer_recent_messages": [{"text": "よろしくお願いします。", "attachments": []}],
            }
        ]))
        ledger = tmp / "buyer-outcomes.jsonl"

        first = MODULE.scan(snapshot_path, tmp / "projects", ledger)
        second = MODULE.scan(snapshot_path, tmp / "projects", ledger)

        assert first["appended"] == 1, first
        assert second["appended"] == 0, second
        assert second["skipped_existing"] == 1, second
        assert len(_read_ledger(ledger)) == 1
        print("PASS test_dedupe_on_second_run_over_same_snapshot")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_rolling_window_across_passes_only_appends_the_new_message():
    """buyer_recent_messages is a last-10 rolling window; a later snapshot that still
    carries an old message plus one new one must append only the new one."""
    tmp = Path(tempfile.mkdtemp())
    try:
        evidence_root = tmp / "evidence"
        pass1 = evidence_root / "gig-pass-1"
        pass2 = evidence_root / "gig-pass-2"
        _write_json(pass1 / "marketplace-snapshot.json", _snapshot([
            {"talkroom_id": "1", "request_id": "1", "talkroom_state": "取引中",
             "buyer_recent_messages": [{"text": "old message", "attachments": []}]},
        ]))
        _write_json(pass2 / "marketplace-snapshot.json", _snapshot([
            {"talkroom_id": "1", "request_id": "1", "talkroom_state": "取引中",
             "buyer_recent_messages": [
                 {"text": "old message", "attachments": []},
                 {"text": "new message", "attachments": []},
             ]},
        ]))
        ledger = tmp / "buyer-outcomes.jsonl"

        first = MODULE.scan(pass1 / "marketplace-snapshot.json", tmp / "projects", ledger)
        second = MODULE.scan(pass2 / "marketplace-snapshot.json", tmp / "projects", ledger)

        assert first["appended"] == 1, first
        assert second["appended"] == 1, second
        rows = _read_ledger(ledger)
        assert {r["text"] for r in rows} == {"old message", "new message"}
        print("PASS test_rolling_window_across_passes_only_appends_the_new_message")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_missing_talkroom_state_falls_back_to_project_state_json():
    tmp = Path(tempfile.mkdtemp())
    try:
        snapshot_path = tmp / "evidence" / "marketplace-snapshot.json"
        _write_json(snapshot_path, _snapshot([
            {"talkroom_id": "9", "request_id": "9",
             "buyer_recent_messages": [{"text": "hi", "attachments": []}]},
        ]))
        projects_root = tmp / "projects"
        _write_json(projects_root / "9" / "state.json", {"queue_class": "buyer_feedback_or_revision"})
        ledger = tmp / "buyer-outcomes.jsonl"

        summary = MODULE.scan(snapshot_path, projects_root, ledger)

        assert summary["appended"] == 1, summary
        rows = _read_ledger(ledger)
        assert rows[0]["phase"] == "buyer_feedback_or_revision"
        print("PASS test_missing_talkroom_state_falls_back_to_project_state_json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_malformed_snapshot_does_not_crash():
    tmp = Path(tempfile.mkdtemp())
    try:
        snapshot_path = tmp / "evidence" / "marketplace-snapshot.json"
        snapshot_path.parent.mkdir(parents=True)
        snapshot_path.write_text("{not valid json", encoding="utf-8")
        ledger = tmp / "buyer-outcomes.jsonl"

        summary = MODULE.scan(snapshot_path, tmp / "projects", ledger)

        assert summary["appended"] == 0, summary
        assert "error" in summary, summary
        assert not ledger.exists()
        print("PASS test_malformed_snapshot_does_not_crash")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_order_without_talkroom_id_and_non_dict_message_are_skipped_not_fatal():
    tmp = Path(tempfile.mkdtemp())
    try:
        snapshot_path = tmp / "evidence" / "marketplace-snapshot.json"
        _write_json(snapshot_path, _snapshot([
            {"request_id": "no-room", "buyer_recent_messages": [{"text": "x", "attachments": []}]},
            {"talkroom_id": "5", "request_id": "5", "buyer_recent_messages": ["not-a-dict", {"text": "ok", "attachments": []}]},
        ]))
        ledger = tmp / "buyer-outcomes.jsonl"

        summary = MODULE.scan(snapshot_path, tmp / "projects", ledger)

        assert summary["appended"] == 1, summary
        rows = _read_ledger(ledger)
        assert rows[0]["text"] == "ok"
        print("PASS test_order_without_talkroom_id_and_non_dict_message_are_skipped_not_fatal")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_main_falls_back_to_freshest_evidence_dir_when_none_given():
    tmp = Path(tempfile.mkdtemp())
    try:
        evidence_root = tmp / "evidence"
        older = evidence_root / "gig-pass-old"
        newer = evidence_root / "gig-pass-new"
        _write_json(older / "marketplace-snapshot.json", _snapshot([
            {"talkroom_id": "1", "request_id": "1", "buyer_recent_messages": [{"text": "old pass", "attachments": []}]},
        ]))
        _write_json(newer / "marketplace-snapshot.json", _snapshot([
            {"talkroom_id": "1", "request_id": "1", "buyer_recent_messages": [{"text": "new pass", "attachments": []}]},
        ]))
        # Force mtime ordering deterministically (dict insertion order in evidence_root
        # is not guaranteed to match creation order across filesystems).
        import os
        import time as time_mod
        os.utime(older, (time_mod.time() - 100, time_mod.time() - 100))
        os.utime(newer, (time_mod.time(), time_mod.time()))

        found = MODULE._freshest_evidence_dir(evidence_root)

        assert found == newer, found
        print("PASS test_main_falls_back_to_freshest_evidence_dir_when_none_given")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_new_buyer_messages_appended_with_null_reaction()
    test_dedupe_on_second_run_over_same_snapshot()
    test_rolling_window_across_passes_only_appends_the_new_message()
    test_missing_talkroom_state_falls_back_to_project_state_json()
    test_malformed_snapshot_does_not_crash()
    test_order_without_talkroom_id_and_non_dict_message_are_skipped_not_fatal()
    test_main_falls_back_to_freshest_evidence_dir_when_none_given()
    print("ALL PASS")
