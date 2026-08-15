"""Run directly: python3 skills/earn/gig/tests/test_daily_gig_report.py
(NEVER pytest -- the rtk shim blocks it, see repo convention in sibling tests)."""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "daily_gig_report.py"
SCRIPTS_DIR = SCRIPT.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location("daily_gig_report", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

JST = MODULE.listing_ledger.JST
TODAY = datetime(2026, 8, 9, 12, 0, tzinfo=JST)  # inside [2026-08-09 00:00, 2026-08-10 00:00) JST
YESTERDAY = TODAY - timedelta(days=1)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_rollup_counts_only_todays_jst_rows():
    tmp = Path(tempfile.mkdtemp())
    try:
        gig_dir = tmp / "gig"
        projects_root = gig_dir / "projects"

        _write_jsonl(gig_dir / "applied.jsonl", [
            {"ts": int(TODAY.timestamp()), "status": "applied", "requestId": "1"},
            {"ts": int(TODAY.timestamp()) + 10, "status": "applied", "requestId": "2"},
            {"ts": int(TODAY.timestamp()), "status": "replied", "requestId": "3"},  # not "applied"
            {"ts": int(YESTERDAY.timestamp()), "status": "applied", "requestId": "4"},  # wrong day
        ])
        _write_jsonl(gig_dir / "buyer-outcomes.jsonl", [
            {"ts": int(TODAY.timestamp()), "talkroom_id": "a", "text": "hi", "reaction": None},
            {"ts": int(TODAY.timestamp()), "talkroom_id": "b", "text": "yo", "reaction": "satisfied"},
            {"ts": int(YESTERDAY.timestamp()), "talkroom_id": "c", "text": "old", "reaction": None},
        ])
        _write_jsonl(gig_dir / "janitor.jsonl", [
            {"ts": int(TODAY.timestamp()), "project_id": "1"},
            {"ts": int(YESTERDAY.timestamp()), "project_id": "2"},
        ])

        _write_json(projects_root / "1" / "state.json", {
            "delivery_attempts": [
                {"at": TODAY.timestamp(), "outcome": "confirmed"},
                {"at": YESTERDAY.timestamp(), "outcome": "confirmed"},
                {"at": TODAY.timestamp(), "outcome": "failed"},
            ]
        })
        _write_jsonl(projects_root / "1" / "events.jsonl", [
            {"ts": TODAY.timestamp(), "event": "state_reconciled",
             "changes": {"transaction_state": {"from": "取引中", "to": "取引完了"}}},
            {"ts": YESTERDAY.timestamp(), "event": "state_reconciled",
             "changes": {"transaction_state": {"from": None, "to": "取引完了"}}},
            {"ts": TODAY.timestamp(), "event": "queue_selected"},
        ])
        _write_json(projects_root / "2" / "state.json", {"delivery_attempts": []})
        _write_jsonl(projects_root / "2" / "events.jsonl", [
            {"ts": TODAY.timestamp(), "event": "state_reconciled",
             "changes": {"transaction_state": {"from": "取引中", "to": "自動キャンセル"}}},
        ])
        _write_jsonl(gig_dir / "score-reality.jsonl", [
            {"project_id": "1", "talkroom_id": "a", "score": 90, "first_reaction": "positive",
             "reaction_ts": int(TODAY.timestamp()), "scored_ts": TODAY.timestamp()},
            {"project_id": "2", "talkroom_id": "b", "score": 20, "first_reaction": "negative",
             "reaction_ts": int(TODAY.timestamp()), "scored_ts": TODAY.timestamp()},
            {"project_id": "3", "talkroom_id": "c", "score": 55, "first_reaction": "positive",
             "reaction_ts": int(YESTERDAY.timestamp()), "scored_ts": YESTERDAY.timestamp()},  # wrong day
        ])

        report = MODULE.build_report(gig_dir, projects_root, now=TODAY)

        assert report["date"] == "2026-08-09", report
        assert report["applications_verified"] == 2, report
        assert report["deliveries_confirmed"] == 1, report
        assert report["buyer_replies"] == 2, report
        assert report["buyer_replies_by_reaction"] == {"unclassified": 1, "satisfied": 1}, report
        assert report["revenue_transitions"] == {"取引完了": 1, "自動キャンセル": 1}, report
        assert report["revenue_completed"] == 1, report
        assert report["cancellations"] == 1, report
        assert report["projects_reclaimed"] == 1, report
        assert report["score_reality"] == 2, report  # the YESTERDAY row is excluded
        assert report["score_reality_by_band"] == {
            "70-100": {"positive": 1},
            "<40": {"negative": 1},
        }, report
        print("PASS test_rollup_counts_only_todays_jst_rows")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_missing_ledgers_and_projects_root_report_all_zero_not_crash():
    tmp = Path(tempfile.mkdtemp())
    try:
        gig_dir = tmp / "gig"  # never created
        report = MODULE.build_report(gig_dir, gig_dir / "projects", now=TODAY)
        assert report["applications_verified"] == 0
        assert report["deliveries_confirmed"] == 0
        assert report["buyer_replies"] == 0
        assert report["revenue_transitions"] == {}
        assert report["cancellations"] == 0
        assert report["projects_reclaimed"] == 0
        assert report["score_reality"] == 0
        assert report["score_reality_by_band"] == {}
        print("PASS test_missing_ledgers_and_projects_root_report_all_zero_not_crash")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_malformed_rows_and_bad_state_json_are_skipped_not_fatal():
    tmp = Path(tempfile.mkdtemp())
    try:
        gig_dir = tmp / "gig"
        projects_root = gig_dir / "projects"
        applied_path = gig_dir / "applied.jsonl"
        applied_path.parent.mkdir(parents=True)
        applied_path.write_text(
            "not json at all\n"
            + json.dumps({"ts": int(TODAY.timestamp()), "status": "applied"}) + "\n"
            + "[]\n",  # valid json, not a dict
            encoding="utf-8",
        )
        (projects_root / "broken").mkdir(parents=True)
        (projects_root / "broken" / "state.json").write_text("{not valid", encoding="utf-8")
        (projects_root / "broken" / "events.jsonl").write_text("also not valid\n", encoding="utf-8")

        report = MODULE.build_report(gig_dir, projects_root, now=TODAY)

        assert report["applications_verified"] == 1, report
        assert report["deliveries_confirmed"] == 0, report
        assert report["revenue_transitions"] == {}, report
        print("PASS test_malformed_rows_and_bad_state_json_are_skipped_not_fatal")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_score_band_boundaries_match_predelivery_score_floor():
    tmp = Path(tempfile.mkdtemp())
    try:
        gig_dir = tmp / "gig"
        _write_jsonl(gig_dir / "score-reality.jsonl", [
            {"project_id": "1", "score": 0, "first_reaction": "negative", "scored_ts": TODAY.timestamp()},
            {"project_id": "2", "score": MODULE.predelivery_score.SCORE_FLOOR - 1,
             "first_reaction": "negative", "scored_ts": TODAY.timestamp()},
            {"project_id": "3", "score": MODULE.predelivery_score.SCORE_FLOOR,
             "first_reaction": "neutral", "scored_ts": TODAY.timestamp()},
            {"project_id": "4", "score": MODULE.HIGH_BAND_MIN - 1,
             "first_reaction": "neutral", "scored_ts": TODAY.timestamp()},
            {"project_id": "5", "score": MODULE.HIGH_BAND_MIN,
             "first_reaction": "positive", "scored_ts": TODAY.timestamp()},
            {"project_id": "6", "score": 100, "first_reaction": "positive", "scored_ts": TODAY.timestamp()},
            {"project_id": "7", "score": None, "first_reaction": "unclear", "scored_ts": TODAY.timestamp()},
        ])

        report = MODULE.build_report(gig_dir, gig_dir / "projects", now=TODAY)

        assert report["score_reality"] == 6, "the null-score row must not count"
        assert report["score_reality_by_band"] == {
            "<40": {"negative": 2},
            "40-69": {"neutral": 2},
            "70-100": {"positive": 2},
        }, report
        print("PASS test_score_band_boundaries_match_predelivery_score_floor")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_main_writes_dated_json_file_and_prints_same_report():
    tmp = Path(tempfile.mkdtemp())
    try:
        gig_dir = tmp / "gig"
        (gig_dir).mkdir(parents=True)
        out_dir = tmp / "daily-report"

        report = MODULE.build_report(gig_dir, gig_dir / "projects", now=TODAY)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{report['date']}.json"
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        assert out_path.is_file()
        on_disk = json.loads(out_path.read_text(encoding="utf-8"))
        assert on_disk["date"] == report["date"]
        print("PASS test_main_writes_dated_json_file_and_prints_same_report")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_rollup_counts_only_todays_jst_rows()
    test_missing_ledgers_and_projects_root_report_all_zero_not_crash()
    test_malformed_rows_and_bad_state_json_are_skipped_not_fatal()
    test_score_band_boundaries_match_predelivery_score_floor()
    test_main_writes_dated_json_file_and_prints_same_report()
    print("ALL PASS")
