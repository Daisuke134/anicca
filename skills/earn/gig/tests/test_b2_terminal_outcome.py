"""E7: a terminal B2 result must say WHICH kind of red it is.

Measured 2026-08-07: thirty consecutive passes ended FAILED at step B2 while B2 was
submitting real applications (75 *-submitted.png on disk, 27 of them that day). The
word FAILED carried two unrelated meanings at once -- "the lane could not do its
work" and "the lane did less work than the target" -- and a genuinely broken paid
delivery hid underneath the second one for hours because every pass was red.

These tests pin the split. They also pin the direction that costs money silently:
a lane that really is broken must still fail.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import b2_result_gate as gate  # noqa: E402

GATE = Path(__file__).resolve().parents[1] / "scripts" / "b2_result_gate.py"


# --------------------------------------------------------------------------
# 1. The classifier itself
# --------------------------------------------------------------------------


def test_below_target_is_a_shortfall_not_a_break():
    """2 verified against a target of 8 is a throughput number, not an error."""
    record = gate.classify_terminal_outcome(
        errors=[
            "application_count_mismatch:expected=3:actual=2",
            "under_target_search_not_exhausted",
        ],
        verified_count=2,
        target=8,
    )
    assert record["outcome"] == "shortfall"
    assert record["blocking_errors"] == []
    assert record["verified_applications"] == 2
    assert record["target_applications"] == 8
    assert record["applications_short_of_target"] == 6


def test_zero_applications_with_work_available_is_a_break():
    """The one under-target case that IS a failure: eligible work, nothing applied."""
    record = gate.classify_terminal_outcome(
        errors=[
            "application_count_mismatch:expected=5:actual=0",
            "under_target_search_not_exhausted",
        ],
        verified_count=0,
        target=8,
    )
    assert record["outcome"] == "broken"
    assert record["reason"] == "zero_applications_with_work_available"
    assert record["eligible_work_available"] == 5


def test_zero_applications_with_no_work_available_is_not_a_break():
    """An empty marketplace is not a malfunction."""
    record = gate.classify_terminal_outcome(
        errors=["under_target_search_not_exhausted"],
        verified_count=0,
        target=8,
    )
    assert record["outcome"] == "shortfall"
    assert record["eligible_work_available"] == 0


@pytest.mark.parametrize(
    "error",
    [
        "b2_runner_summary_not_success",
        "b2_result_missing",
        "applications_malformed",
        "application_submit_evidence_missing:91000108",
        "application_ledger_missing:91000108",
        "application_applied_page_readback_missing:91000108",
        "application_ledger_verification_missing:91000108",
        "unreported_submit_evidence:91000108",
        "application_not_eligible:91000108",
        "application_request_duplicate",
        "eligible_marketplace_closed:91000088",
        "context_sha256_mismatch",
        "marketplace_not_observed",
    ],
)
def test_integrity_errors_still_break_the_pass(error):
    """Never downgrade a claim about an application or its evidence."""
    record = gate.classify_terminal_outcome(
        errors=[error, "under_target_search_not_exhausted"],
        verified_count=4,
        target=8,
    )
    assert record["outcome"] == "broken", error
    assert error in record["blocking_errors"]


def test_search_source_evidence_defects_are_recorded_not_deleted():
    """A2/A6-shaped: the signal keeps its own name and its own count."""
    errors = [f"search_source_not_observed:single:category:x{i}" for i in range(61)]
    record = gate.classify_terminal_outcome(
        errors=errors + ["application_count_mismatch:expected=3:actual=2"],
        verified_count=2,
        target=8,
    )
    assert record["outcome"] == "shortfall"
    assert record["evidence_defect_count"] == 61
    assert len(record["evidence_defects"]) == 61


def test_target_met_is_clean():
    record = gate.classify_terminal_outcome(errors=[], verified_count=8, target=8)
    assert record["outcome"] == "clean"


# --------------------------------------------------------------------------
# 2. The CLI the pass actually calls
# --------------------------------------------------------------------------


def _fixture(tmp_path: Path, *, errors, ledger_rows, target=8, pass_id="p1"):
    gate_result = tmp_path / "b2-gate-result.json"
    gate_result.write_text(
        json.dumps({"ok": not errors, "errors": errors}) + "\n", encoding="utf-8"
    )
    context = tmp_path / "b2-context.json"
    context.write_text(
        json.dumps(
            {
                "target_applications": target,
                "target_retainer_applications": 0,
                "required_search_source_ids": [],
            }
        ),
        encoding="utf-8",
    )
    ledger = tmp_path / "applied.jsonl"
    ledger.write_text(
        "".join(json.dumps(row) + "\n" for row in ledger_rows), encoding="utf-8"
    )
    return gate_result, context, ledger


def _verified_row(request_id, pass_id="p1"):
    return {
        "requestId": request_id,
        "pass_id": pass_id,
        "submit_verified": True,
        "applied_page_verified": True,
    }


def _run(tmp_path, errors, ledger_rows, target=8):
    gate_result, context, ledger = _fixture(
        tmp_path, errors=errors, ledger_rows=ledger_rows, target=target
    )
    out = tmp_path / "b2-terminal-outcome.json"
    shortfall = tmp_path / "b2-shortfall.jsonl"
    proc = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "terminal-outcome",
            "--gate-result",
            str(gate_result),
            "--context",
            str(context),
            "--ledger",
            str(ledger),
            "--pass-id",
            "p1",
            "--output",
            str(out),
            "--shortfall-ledger",
            str(shortfall),
        ],
        capture_output=True,
        text=True,
    )
    return proc, out, shortfall


def test_cli_exits_zero_for_a_shortfall_and_records_it(tmp_path):
    proc, out, shortfall = _run(
        tmp_path,
        errors=[
            "application_count_mismatch:expected=3:actual=2",
            "under_target_search_not_exhausted",
        ],
        ledger_rows=[_verified_row("91000108"), _verified_row("91000109")],
    )
    assert proc.returncode == 0, proc.stderr
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["outcome"] == "shortfall"
    assert record["verified_applications"] == 2
    assert record["applications_short_of_target"] == 6
    # The shortfall must survive the pass, in a file a human and D1 can read.
    rows = [
        json.loads(line)
        for line in shortfall.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows[-1]["outcome"] == "shortfall"
    assert rows[-1]["verified_applications"] == 2
    assert rows[-1]["pass_id"] == "p1"


def test_cli_exits_nonzero_when_the_lane_is_broken(tmp_path):
    proc, out, shortfall = _run(
        tmp_path,
        errors=["application_submit_evidence_missing:91000108"],
        ledger_rows=[_verified_row("91000108")],
    )
    assert proc.returncode == 1
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["outcome"] == "broken"
    # A break is recorded too -- the ledger is the record of what happened,
    # not a record of only the good news.
    rows = [
        json.loads(line)
        for line in shortfall.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows[-1]["outcome"] == "broken"


def test_cli_exits_nonzero_when_nothing_was_applied_but_work_existed(tmp_path):
    proc, _out, _shortfall = _run(
        tmp_path,
        errors=[
            "application_count_mismatch:expected=5:actual=0",
            "under_target_search_not_exhausted",
        ],
        ledger_rows=[],
    )
    assert proc.returncode == 1


def test_cli_refuses_an_unreadable_gate_result(tmp_path):
    """Fail closed: an outcome we cannot read is never a shortfall."""
    gate_result = tmp_path / "b2-gate-result.json"
    gate_result.write_text("not json\n", encoding="utf-8")
    context = tmp_path / "b2-context.json"
    context.write_text(json.dumps({"target_applications": 8}), encoding="utf-8")
    ledger = tmp_path / "applied.jsonl"
    ledger.write_text("", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "terminal-outcome",
            "--gate-result",
            str(gate_result),
            "--context",
            str(context),
            "--ledger",
            str(ledger),
            "--pass-id",
            "p1",
            "--output",
            str(tmp_path / "o.json"),
            "--shortfall-ledger",
            str(tmp_path / "s.jsonl"),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0


# --------------------------------------------------------------------------
# 3. Submit proof lives inside the pass evidence dir, not beside it
# --------------------------------------------------------------------------


def test_submit_proof_is_found_inside_the_pass_evidence_directory(tmp_path):
    """Production writes proofs to <root>/gig-pass-<id>/agent-B2/, not to <root>/.

    Measured 2026-08-07: 75 real proofs sat in per-pass directories while a
    non-recursive glob at the root found none, so every verified application was
    reported as application_submit_evidence_missing.
    """
    root = tmp_path / "evidence"
    evidence_dir = root / "gig-pass-1786107605-99603" / "agent-B2"
    evidence_dir.mkdir(parents=True)
    proof = evidence_dir / "gig-1786107605-99603-B2-91000108-submitted.png"
    proof.write_bytes(b"png")
    assert gate._has_fresh_submit_proof(root, "91000108", 0, evidence_dir=evidence_dir)
    assert gate._fresh_submit_ids(root, 0, evidence_dir=evidence_dir) == {"91000108"}


def test_submit_proof_lookup_ignores_other_passes(tmp_path):
    """A later pass's proof must never be counted as this pass's evidence."""
    root = tmp_path / "evidence"
    mine = root / "gig-pass-100-a" / "agent-B2"
    other = root / "gig-pass-200-b" / "agent-B2"
    mine.mkdir(parents=True)
    other.mkdir(parents=True)
    (mine / "gig-100-a-B2-111-submitted.png").write_bytes(b"png")
    (other / "gig-200-b-B2-222-submitted.png").write_bytes(b"png")
    assert gate._fresh_submit_ids(root, 0, evidence_dir=mine) == {"111"}
    assert not gate._has_fresh_submit_proof(root, "222", 0, evidence_dir=mine)


def test_legacy_flat_submit_proof_is_still_honoured(tmp_path):
    """Older passes wrote proofs flat at the evidence root; keep reading them."""
    root = tmp_path / "evidence"
    evidence_dir = root / "gig-pass-1-a" / "agent-B2"
    evidence_dir.mkdir(parents=True)
    (root / "gig-1-a-B2-333-submitted.png").write_bytes(b"png")
    assert gate._has_fresh_submit_proof(root, "333", 0, evidence_dir=evidence_dir)
