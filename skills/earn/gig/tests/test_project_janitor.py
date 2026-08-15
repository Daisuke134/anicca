"""Run directly: python3 skills/earn/gig/tests/test_project_janitor.py
(NEVER pytest -- the rtk shim blocks it, see repo convention in sibling tests)."""
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "project_janitor.py"
SPEC = importlib.util.spec_from_file_location("project_janitor", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _make_project(root: Path, project_id: str, transaction_state, *, with_state=True):
    proj = root / project_id
    (proj / "source").mkdir(parents=True)
    (proj / "source" / "raw.bin").write_bytes(b"x" * 100)
    (proj / "work").mkdir(parents=True)
    (proj / "work" / "build.tmp").write_bytes(b"y" * 50)
    (proj / "artifacts").mkdir(parents=True)
    (proj / "artifacts" / "final.zip").write_bytes(b"z" * 10)
    (proj / "evidence").mkdir(parents=True)
    (proj / "delivery").mkdir(parents=True)
    (proj / "events.jsonl").write_text('{"ev":"x"}\n', encoding="utf-8")
    if with_state:
        state = {"request_id": project_id}
        if transaction_state is not None:
            state["transaction_state"] = transaction_state
        (proj / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return proj


def test_completed_project_loses_source_and_work_keeps_the_rest():
    tmp = Path(tempfile.mkdtemp())
    try:
        root = tmp / "projects"
        proj = _make_project(root, "111", "取引完了")
        state = json.loads((proj / "state.json").read_text(encoding="utf-8"))
        state.update(
            {
                "official_readback": True,
                "payment_received": True,
                "paid": True,
                "lesson_complete": True,
            }
        )
        (proj / "state.json").write_text(json.dumps(state), encoding="utf-8")
        ledger = tmp / "janitor.jsonl"

        summary = MODULE.scan(root, ledger, dry_run=False)

        assert summary["cleaned"] == 1, summary
        assert summary["errors"] == 0, summary
        assert not (proj / "source").exists()
        assert not (proj / "work").exists()
        assert (proj / "artifacts" / "final.zip").exists()
        assert (proj / "state.json").exists()
        assert (proj / "events.jsonl").exists()
        assert (proj / "evidence").exists()
        assert (proj / "delivery").exists()

        rows = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines()]
        assert len(rows) == 1
        assert rows[0]["project_id"] == "111"
        assert sorted(rows[0]["deleted"]) == ["source", "work"]
        assert rows[0]["bytes_freed"] == 150
        assert rows[0]["transaction_state"] == "取引完了"
        print("PASS test_completed_project_loses_source_and_work_keeps_the_rest")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_awaiting_confirmation_project_is_untouched():
    tmp = Path(tempfile.mkdtemp())
    try:
        root = tmp / "projects"
        proj = _make_project(root, "222", "納品確認待ち")
        ledger = tmp / "janitor.jsonl"

        summary = MODULE.scan(root, ledger, dry_run=False)

        assert summary["cleaned"] == 0, summary
        assert summary["skipped"] == 1, summary
        assert (proj / "source").exists()
        assert (proj / "work").exists()
        assert not ledger.exists()
        print("PASS test_awaiting_confirmation_project_is_untouched")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_in_progress_project_is_untouched():
    tmp = Path(tempfile.mkdtemp())
    try:
        root = tmp / "projects"
        proj = _make_project(root, "333", "取引中")
        ledger = tmp / "janitor.jsonl"

        summary = MODULE.scan(root, ledger, dry_run=False)

        assert summary["cleaned"] == 0, summary
        assert (proj / "source").exists()
        assert (proj / "work").exists()
        print("PASS test_in_progress_project_is_untouched")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_unparseable_state_json_is_untouched_and_does_not_stop_scan():
    tmp = Path(tempfile.mkdtemp())
    try:
        root = tmp / "projects"
        bad = _make_project(root, "444", "取引完了")
        (bad / "state.json").write_text("{not valid json", encoding="utf-8")
        good = _make_project(root, "555", "取引完了")
        ledger = tmp / "janitor.jsonl"

        summary = MODULE.scan(root, ledger, dry_run=False)

        assert summary["errors"] == 1, summary
        assert summary["cleaned"] == 1, summary
        assert (bad / "source").exists()
        assert (bad / "work").exists()
        assert not (good / "source").exists()
        assert not (good / "work").exists()
        print("PASS test_unparseable_state_json_is_untouched_and_does_not_stop_scan")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_missing_transaction_state_key_is_untouched():
    tmp = Path(tempfile.mkdtemp())
    try:
        root = tmp / "projects"
        proj = _make_project(root, "666", None)
        ledger = tmp / "janitor.jsonl"

        summary = MODULE.scan(root, ledger, dry_run=False)

        assert summary["cleaned"] == 0, summary
        assert (proj / "source").exists()
        assert (proj / "work").exists()
        print("PASS test_missing_transaction_state_key_is_untouched")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_completed_reclaim_fails_closed_for_active_shared_uncertain_and_immutable():
    tmp = Path(tempfile.mkdtemp())
    try:
        cases = (
            {"active": True},
            {"active": "pass"},
            {"shared_refs": ["other-project/source/raw.bin"]},
            {
                "work_state": "WORK_REQUIRED",
                "official_readback": {"status": "pending"},
                "payment": {"status": "pending"},
                "lesson": {"status": "open"},
            },
            {
                "official_readback_status": "none",
                "payment_status": "none",
                "lesson_status": "none",
            },
            {
                "queue_class": "buyer_feedback_or_revision",
                "next_action": "await_buyer_feedback",
                "formal_delivery": False,
                "buyer_feedback_pending_artifact": True,
                "talkroom_state": "取引中",
            },
        )
        for index, metadata in enumerate(cases):
            root = tmp / f"projects-{index}"
            proj = _make_project(root, str(index), "取引完了")
            (proj / "state.json").write_text(
                json.dumps({"transaction_state": "取引完了", **metadata}), encoding="utf-8"
            )
            ledger = tmp / f"janitor-{index}.jsonl"
            summary = MODULE.scan(root, ledger, dry_run=False)
            assert summary["cleaned"] == 0 and summary["skipped"] == 1, summary
            assert (proj / "source").exists() and (proj / "work").exists()
            assert not ledger.exists()

        root = tmp / "projects-symlink"
        proj = _make_project(root, "symlink", "取引完了")
        shared = tmp / "shared-source"
        shared.write_bytes(b"shared")
        (proj / "source" / "shared.bin").symlink_to(shared)
        ledger = tmp / "janitor.jsonl"
        summary = MODULE.scan(root, ledger, dry_run=False)
        assert summary["cleaned"] == 0 and summary["skipped"] == 1, summary
        assert (proj / "source" / "shared.bin").is_symlink()
        assert not ledger.exists()

        immutable_root = tmp / ".openclaw" / "state"
        proj = _make_project(immutable_root, "protected", "取引完了")
        ledger = tmp / "janitor.jsonl"
        summary = MODULE.scan(immutable_root, ledger, dry_run=False)
        assert summary["cleaned"] == 0 and summary["errors"] == 1, summary
        assert (proj / "source").exists() and (proj / "work").exists()
        assert not ledger.exists()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_idempotent_second_run_writes_no_new_ledger_row():
    tmp = Path(tempfile.mkdtemp())
    try:
        root = tmp / "projects"
        _make_project(root, "777", "取引完了")
        ledger = tmp / "janitor.jsonl"

        first = MODULE.scan(root, ledger, dry_run=False)
        assert first["cleaned"] == 1, first

        second = MODULE.scan(root, ledger, dry_run=False)
        assert second["cleaned"] == 0, second

        rows = ledger.read_text(encoding="utf-8").splitlines()
        assert len(rows) == 1
        print("PASS test_idempotent_second_run_writes_no_new_ledger_row")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_dry_run_deletes_nothing_and_writes_no_ledger():
    tmp = Path(tempfile.mkdtemp())
    try:
        root = tmp / "projects"
        proj = _make_project(root, "888", "取引完了")
        ledger = tmp / "janitor.jsonl"

        summary = MODULE.scan(root, ledger, dry_run=True)

        assert summary["cleaned"] == 1, summary
        assert summary["would_clean"][0]["project_id"] == "888"
        assert (proj / "source").exists()
        assert (proj / "work").exists()
        assert not ledger.exists()
        print("PASS test_dry_run_deletes_nothing_and_writes_no_ledger")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_already_manually_cleaned_project_produces_no_ledger_row():
    tmp = Path(tempfile.mkdtemp())
    try:
        root = tmp / "projects"
        proj = _make_project(root, "999", "取引完了")
        shutil.rmtree(proj / "source")
        shutil.rmtree(proj / "work")
        ledger = tmp / "janitor.jsonl"

        summary = MODULE.scan(root, ledger, dry_run=False)

        assert summary["cleaned"] == 0, summary
        assert not ledger.exists()
        print("PASS test_already_manually_cleaned_project_produces_no_ledger_row")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_completed_project_loses_source_and_work_keeps_the_rest()
    test_awaiting_confirmation_project_is_untouched()
    test_in_progress_project_is_untouched()
    test_unparseable_state_json_is_untouched_and_does_not_stop_scan()
    test_missing_transaction_state_key_is_untouched()
    test_completed_reclaim_fails_closed_for_active_shared_uncertain_and_immutable()
    test_idempotent_second_run_writes_no_new_ledger_row()
    test_dry_run_deletes_nothing_and_writes_no_ledger()
    test_already_manually_cleaned_project_produces_no_ledger_row()
    print("ALL PASS")
