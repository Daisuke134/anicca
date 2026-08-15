"""Run directly: python3 skills/earn/gig/tests/test_selfimprove_consumer.py
(NEVER pytest -- the rtk shim blocks it, see repo convention in sibling tests)."""
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "selfimprove_consumer.py"
SPEC = importlib.util.spec_from_file_location("selfimprove_consumer", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _read_ledger(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _gap_row(ts: int, missing: list[str]) -> str:
    return json.dumps({
        "ts": ts,
        "evidence": {},
        "missing": missing,
        "verification_mode": "material_or_improve",
        "ledger_diagnostics": {"applied.jsonl": {"malformed_count": 0, "details": []}},
    }, ensure_ascii=False)


def _noop_row(ts: int) -> str:
    return json.dumps({
        "ts": ts,
        "evidence": {},
        "missing": [],
        "verification_mode": "normal_noop",
        "ledger_diagnostics": {"applied.jsonl": {"malformed_count": 0, "details": []}},
    }, ensure_ascii=False)


def _malformed_ledger_row(ts: int) -> str:
    return json.dumps({
        "ts": ts,
        "evidence": {},
        "missing": [],
        "verification_mode": "normal_noop",
        "ledger_diagnostics": {"applied.jsonl": {"malformed_count": 2, "details": [{"line": 3}]}},
    }, ensure_ascii=False)


def _paths(tmp: Path, *, seed_cursor: bool = True):
    cursor = tmp / ".selfimprove-consumer-cursor"
    if seed_cursor:
        # Simulate the post-first-run steady state: the first-ever live run only initializes
        # the cursor at EOF (pinned by test_first_run_initializes_cursor_at_eof_and_processes
        # _nothing); every other test exercises the state where a cursor already exists.
        cursor.write_text("0", encoding="utf-8")
    return (
        tmp / "selfimprove-audit.jsonl",
        cursor,
        tmp / "selfheal-request.jsonl",
        tmp / "state" / ".gig-core-selfheal-request.json",
    )


def test_qualifying_gap_row_produces_one_request_and_feeds_entrypoint():
    tmp = Path(tempfile.mkdtemp())
    try:
        audit, cursor, ledger, selfheal_req = _paths(tmp)
        _write_lines(audit, [_gap_row(100, ["self_check", "apply_volume"])])

        summary = MODULE.run(audit, cursor, ledger, selfheal_req)

        assert summary["processed"] == 1, summary
        assert summary["qualified"] == 1, summary
        assert summary["selfheal_req_written"] is True, summary
        rows = _read_ledger(ledger)
        assert len(rows) == 1, rows
        assert rows[0]["kind"] == "selfimprove_gap"
        assert rows[0]["source_ts"] == 100
        assert "self_check" in rows[0]["reason"] and "apply_volume" in rows[0]["reason"]
        req = json.loads(selfheal_req.read_text(encoding="utf-8"))
        assert req["kind"] == "selfimprove_gap"
        assert req["reason"] and req["failure_reason"] == req["reason"]
        print("PASS test_qualifying_gap_row_produces_one_request_and_feeds_entrypoint")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_normal_noop_row_never_qualifies():
    tmp = Path(tempfile.mkdtemp())
    try:
        audit, cursor, ledger, selfheal_req = _paths(tmp)
        _write_lines(audit, [_noop_row(100)])

        summary = MODULE.run(audit, cursor, ledger, selfheal_req)

        assert summary["qualified"] == 0, summary
        assert summary["skipped_no_gap"] == 1, summary
        assert not ledger.exists()
        assert not selfheal_req.exists()
        print("PASS test_normal_noop_row_never_qualifies")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_malformed_ledger_diagnostics_qualifies_even_on_noop_pass():
    tmp = Path(tempfile.mkdtemp())
    try:
        audit, cursor, ledger, selfheal_req = _paths(tmp)
        _write_lines(audit, [_malformed_ledger_row(100)])

        summary = MODULE.run(audit, cursor, ledger, selfheal_req)

        assert summary["qualified"] == 1, summary
        rows = _read_ledger(ledger)
        assert "malformed rows in applied.jsonl(2)" in rows[0]["reason"], rows
        print("PASS test_malformed_ledger_diagnostics_qualifies_even_on_noop_pass")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_malformed_json_line_is_skipped_not_fatal():
    tmp = Path(tempfile.mkdtemp())
    try:
        audit, cursor, ledger, selfheal_req = _paths(tmp)
        _write_lines(audit, ["{not json", _gap_row(200, ["self_check"])])

        summary = MODULE.run(audit, cursor, ledger, selfheal_req)

        assert summary["processed"] == 2, summary
        assert summary["skipped_unrecognised"] == 1, summary
        assert summary["qualified"] == 1, summary
        rows = _read_ledger(ledger)
        assert len(rows) == 1, rows
        print("PASS test_malformed_json_line_is_skipped_not_fatal")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_unrecognised_verification_mode_is_skipped_not_fatal():
    tmp = Path(tempfile.mkdtemp())
    try:
        audit, cursor, ledger, selfheal_req = _paths(tmp)
        weird = json.dumps({
            "ts": 100, "missing": ["x"], "verification_mode": "some_future_severity",
            "ledger_diagnostics": {},
        }, ensure_ascii=False)
        _write_lines(audit, [weird, _gap_row(200, ["self_check"])])

        summary = MODULE.run(audit, cursor, ledger, selfheal_req)

        assert summary["skipped_unrecognised"] == 1, summary
        assert summary["qualified"] == 1, summary
        print("PASS test_unrecognised_verification_mode_is_skipped_not_fatal")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_missing_expected_keys_is_skipped_not_fatal():
    tmp = Path(tempfile.mkdtemp())
    try:
        audit, cursor, ledger, selfheal_req = _paths(tmp)
        shapeless = json.dumps({"ts": 100, "note": "no missing/verification_mode keys at all"})
        _write_lines(audit, [shapeless])

        summary = MODULE.run(audit, cursor, ledger, selfheal_req)

        assert summary["skipped_unrecognised"] == 1, summary
        assert summary["qualified"] == 0, summary
        print("PASS test_missing_expected_keys_is_skipped_not_fatal")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_second_run_over_same_rows_is_idempotent():
    tmp = Path(tempfile.mkdtemp())
    try:
        audit, cursor, ledger, selfheal_req = _paths(tmp)
        _write_lines(audit, [_gap_row(100, ["self_check"])])

        first = MODULE.run(audit, cursor, ledger, selfheal_req)
        selfheal_req.unlink()  # simulate auditor.sh having consumed+removed it
        second = MODULE.run(audit, cursor, ledger, selfheal_req)

        assert first["qualified"] == 1, first
        assert second["processed"] == 0, second
        assert second["qualified"] == 0, second
        rows = _read_ledger(ledger)
        assert len(rows) == 1, rows  # not duplicated on the second run
        print("PASS test_second_run_over_same_rows_is_idempotent")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_new_rows_appended_after_a_prior_run_are_still_picked_up():
    tmp = Path(tempfile.mkdtemp())
    try:
        audit, cursor, ledger, selfheal_req = _paths(tmp)
        _write_lines(audit, [_gap_row(100, ["self_check"])])
        MODULE.run(audit, cursor, ledger, selfheal_req)

        with audit.open("a", encoding="utf-8") as handle:
            handle.write(_gap_row(200, ["apply_volume"]) + "\n")
        summary = MODULE.run(audit, cursor, ledger, selfheal_req)

        assert summary["processed"] == 1, summary
        assert summary["qualified"] == 1, summary
        rows = _read_ledger(ledger)
        assert len(rows) == 2, rows
        assert rows[1]["source_ts"] == 200
        print("PASS test_new_rows_appended_after_a_prior_run_are_still_picked_up")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_pending_selfheal_req_is_not_clobbered_but_ledger_still_appends():
    tmp = Path(tempfile.mkdtemp())
    try:
        audit, cursor, ledger, selfheal_req = _paths(tmp)
        selfheal_req.parent.mkdir(parents=True, exist_ok=True)
        selfheal_req.write_text(json.dumps({"kind": "timeout", "reason": "pending", "ts": 1}), encoding="utf-8")
        _write_lines(audit, [_gap_row(100, ["self_check"])])

        summary = MODULE.run(audit, cursor, ledger, selfheal_req)

        assert summary["qualified"] == 1, summary
        assert summary["selfheal_req_written"] is False, summary
        req = json.loads(selfheal_req.read_text(encoding="utf-8"))
        assert req["kind"] == "timeout"  # untouched
        rows = _read_ledger(ledger)
        assert len(rows) == 1, rows  # observability still recorded
        print("PASS test_pending_selfheal_req_is_not_clobbered_but_ledger_still_appends")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_dry_run_writes_nothing_and_reports_what_would_happen():
    tmp = Path(tempfile.mkdtemp())
    try:
        audit, cursor, ledger, selfheal_req = _paths(tmp)
        _write_lines(audit, [_gap_row(100, ["self_check"])])

        summary = MODULE.run(audit, cursor, ledger, selfheal_req, dry_run=True)

        assert summary["qualified"] == 1, summary
        assert summary["sample"]["source_ts"] == 100, summary
        assert not ledger.exists()
        assert not selfheal_req.exists()
        assert cursor.read_text(encoding="utf-8") == "0"  # never advanced by dry-run
        # confirm a REAL run afterwards still sees the row (cursor never advanced by dry-run)
        real = MODULE.run(audit, cursor, ledger, selfheal_req)
        assert real["qualified"] == 1, real
        print("PASS test_dry_run_writes_nothing_and_reports_what_would_happen")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_missing_audit_file_is_a_clean_noop():
    tmp = Path(tempfile.mkdtemp())
    try:
        audit, cursor, ledger, selfheal_req = _paths(tmp)

        summary = MODULE.run(audit, cursor, ledger, selfheal_req)

        assert summary["processed"] == 0, summary
        print("PASS test_missing_audit_file_is_a_clean_noop")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_first_run_initializes_cursor_at_eof_and_processes_nothing():
    tmp = Path(tempfile.mkdtemp())
    try:
        # NO seeded cursor = the first-ever live run, with historical rows already on disk.
        audit, cursor, ledger, selfheal_req = _paths(tmp, seed_cursor=False)
        _write_lines(audit, [_gap_row(100, ["self_check"]), _gap_row(200, ["apply_volume"])])

        first = MODULE.run(audit, cursor, ledger, selfheal_req)

        assert first["processed"] == 0, first
        assert first["qualified"] == 0, first
        assert first["initialized_cursor_at_eof"] == audit.stat().st_size, first
        assert int(cursor.read_text(encoding="utf-8")) == audit.stat().st_size
        assert not ledger.exists()
        assert not selfheal_req.exists()

        # A row appended AFTER going live IS picked up.
        with audit.open("a", encoding="utf-8") as handle:
            handle.write(_gap_row(300, ["funnel"]) + "\n")
        second = MODULE.run(audit, cursor, ledger, selfheal_req)

        assert second["processed"] == 1, second
        assert second["qualified"] == 1, second
        rows = _read_ledger(ledger)
        assert len(rows) == 1 and rows[0]["source_ts"] == 300, rows
        print("PASS test_first_run_initializes_cursor_at_eof_and_processes_nothing")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_first_run_initializes_cursor_at_eof_and_processes_nothing()
    test_qualifying_gap_row_produces_one_request_and_feeds_entrypoint()
    test_normal_noop_row_never_qualifies()
    test_malformed_ledger_diagnostics_qualifies_even_on_noop_pass()
    test_malformed_json_line_is_skipped_not_fatal()
    test_unrecognised_verification_mode_is_skipped_not_fatal()
    test_missing_expected_keys_is_skipped_not_fatal()
    test_second_run_over_same_rows_is_idempotent()
    test_new_rows_appended_after_a_prior_run_are_still_picked_up()
    test_pending_selfheal_req_is_not_clobbered_but_ledger_still_appends()
    test_dry_run_writes_nothing_and_reports_what_would_happen()
    test_missing_audit_file_is_a_clean_noop()
    print("ALL PASS")
