"""One unreachable source must not end the pass, and the exit must say which happened.

Measured 2026-09-06: `hf-gig-apply-direct` delivered its report (`message_id 62188`,
`transport: sent`) and still ended `entrypoint_exit_1`, every wake. The only non-empty stderr was
`{"error":"source_not_found:single:new","error_type":"ParentContractError"}`.

A 403 on one source was already absorbed -- recorded, cursor moved on, pass ends ok. A page whose
title matched the not-found pattern was not, so it reached the wrapper as an unrecognised parent
failure and killed the pass. That made two very different things produce the same exit 1: "one of
several sources is missing" and "this lane never reported at all".

Run: python3 -m pytest skills/earn/gig/tests/test_source_failure_absorption.py
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import application_direct  # noqa: E402


def _completed(error: str | None, *, error_type: str = "ParentContractError") -> subprocess.CompletedProcess:
    stderr = ""
    if error is not None:
        stderr = json.dumps({"ok": False, "error": error, "error_type": error_type,
                             "error_at": "application_parent.py:953"}) + "\n"
    return subprocess.CompletedProcess(args=["parent"], returncode=2, stdout="", stderr=stderr)


def test_access_denial_is_recognised_as_a_survivable_source_failure():
    assert application_direct._temporary_source_denial(
        _completed("source_access_denied:single:new")
    ) == ("single:new", "source_access_denied")


def test_not_found_is_recognised_too_and_its_diagnostic_detail_is_not_read_as_the_id():
    """The parent appends the observed title; the id must survive that."""
    observed = application_direct._temporary_source_denial(
        _completed("source_not_found:single:new title='お探しのページは見つかりません | ココナラ'")
    )
    assert observed == ("single:new", "source_not_found")


def test_an_unrelated_contract_error_still_ends_the_pass():
    assert application_direct._temporary_source_denial(
        _completed("snapshot_required_sources_invalid")
    ) is None


def test_a_non_contract_failure_still_ends_the_pass():
    assert application_direct._temporary_source_denial(
        _completed("boom", error_type="RuntimeError")
    ) is None
    assert application_direct._temporary_source_denial(_completed(None)) is None


@pytest.mark.parametrize(
    "kind,temporary",
    [("source_access_denied", True), ("source_not_found", False)],
)
def test_recorded_failure_separates_what_clears_by_itself_from_what_does_not(tmp_path, kind, temporary):
    """A 403 is expected to clear. A page that is not there will not, and must not be retried
    forever under a label that says it is temporary."""
    failures: dict[str, dict] = {}
    application_direct._record_temporary_source_failure(
        tmp_path, failures, "single:new", "refresh", kind,
    )
    assert failures["single:new"] == {
        "source_id": "single:new",
        "phase": "refresh",
        "error": kind,
        "temporary": temporary,
        "exhausted": False,
    }
    written = json.loads((tmp_path / "temporary-source-failures.json").read_text(encoding="utf-8"))
    assert written["sources"] == [failures["single:new"]]


def test_the_default_kind_stays_access_denied_for_callers_that_pass_none():
    failures: dict[str, dict] = {}
    application_direct._record_temporary_source_failure(
        Path("/tmp"), failures, "single:new", "refresh",
    )
    assert failures["single:new"]["error"] == "source_access_denied"
