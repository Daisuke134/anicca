from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load():
    spec = importlib.util.spec_from_file_location(
        "application_outcome_summary", SCRIPTS / "application_outcome_summary.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_same_meaning_in_three_spellings_counts_once() -> None:
    # Measured 2026-08-06 in application-decisions.json: the planner writes free text and
    # spells one meaning several ways. Counting raw strings splits one cause into three.
    m = load()
    for text in ("すでに応募済み", "既応募", "already_applied"):
        assert m.normalise_reason(text) == "already"
    for text in ("募集終了", "現在応募受付終了", "applications_closed", "APPLICATIONS_CLOSED"):
        assert m.normalise_reason(text) == "closed"
    for text in ("実写動画編集不可", "real_video_editing_prohibited", "同期的な人間対応", "静岡県内在住が必須"):
        assert m.normalise_reason(text) == "capability"


def test_an_unknown_reason_is_a_capability_limit_and_keeps_its_words() -> None:
    # Superseded on 2026-08-06 by the first real run: a separate "other" bucket only meant
    # "the keyword list is out of date". Unknown wording is still a reason we could not do
    # the work, and summarise() quotes it, so nothing is hidden.
    m = load()
    assert m.normalise_reason("予算が非公開のため判断不能") == "capability"


def test_empty_and_non_string_do_not_crash() -> None:
    # Fail towards "we could not do it" rather than towards "the posting was closed":
    # claiming a posting closed when we never learned why would be a fabricated fact.
    m = load()
    assert m.normalise_reason("") == "capability"
    assert m.normalise_reason(None) == "capability"
    assert m.normalise_reason(42) == "capability"


def commit_results():
    # The exact shape measured in agent-B2/parent-commit.json on 2026-08-06 12:39.
    rows = [{"request_id": str(n), "status": "ineligible"} for n in range(26)]
    rows += [
        {"request_id": "900", "status": "confirmed"},
        {"request_id": "901", "status": "confirmed"},
        {"request_id": "902", "status": "recovered_prepared_confirmed"},
        {"request_id": "903", "status": "submission_runtime_failed:ParentContractError"},
        {"request_id": "904", "status": "submission_failed:form_rejected"},
        {"request_id": "905", "status": "quarantined_wedging_form:count=3"},
    ]
    return rows


def decisions(reasons):
    return {
        "decisions": [
            {"request_id": str(n), "eligibility": "ineligible", "reason_codes": [reason]}
            for n, reason in enumerate(reasons)
        ]
    }


def test_a_pass_that_applied_reports_what_the_rest_of_the_batch_was() -> None:
    m = load()
    summary = m.summarise(
        commit_results(),
        decisions(["募集終了"] * 20 + ["既応募"] * 2 + ["実写動画編集不可"] * 4),
    )
    assert summary["ran"] is True
    assert summary["inspected"] == 32
    assert summary["applied"] == 3
    assert summary["submit_failed"] == 2
    assert summary["quarantined"] == 1
    assert summary["reasons"] == {"closed": 20, "already": 2, "capability": 4}


def test_unknown_reasons_carry_their_wording() -> None:
    m = load()
    summary = m.summarise(
        commit_results(), decisions(["予算が非公開のため判断不能", "発注者が匿名"])
    )
    assert summary["reasons"]["capability"] == 2
    assert "予算が非公開のため判断不能" in summary["other_examples"]
    assert "発注者が匿名" in summary["other_examples"]


def test_other_examples_are_capped_and_truncated() -> None:
    m = load()
    long_reason = "非常に長い理由" * 10
    summary = m.summarise(commit_results(), decisions([f"{long_reason}{n}" for n in range(9)]))
    assert summary["reasons"]["capability"] == 9
    assert len(summary["other_examples"]) == 3
    assert all(len(text) <= 20 for text in summary["other_examples"])


def test_readback_inconclusive_rows_are_counted_not_silently_dropped() -> None:
    # §FG' B3: readback_inconclusive rows (a neighbour's page hung during the exact-id
    # scan) are deliberately not submit failures and not strikes -- but a bucket that no
    # counter covers is a silent stall. The operator has to see how many candidates are
    # waiting on an inconclusive readback, or a pass full of them looks like a quiet market.
    m = load()
    rows = commit_results() + [
        {"request_id": "906", "status": "readback_inconclusive:ReadbackScanTimeout"},
        {"request_id": "907", "status": "readback_inconclusive:ReadbackScanTimeout"},
    ]
    summary = m.summarise(rows, decisions([]))
    assert summary["readback_inconclusive"] == 2
    # They did not leak into any existing bucket.
    assert summary["submit_failed"] == 2
    assert summary["quarantined"] == 1
    line = m.render_line(summary)
    assert "確認不能2" in line


def test_pre_submit_abort_is_reported_as_submit_failure() -> None:
    m = load()
    summary = m.summarise(
        [{"request_id": "908", "status": "pre_submit_aborted:open_form:ParentContractError"}],
        decisions([]),
    )
    assert summary["submit_failed"] == 1
    assert "送信失敗1" in m.render_line(summary)


def test_a_lane_that_never_ran_is_not_a_zero_result() -> None:
    # The whole point: absence of a run and a run that found nothing must not look alike.
    m = load()
    summary = m.summarise(None, None)
    assert summary["ran"] is False
    assert summary["inspected"] == 0
    assert summary["applied"] == 0


def test_malformed_evidence_degrades_instead_of_raising() -> None:
    # This runs on the reporting path of every pass. A half-written evidence file must not
    # take the report down -- a report that fails to render is the silence P1b removes.
    m = load()
    summary = m.summarise("not a list", {"decisions": "not a list"})
    assert summary["ran"] is False
    assert summary["reasons"] == {}


def test_the_line_shows_the_batch_behind_a_successful_pass() -> None:
    # Dais 2026-08-06 chose the always-on breakdown over a zero-only one: without it, "4件
    # applied" hides that 33 of 37 inspections were wasted.
    m = load()
    line = m.render_line({
        "ran": True, "inspected": 37, "applied": 4, "submit_failed": 4, "quarantined": 0,
        "reasons": {"closed": 20, "already": 2, "capability": 7}, "other_examples": [],
    })
    assert line == "- 応募: 4件 ／ 検査37（募集終了20 / 既応募2 / 実務不可7 / 送信失敗4）"


def test_a_lane_that_never_ran_says_so() -> None:
    m = load()
    line = m.render_line({
        "ran": False, "inspected": 0, "applied": 0, "submit_failed": 0, "quarantined": 0,
        "reasons": {}, "other_examples": [],
    })
    assert line == "- 応募: 0件（レーン未実行）"


def test_zero_after_a_real_search_reads_differently_from_never_running() -> None:
    m = load()
    line = m.render_line({
        "ran": True, "inspected": 35, "applied": 0, "submit_failed": 0, "quarantined": 0,
        "reasons": {"closed": 30, "already": 5}, "other_examples": [],
    })
    assert "レーン未実行" not in line
    assert line == "- 応募: 0件 ／ 検査35（募集終了30 / 既応募5）"


def test_unknown_reasons_reach_the_reader_verbatim() -> None:
    m = load()
    line = m.render_line({
        "ran": True, "inspected": 3, "applied": 0, "submit_failed": 0, "quarantined": 0,
        "reasons": {"other": 3}, "other_examples": ["予算が非公開"],
    })
    assert "その他3" in line
    assert "予算が非公開" in line


def test_quarantined_forms_are_shown_when_present() -> None:
    m = load()
    line = m.render_line({
        "ran": True, "inspected": 10, "applied": 1, "submit_failed": 0, "quarantined": 2,
        "reasons": {"closed": 7}, "other_examples": [],
    })
    assert "隔離2" in line


def test_the_envelope_builder_reads_both_b2_evidence_files(tmp_path) -> None:
    # report_envelope already has evidence_dir (collect_lane_events, line 704) and already
    # reads agent-B2 there. The summary must come from the same place rather than from a
    # new collection pass.
    import json as json_module

    spec = importlib.util.spec_from_file_location(
        "report_envelope_p1b", SCRIPTS / "report_envelope.py"
    )
    assert spec and spec.loader
    envelope_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(envelope_module)

    b2 = tmp_path / "agent-B2"
    b2.mkdir()
    (b2 / "parent-commit.json").write_text(
        json_module.dumps({"results": [
            {"request_id": "1", "status": "confirmed"},
            {"request_id": "2", "status": "ineligible"},
        ]}),
        encoding="utf-8",
    )
    (b2 / "application-decisions.json").write_text(
        json_module.dumps({"decisions": [
            {"request_id": "2", "eligibility": "ineligible", "reason_codes": ["募集終了"]},
        ]}),
        encoding="utf-8",
    )

    summary = envelope_module.application_outcome(tmp_path)
    assert summary["ran"] is True
    assert summary["inspected"] == 2
    assert summary["applied"] == 1
    assert summary["reasons"] == {"closed": 1}


def test_a_missing_evidence_dir_reports_a_lane_that_did_not_run(tmp_path) -> None:
    spec = importlib.util.spec_from_file_location(
        "report_envelope_p1b_missing", SCRIPTS / "report_envelope.py"
    )
    assert spec and spec.loader
    envelope_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(envelope_module)

    summary = envelope_module.application_outcome(tmp_path / "absent")
    assert summary["ran"] is False


def test_the_human_report_uses_the_breakdown_line() -> None:
    # This is the sentence Dais actually receives. Before P1b it read "- 応募: 0件" whether
    # the lane had been blocked all hour or had inspected 35 jobs and found them all closed.
    spec = importlib.util.spec_from_file_location(
        "report_envelope_p1b_render", SCRIPTS / "report_envelope.py"
    )
    assert spec and spec.loader
    envelope_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(envelope_module)

    envelope = {
        "time": "2026-08-06T12:39:00+09:00",
        "data": {
            "trace_id": "pass-p1b",
            "status": "success",
            "state": "作業サイクルは正常に完了しました",
            "actions": [],
            "events": [],
            # render_human_ja closes every report with the AI cost line, so metrics is not
            # optional in this fixture even though P1b does not touch it.
            "metrics": {"model_cost_usd": 0.0},
            "work": {
                "searched": 37,
                "application_outcome": {
                    "ran": True, "inspected": 37, "applied": 0, "submit_failed": 4,
                    "quarantined": 0, "reasons": {"closed": 20, "already": 2, "capability": 7},
                    "other_examples": [],
                },
            },
        },
    }
    text = envelope_module.render_human_ja(envelope)
    assert "検査37" in text
    assert "募集終了20" in text
    assert "送信失敗4" in text


def test_the_pass_envelope_populates_the_breakdown_from_its_own_evidence(tmp_path) -> None:
    # The end-to-end gap the plan left open: render_human_ja reads
    # data["work"]["application_outcome"], and nothing was writing it, so a live pass still
    # printed the old sentence. pass_row carries evidence_dir -- the same value
    # telegram_report.py already hands to collect_lane_events -- so the envelope can fill
    # this in without any new collection.
    import json as json_module
    from datetime import datetime, timezone

    spec = importlib.util.spec_from_file_location(
        "report_envelope_p1b_wire", SCRIPTS / "report_envelope.py"
    )
    assert spec and spec.loader
    envelope_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(envelope_module)

    b2 = tmp_path / "agent-B2"
    b2.mkdir()
    (b2 / "parent-commit.json").write_text(
        json_module.dumps({"results": [
            {"request_id": "1", "status": "confirmed"},
            {"request_id": "2", "status": "ineligible"},
            {"request_id": "3", "status": "ineligible"},
        ]}),
        encoding="utf-8",
    )
    (b2 / "application-decisions.json").write_text(
        json_module.dumps({"decisions": [
            {"request_id": "2", "eligibility": "ineligible", "reason_codes": ["募集終了"]},
            {"request_id": "3", "eligibility": "ineligible", "reason_codes": ["既応募"]},
        ]}),
        encoding="utf-8",
    )

    envelope = envelope_module.build_pass_envelope(
        pass_row={
            "pass_id": "pass-wire",
            "status": "success",
            "ts": 1785988800,
            "evidence_dir": str(tmp_path),
        },
        applications=[],
        usage_rows=[],
        observed_at=datetime.fromtimestamp(1785988800, tz=timezone.utc),
    )

    outcome = envelope["data"]["work"]["application_outcome"]
    assert outcome["ran"] is True
    assert outcome["inspected"] == 3
    assert outcome["reasons"] == {"closed": 1, "already": 1}


def test_a_pass_envelope_without_an_evidence_dir_still_builds(tmp_path) -> None:
    # Older rows and fixture-driven callers have no evidence_dir. The report must still
    # render rather than raising on the reporting path of every pass.
    from datetime import datetime, timezone

    spec = importlib.util.spec_from_file_location(
        "report_envelope_p1b_wire_missing", SCRIPTS / "report_envelope.py"
    )
    assert spec and spec.loader
    envelope_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(envelope_module)

    envelope = envelope_module.build_pass_envelope(
        pass_row={"pass_id": "pass-noev", "status": "success", "ts": 1785988800},
        applications=[],
        usage_rows=[],
        observed_at=datetime.fromtimestamp(1785988800, tz=timezone.utc),
    )
    assert envelope["data"]["work"]["application_outcome"] == {}


def test_closed_and_already_are_the_only_mechanical_buckets() -> None:
    # Measured on five real passes: 18 of 29 rejections fell into "other", and every
    # verbatim example was a capability limit the keyword list had not anticipated
    # (phone_call_required, ILLUSTRATION_PRODUCTION_NOT_SUPPORTED, 公的資格が必要...).
    # Chasing that with a longer keyword list is endless. Only two rejection causes are
    # mechanical facts about the posting; everything else is a statement about us.
    m = load()
    assert m.normalise_reason("accepting_applications_false") == "closed"
    assert m.normalise_reason("募集終了") == "closed"
    assert m.normalise_reason("既応募") == "already"
    for text in (
        "phone_call_required",
        "ILLUSTRATION_PRODUCTION_NOT_SUPPORTED",
        "PHYSICAL_MANUFACTURING_REQUIRED",
        "中小企業診断士・公認会計士・税理士等の公的資格が必要",
        "ピアノ編曲・演奏経験が必須",
        "予算が非公開のため判断不能",
    ):
        assert m.normalise_reason(text) == "capability", text


def test_capability_reasons_are_quoted_so_a_missing_skill_is_visible() -> None:
    # The business signal lives here: "we declined illustration work eleven times" is a
    # decision about what to build next, and it is invisible if the bucket is just a count.
    m = load()
    summary = m.summarise(
        commit_results(),
        decisions(["ILLUSTRATION_PRODUCTION_NOT_SUPPORTED", "phone_call_required"]),
    )
    assert summary["reasons"]["capability"] == 2
    assert "ILLUSTRATION_PRODUCT" in " ".join(summary["other_examples"])
