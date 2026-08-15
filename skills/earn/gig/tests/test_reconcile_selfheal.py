"""Run directly: python3 skills/earn/gig/tests/test_reconcile_selfheal.py
(NEVER pytest -- the rtk shim blocks it, see repo convention in sibling tests)."""
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reconcile_selfheal.py"
SPEC = importlib.util.spec_from_file_location("reconcile_selfheal", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _read_ledger(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _report(tmp: Path, name: str, generated_at: str, *, agree: bool, extra_row: bool = False) -> Path:
    rows = [
        {
            "project_id": "P1",
            "talkroom_id": 9001,
            "status": "ok",
            "checks": [
                {"name": "artifact_visible", "site_value": True, "ledger_value": agree, "agree": agree},
            ],
        }
    ]
    if extra_row:
        rows.append({"project_id": "P2", "talkroom_id": 9002, "status": "skipped_no_state"})
    path = tmp / name
    path.write_text(
        json.dumps({"generated_at": generated_at, "rows": rows}, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _paths(tmp: Path):
    return (
        tmp / ".reconcile-selfheal-state.json",
        tmp / "selfheal-request.jsonl",
        tmp / "state" / ".gig-core-selfheal-request.json",
    )


def test_two_consecutive_disagreements_do_not_qualify():
    tmp = Path(tempfile.mkdtemp())
    try:
        state, ledger, selfheal_req = _paths(tmp)
        r1 = _report(tmp, "r1.json", "t1", agree=False)
        r2 = _report(tmp, "r2.json", "t2", agree=False)

        s1 = MODULE.run(state, ledger, selfheal_req, report_path=r1)
        s2 = MODULE.run(state, ledger, selfheal_req, report_path=r2)

        assert s1["qualified"] == 0, s1
        assert s2["qualified"] == 0, s2
        assert not ledger.exists()
        assert not selfheal_req.exists()
        print("PASS test_two_consecutive_disagreements_do_not_qualify")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_third_consecutive_disagreement_qualifies_and_feeds_entrypoint():
    tmp = Path(tempfile.mkdtemp())
    try:
        state, ledger, selfheal_req = _paths(tmp)
        for i, name in enumerate(["r1.json", "r2.json", "r3.json"]):
            r = _report(tmp, name, f"t{i}", agree=False)
            summary = MODULE.run(state, ledger, selfheal_req, report_path=r)

        assert summary["qualified"] == 1, summary
        assert summary["selfheal_req_written"] is True, summary
        rows = _read_ledger(ledger)
        assert len(rows) == 1, rows
        assert rows[0]["kind"] == "site_ledger_divergence"
        assert rows[0]["check"] == "artifact_visible"
        assert rows[0]["talkroom_id"] == 9001
        req = json.loads(selfheal_req.read_text(encoding="utf-8"))
        assert req["kind"] == "site_ledger_divergence"
        assert req["failure_reason"] == req["reason"]
        print("PASS test_third_consecutive_disagreement_qualifies_and_feeds_entrypoint")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_dedupe_while_open_no_second_request():
    tmp = Path(tempfile.mkdtemp())
    try:
        state, ledger, selfheal_req = _paths(tmp)
        for i, name in enumerate(["r1.json", "r2.json", "r3.json", "r4.json"]):
            r = _report(tmp, name, f"t{i}", agree=False)
            summary = MODULE.run(state, ledger, selfheal_req, report_path=r)
            if i == 3:
                fourth = summary

        assert fourth["qualified"] == 0, fourth  # still disagreeing, but already requested
        rows = _read_ledger(ledger)
        assert len(rows) == 1, rows  # not duplicated on pass 4
        print("PASS test_dedupe_while_open_no_second_request")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_clear_on_agreement_resets_streak_and_allows_a_later_request():
    tmp = Path(tempfile.mkdtemp())
    try:
        state, ledger, selfheal_req = _paths(tmp)
        for i, name in enumerate(["r1.json", "r2.json", "r3.json"]):
            r = _report(tmp, name, f"t{i}", agree=False)
            MODULE.run(state, ledger, selfheal_req, report_path=r)
        rows = _read_ledger(ledger)
        assert len(rows) == 1, rows

        r_clear = _report(tmp, "r4.json", "t4", agree=True)
        cleared_summary = MODULE.run(state, ledger, selfheal_req, report_path=r_clear)
        assert cleared_summary["cleared"] == 1, cleared_summary
        state_doc = json.loads(state.read_text(encoding="utf-8"))
        assert "artifact_visible|9001" not in state_doc["entries"], state_doc

        # Recurrence: needs 3 more consecutive disagreements before a second request fires.
        for i, name in enumerate(["r5.json", "r6.json"]):
            r = _report(tmp, name, f"t5{i}", agree=False)
            s = MODULE.run(state, ledger, selfheal_req, report_path=r)
            assert s["qualified"] == 0, s
        rows = _read_ledger(ledger)
        assert len(rows) == 1, rows  # still just the first request

        selfheal_req.unlink()  # simulate auditor.sh having consumed the singular slot
        r7 = _report(tmp, "r7.json", "t52", agree=False)
        s7 = MODULE.run(state, ledger, selfheal_req, report_path=r7)
        assert s7["qualified"] == 1, s7
        rows = _read_ledger(ledger)
        assert len(rows) == 2, rows
        print("PASS test_clear_on_agreement_resets_streak_and_allows_a_later_request")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_malformed_report_is_skipped_not_fatal():
    tmp = Path(tempfile.mkdtemp())
    try:
        state, ledger, selfheal_req = _paths(tmp)
        bad = tmp / "bad.json"
        bad.write_text("{not json", encoding="utf-8")

        summary = MODULE.run(state, ledger, selfheal_req, report_path=bad)

        assert summary["skipped_reason"].startswith("unreadable_report"), summary
        assert not state.exists()
        assert not ledger.exists()
        print("PASS test_malformed_report_is_skipped_not_fatal")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_report_missing_rows_key_is_skipped_not_fatal():
    tmp = Path(tempfile.mkdtemp())
    try:
        state, ledger, selfheal_req = _paths(tmp)
        shapeless = tmp / "shapeless.json"
        shapeless.write_text(json.dumps({"generated_at": "t1"}), encoding="utf-8")

        summary = MODULE.run(state, ledger, selfheal_req, report_path=shapeless)

        assert summary["skipped_reason"] == "malformed_report_shape", summary
        print("PASS test_report_missing_rows_key_is_skipped_not_fatal")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_malformed_row_inside_a_valid_report_is_counted_and_skipped():
    tmp = Path(tempfile.mkdtemp())
    try:
        state, ledger, selfheal_req = _paths(tmp)
        path = tmp / "partial-bad-row.json"
        path.write_text(
            json.dumps({
                "generated_at": "t1",
                "rows": [
                    {"project_id": "P1", "status": "ok", "checks": []},  # missing talkroom_id
                    {
                        "project_id": "P2", "talkroom_id": 9002, "status": "ok",
                        "checks": [{"name": "control_disabled", "agree": True}],
                    },
                ],
            }),
            encoding="utf-8",
        )

        summary = MODULE.run(state, ledger, selfheal_req, report_path=path)

        assert summary["skipped_malformed_rows"] == 1, summary
        print("PASS test_malformed_row_inside_a_valid_report_is_counted_and_skipped")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_missing_report_is_a_clean_noop():
    tmp = Path(tempfile.mkdtemp())
    try:
        state, ledger, selfheal_req = _paths(tmp)

        summary = MODULE.run(state, ledger, selfheal_req, report_path=tmp / "does-not-exist.json")

        assert summary["skipped_reason"] == "no_report_found", summary
        assert not state.exists()
        print("PASS test_missing_report_is_a_clean_noop")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_rerun_over_same_report_does_not_double_count_streak():
    tmp = Path(tempfile.mkdtemp())
    try:
        state, ledger, selfheal_req = _paths(tmp)
        r1 = _report(tmp, "r1.json", "t1", agree=False)

        MODULE.run(state, ledger, selfheal_req, report_path=r1)
        second = MODULE.run(state, ledger, selfheal_req, report_path=r1)  # same generated_at

        assert second["skipped_reason"] == "already_scored_this_report", second
        state_doc = json.loads(state.read_text(encoding="utf-8"))
        assert state_doc["entries"]["artifact_visible|9001"]["streak"] == 1, state_doc
        print("PASS test_rerun_over_same_report_does_not_double_count_streak")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_dry_run_writes_nothing():
    tmp = Path(tempfile.mkdtemp())
    try:
        state, ledger, selfheal_req = _paths(tmp)
        for i, name in enumerate(["r1.json", "r2.json"]):
            r = _report(tmp, name, f"t{i}", agree=False)
            MODULE.run(state, ledger, selfheal_req, report_path=r)
        r3 = _report(tmp, "r3.json", "t3", agree=False)

        summary = MODULE.run(state, ledger, selfheal_req, report_path=r3, dry_run=True)

        assert summary["qualified"] == 1, summary  # would qualify
        assert not ledger.exists()  # but nothing written
        state_doc = json.loads(state.read_text(encoding="utf-8"))
        assert state_doc["last_report_generated_at"] == "t1"  # state not advanced by dry-run
        print("PASS test_dry_run_writes_nothing")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_pending_selfheal_req_is_not_clobbered_but_ledger_still_appends():
    tmp = Path(tempfile.mkdtemp())
    try:
        state, ledger, selfheal_req = _paths(tmp)
        selfheal_req.parent.mkdir(parents=True, exist_ok=True)
        selfheal_req.write_text(json.dumps({"kind": "timeout", "reason": "pending", "ts": 1}), encoding="utf-8")

        for i, name in enumerate(["r1.json", "r2.json", "r3.json"]):
            r = _report(tmp, name, f"t{i}", agree=False)
            summary = MODULE.run(state, ledger, selfheal_req, report_path=r)

        assert summary["qualified"] == 1, summary
        assert summary["selfheal_req_written"] is False, summary
        req = json.loads(selfheal_req.read_text(encoding="utf-8"))
        assert req["kind"] == "timeout"  # untouched
        rows = _read_ledger(ledger)
        assert len(rows) == 1, rows  # observability still recorded
        print("PASS test_pending_selfheal_req_is_not_clobbered_but_ledger_still_appends")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_two_consecutive_disagreements_do_not_qualify()
    test_third_consecutive_disagreement_qualifies_and_feeds_entrypoint()
    test_dedupe_while_open_no_second_request()
    test_clear_on_agreement_resets_streak_and_allows_a_later_request()
    test_malformed_report_is_skipped_not_fatal()
    test_report_missing_rows_key_is_skipped_not_fatal()
    test_malformed_row_inside_a_valid_report_is_counted_and_skipped()
    test_missing_report_is_a_clean_noop()
    test_rerun_over_same_report_does_not_double_count_streak()
    test_dry_run_writes_nothing()
    test_pending_selfheal_req_is_not_clobbered_but_ledger_still_appends()
    print("ALL PASS")
