"""E4 prerequisite (26-gig-loop §CC'/§EW' item 4): the model step E2 left open.
Run directly: python3 skills/earn/gig/tests/test_buyer_reaction_classify.py
(NEVER pytest -- the rtk shim blocks it, see repo convention in sibling tests).

Two kinds of test, same split as test_predelivery_score.py: real-subprocess-boundary
tests against buyer_reaction_stub_runner.py (so the summary read, the reaction parse,
and every fail-open path are exercised for real, at zero cost), and pure-function tests
of classify_batch's row-preserving rewrite with an injected classifier callable (no
subprocess at all).
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("buyer_reaction_classify", SCRIPTS / "buyer_reaction_classify.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

STUB_RUNNER = Path(__file__).resolve().parent / "fixtures" / "buyer_reaction_stub_runner.py"
SCHEMA = SCRIPTS.parent / "schemas" / "buyer_reaction.schema.json"


def _write_ledger(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            if isinstance(row, str):
                handle.write(row + "\n")
            else:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_lines(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _row(text: str = "ありがとうございます", reaction=None, **extra) -> dict:
    base = {"ts": 1, "talkroom_id": "1", "project_id": "1", "text": text,
            "attachments_count": 0, "phase": "unknown", "reaction": reaction}
    base.update(extra)
    return base


# ---------------------------------------------------------------------------
# real subprocess boundary, via the stub runner
# ---------------------------------------------------------------------------

def _classify_with_stub(mode: str, tmp: Path) -> str | None:
    import os
    os.environ["GIG_BUYER_REACTION_STUB"] = mode
    try:
        return MODULE.classify_via_runner(
            "満足しています", 0, runner=STUB_RUNNER, schema=SCHEMA, evidence_dir=tmp / "evidence",
        )
    finally:
        del os.environ["GIG_BUYER_REACTION_STUB"]


def test_stub_runner_positive_is_parsed():
    tmp = Path(tempfile.mkdtemp())
    try:
        assert _classify_with_stub("positive", tmp) == "positive"
        print("PASS test_stub_runner_positive_is_parsed")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_stub_runner_invalid_enum_returns_none():
    tmp = Path(tempfile.mkdtemp())
    try:
        assert _classify_with_stub("invalid_enum", tmp) is None
        print("PASS test_stub_runner_invalid_enum_returns_none")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_stub_runner_malformed_result_returns_none():
    tmp = Path(tempfile.mkdtemp())
    try:
        assert _classify_with_stub("malformed", tmp) is None
        print("PASS test_stub_runner_malformed_result_returns_none")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_stub_runner_no_result_returns_none():
    tmp = Path(tempfile.mkdtemp())
    try:
        assert _classify_with_stub("no_result", tmp) is None
        print("PASS test_stub_runner_no_result_returns_none")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_stub_runner_crash_returns_none():
    tmp = Path(tempfile.mkdtemp())
    try:
        assert _classify_with_stub("crash", tmp) is None
        print("PASS test_stub_runner_crash_returns_none")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_missing_runner_returns_none_without_raising():
    tmp = Path(tempfile.mkdtemp())
    try:
        result = MODULE.classify_via_runner(
            "text", 0, runner=tmp / "nonexistent.py", schema=SCHEMA, evidence_dir=tmp / "evidence",
        )
        assert result is None
        print("PASS test_missing_runner_returns_none_without_raising")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# parse_reaction: fails toward None, never toward a guess
# ---------------------------------------------------------------------------

def test_parse_reaction_accepts_enum_values():
    for value in MODULE.REACTIONS:
        assert MODULE.parse_reaction({"reaction": value}) == value
    print("PASS test_parse_reaction_accepts_enum_values")


def test_parse_reaction_rejects_out_of_enum_and_non_dict():
    assert MODULE.parse_reaction({"reaction": "happy"}) is None
    assert MODULE.parse_reaction("positive") is None
    assert MODULE.parse_reaction(None) is None
    assert MODULE.parse_reaction({}) is None
    print("PASS test_parse_reaction_rejects_out_of_enum_and_non_dict")


# ---------------------------------------------------------------------------
# classify_batch: pure orchestration, injected classifier, no subprocess
# ---------------------------------------------------------------------------

def test_classify_batch_fills_unclassified_rows_and_preserves_row_count():
    tmp = Path(tempfile.mkdtemp())
    try:
        ledger = tmp / "buyer-outcomes.jsonl"
        _write_ledger(ledger, [_row("great"), _row("ok", reaction="positive"), _row("bad")])

        summary = MODULE.classify_batch(ledger, classifier=lambda text, n: "positive")

        assert summary["total_rows"] == 3, summary
        assert summary["unclassified_before"] == 2, summary
        assert summary["classified"] == 2, summary
        rows = [json.loads(line) for line in _read_lines(ledger)]
        assert len(rows) == 3
        assert all(r["reaction"] == "positive" for r in rows)
        print("PASS test_classify_batch_fills_unclassified_rows_and_preserves_row_count")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_classify_batch_bounded_by_limit():
    tmp = Path(tempfile.mkdtemp())
    try:
        ledger = tmp / "buyer-outcomes.jsonl"
        _write_ledger(ledger, [_row(f"msg-{i}") for i in range(5)])

        summary = MODULE.classify_batch(ledger, classifier=lambda text, n: "neutral", limit=2)

        assert summary["attempted"] == 2, summary
        assert summary["classified"] == 2, summary
        rows = [json.loads(line) for line in _read_lines(ledger)]
        assert len(rows) == 5, "no row may be dropped"
        assert sum(1 for r in rows if r["reaction"] == "neutral") == 2
        assert sum(1 for r in rows if r["reaction"] is None) == 3
        print("PASS test_classify_batch_bounded_by_limit")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_classify_batch_dry_run_never_calls_classifier():
    tmp = Path(tempfile.mkdtemp())
    try:
        ledger = tmp / "buyer-outcomes.jsonl"
        _write_ledger(ledger, [_row("a"), _row("b")])

        def _boom(text, n):
            raise AssertionError("dry_run must never call the classifier")

        summary = MODULE.classify_batch(ledger, classifier=_boom, dry_run=True)

        assert summary["dry_run"] is True
        assert summary["unclassified_before"] == 2, summary
        assert summary["attempted"] == 2, "dry_run reports the batch it WOULD process"
        assert summary["classified"] == 0, summary
        rows = [json.loads(line) for line in _read_lines(ledger)]
        assert all(r["reaction"] is None for r in rows)
        print("PASS test_classify_batch_dry_run_never_calls_classifier")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_classify_batch_dry_run_respects_limit():
    tmp = Path(tempfile.mkdtemp())
    try:
        ledger = tmp / "buyer-outcomes.jsonl"
        _write_ledger(ledger, [_row(f"msg-{i}") for i in range(5)])

        def _boom(text, n):
            raise AssertionError("dry_run must never call the classifier")

        summary = MODULE.classify_batch(ledger, classifier=_boom, dry_run=True, limit=2)

        assert summary["unclassified_before"] == 5, summary
        assert summary["attempted"] == 2, "bounded by limit, same as a real run would be"
        print("PASS test_classify_batch_dry_run_respects_limit")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_classify_batch_model_failure_leaves_row_null_fail_open():
    tmp = Path(tempfile.mkdtemp())
    try:
        ledger = tmp / "buyer-outcomes.jsonl"
        _write_ledger(ledger, [_row("a"), _row("b")])

        summary = MODULE.classify_batch(ledger, classifier=lambda text, n: None)

        assert summary["failed"] == 2, summary
        assert summary["classified"] == 0, summary
        rows = [json.loads(line) for line in _read_lines(ledger)]
        assert all(r["reaction"] is None for r in rows)
        print("PASS test_classify_batch_model_failure_leaves_row_null_fail_open")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_classify_batch_crashing_classifier_treated_as_failure_not_fatal():
    tmp = Path(tempfile.mkdtemp())
    try:
        ledger = tmp / "buyer-outcomes.jsonl"
        _write_ledger(ledger, [_row("a"), _row("b")])
        calls = []

        def _flaky(text, n):
            calls.append(text)
            if text == "a":
                raise RuntimeError("boom")
            return "negative"

        summary = MODULE.classify_batch(ledger, classifier=_flaky)

        assert len(calls) == 2, "one bad row must not stop the batch"
        assert summary["failed"] == 1, summary
        assert summary["classified"] == 1, summary
        rows = [json.loads(line) for line in _read_lines(ledger)]
        assert len(rows) == 2
        print("PASS test_classify_batch_crashing_classifier_treated_as_failure_not_fatal")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_classify_batch_never_drops_a_torn_line():
    tmp = Path(tempfile.mkdtemp())
    try:
        ledger = tmp / "buyer-outcomes.jsonl"
        _write_ledger(ledger, [_row("a"), "{not valid json", _row("b")])

        summary = MODULE.classify_batch(ledger, classifier=lambda text, n: "positive")

        lines_out = _read_lines(ledger)
        assert len(lines_out) == 3, "row count in must equal row count out"
        assert "{not valid json" in lines_out
        print("PASS test_classify_batch_never_drops_a_torn_line")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_classify_batch_idempotent_second_run_is_a_noop():
    tmp = Path(tempfile.mkdtemp())
    try:
        ledger = tmp / "buyer-outcomes.jsonl"
        _write_ledger(ledger, [_row("a"), _row("b")])

        first = MODULE.classify_batch(ledger, classifier=lambda text, n: "positive")
        before = ledger.read_text(encoding="utf-8")
        second = MODULE.classify_batch(ledger, classifier=lambda text, n: "positive")

        assert first["classified"] == 2, first
        assert second["unclassified_before"] == 0, second
        assert second["classified"] == 0, second
        assert ledger.read_text(encoding="utf-8") == before
        print("PASS test_classify_batch_idempotent_second_run_is_a_noop")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_classify_batch_missing_ledger_returns_zeroed_summary():
    tmp = Path(tempfile.mkdtemp())
    try:
        summary = MODULE.classify_batch(tmp / "no-such-file.jsonl", classifier=lambda text, n: "positive")
        assert summary["total_rows"] == 0, summary
        assert summary["unclassified_before"] == 0, summary
        print("PASS test_classify_batch_missing_ledger_returns_zeroed_summary")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_stub_runner_positive_is_parsed()
    test_stub_runner_invalid_enum_returns_none()
    test_stub_runner_malformed_result_returns_none()
    test_stub_runner_no_result_returns_none()
    test_stub_runner_crash_returns_none()
    test_missing_runner_returns_none_without_raising()
    test_parse_reaction_accepts_enum_values()
    test_parse_reaction_rejects_out_of_enum_and_non_dict()
    test_classify_batch_fills_unclassified_rows_and_preserves_row_count()
    test_classify_batch_bounded_by_limit()
    test_classify_batch_dry_run_never_calls_classifier()
    test_classify_batch_dry_run_respects_limit()
    test_classify_batch_model_failure_leaves_row_null_fail_open()
    test_classify_batch_crashing_classifier_treated_as_failure_not_fatal()
    test_classify_batch_never_drops_a_torn_line()
    test_classify_batch_idempotent_second_run_is_a_noop()
    test_classify_batch_missing_ledger_returns_zeroed_summary()
    print("ALL PASS")
