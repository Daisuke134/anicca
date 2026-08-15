"""outcome_tracker.py — M1 durable outcome ledger (gig loop spec §FH' blind spot:
docs/loop-engineering/26-gig-loop-asis-tobe-plan.md). Pure-function tests only; the
browser glue (observe_batch) is exercised through an injected observe_fn so no test
opens a socket or touches ~/gig.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import outcome_tracker as ot  # noqa: E402


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


# ─── load_applied ────────────────────────────────────────────────────────────────
def test_load_applied_keeps_earliest_row_per_request_id(tmp_path):
    applied = tmp_path / "applied.jsonl"
    _write_jsonl(applied, [
        {"requestId": "111", "status": "applied", "ts": 200, "url": "https://coconala.com/requests/111"},
        {"requestId": "111", "status": "applied", "ts": 100, "url": "https://coconala.com/requests/111"},
        {"requestId": "222", "status": "applied", "ts": 150},
        {"requestId": "333", "status": "ineligible", "ts": 999},  # non-applied rows are ignored
        {"requestId": "not-a-digit", "status": "applied", "ts": 1},
    ])
    out = ot.load_applied(applied)
    assert set(out) == {"111", "222"}
    assert out["111"]["applied_ts"] == 100
    assert out["222"]["url"] == "https://coconala.com/requests/222"  # synthesized when absent


def test_load_applied_missing_file_returns_empty(tmp_path):
    assert ot.load_applied(tmp_path / "missing.jsonl") == {}


# ─── load_ledger_latest ──────────────────────────────────────────────────────────
def test_load_ledger_latest_keeps_last_write(tmp_path):
    ledger = tmp_path / "outcomes.jsonl"
    _write_jsonl(ledger, [
        {"request_id": "111", "status": "open", "checked_ts": 100},
        {"request_id": "111", "status": "closed_unfilled", "checked_ts": 200},
        {"request_id": "222", "status": "open", "checked_ts": 50},
    ])
    latest = ot.load_ledger_latest(ledger)
    assert latest["111"]["status"] == "closed_unfilled"
    assert latest["222"]["status"] == "open"


def test_load_ledger_latest_missing_file_returns_empty(tmp_path):
    assert ot.load_ledger_latest(tmp_path / "missing.jsonl") == {}


def test_load_ledger_latest_tolerates_malformed_lines(tmp_path):
    ledger = tmp_path / "outcomes.jsonl"
    ledger.write_text('{"request_id":"1","status":"open","checked_ts":1}\nnot json\n\n', encoding="utf-8")
    latest = ot.load_ledger_latest(ledger)
    assert latest["1"]["status"] == "open"


# ─── won_request_ids ─────────────────────────────────────────────────────────────
def test_won_request_ids_lists_digit_named_project_dirs(tmp_path):
    root = tmp_path / "projects"
    (root / "98000001").mkdir(parents=True)
    (root / "98000002").mkdir(parents=True)
    (root / ".openclaw").mkdir(parents=True)  # non-digit dir ignored
    (root / "notes.txt").write_text("x", encoding="utf-8")
    assert ot.won_request_ids(root) == {"98000001", "98000002"}


def test_won_request_ids_missing_root_returns_empty(tmp_path):
    assert ot.won_request_ids(tmp_path / "nope") == set()


# ─── classify_observation ────────────────────────────────────────────────────────
def test_classify_observation_reads_contracted_and_applicant_counts():
    text = "予算\n5万円\n応募人数 26\n契約人数 1\n閲覧数 348\n"
    obs = ot.classify_observation(text, True, True)
    assert obs["page_state"] == "observed"
    assert obs["contracted_count"] == 1
    assert obs["applicants_count"] == 26
    assert obs["accepting"] is True


def test_classify_observation_not_found_marker():
    obs = ot.classify_observation("お探しのページは見つかりません", None, True)
    assert obs["page_state"] == "not_found"
    assert obs["contracted_count"] is None


def test_classify_observation_empty_text_is_not_found():
    obs = ot.classify_observation("", None, True)
    assert obs["page_state"] == "not_found"


def test_classify_observation_navigation_failed_is_unreachable():
    obs = ot.classify_observation("whatever", None, False)
    assert obs["page_state"] == "unreachable"
    assert obs["accepting"] is None


# ─── decide_status ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("page_state", "accepting", "contracted_count", "expected"),
    [
        ("observed", True, None, ot.STATUS_OPEN),
        ("observed", True, 0, ot.STATUS_OPEN),
        ("observed", False, None, ot.STATUS_CLOSED_UNFILLED),
        ("observed", False, 0, ot.STATUS_CLOSED_UNFILLED),
        ("observed", True, 2, ot.STATUS_SOMEONE_CONTRACTED),
        ("observed", False, 1, ot.STATUS_SOMEONE_CONTRACTED),
        ("not_found", None, None, ot.STATUS_EXPIRED),
        ("unreachable", None, None, ot.STATUS_OPEN),
    ],
)
def test_decide_status_matrix(page_state, accepting, contracted_count, expected):
    obs = {
        "page_state": page_state,
        "accepting": accepting,
        "contracted_count": contracted_count,
        "applicants_count": None,
    }
    assert ot.decide_status(obs) == expected


# ─── select_batch ─────────────────────────────────────────────────────────────────
def test_select_batch_excludes_won_and_terminal_and_orders_never_checked_by_recency():
    applied = {
        "1": {"request_id": "1", "url": "u1", "applied_ts": 100},
        "2": {"request_id": "2", "url": "u2", "applied_ts": 300},
        "3": {"request_id": "3", "url": "u3", "applied_ts": 200},
    }
    ledger = {"3": {"status": ot.STATUS_CLOSED_UNFILLED, "checked_ts": 250}}
    batch = ot.select_batch(
        applied, ledger, won_ids=set(), now=1000, batch_limit=10, cooldown_secs=100
    )
    # 3 is terminal -> excluded. 1 and 2 never-checked -> newest application first.
    assert batch == ["2", "1"]


def test_select_batch_excludes_won_ids_entirely():
    applied = {"1": {"request_id": "1", "url": "u1", "applied_ts": 100}}
    batch = ot.select_batch(
        applied, {}, won_ids={"1"}, now=1000, batch_limit=10, cooldown_secs=100
    )
    assert batch == []


def test_select_batch_respects_cooldown_and_orders_stale_by_oldest_check():
    applied = {
        "1": {"request_id": "1", "url": "u1", "applied_ts": 100},
        "2": {"request_id": "2", "url": "u2", "applied_ts": 100},
    }
    ledger = {
        "1": {"status": ot.STATUS_OPEN, "checked_ts": 900},  # within cooldown -> skip
        "2": {"status": ot.STATUS_OPEN, "checked_ts": 100},  # stale -> included
    }
    batch = ot.select_batch(
        applied, ledger, won_ids=set(), now=1000, batch_limit=10, cooldown_secs=200
    )
    assert batch == ["2"]


def test_select_batch_caps_at_batch_limit():
    applied = {str(i): {"request_id": str(i), "url": "u", "applied_ts": i} for i in range(5)}
    batch = ot.select_batch(
        applied, {}, won_ids=set(), now=1000, batch_limit=2, cooldown_secs=100
    )
    assert len(batch) == 2


# ─── won_rows_to_append ───────────────────────────────────────────────────────────
def test_won_rows_to_append_only_for_applied_requests_not_already_recorded():
    applied = {"1": {"request_id": "1", "url": "u1", "applied_ts": 1}}
    rows = ot.won_rows_to_append(applied, {}, won_ids={"1", "2"}, now=1000)
    # "2" was never applied to (per this loop's own applied.jsonl) -> not tracked here.
    assert [row["request_id"] for row in rows] == ["1"]
    assert rows[0]["status"] == ot.STATUS_WE_WON
    assert rows[0]["checked_ts"] == 1000


def test_won_rows_to_append_skips_already_recorded_wins():
    applied = {"1": {"request_id": "1", "url": "u1", "applied_ts": 1}}
    ledger = {"1": {"status": ot.STATUS_WE_WON, "checked_ts": 5}}
    rows = ot.won_rows_to_append(applied, ledger, won_ids={"1"}, now=1000)
    assert rows == []


# ─── append_rows (durability: append-only, preserves existing bytes) ─────────────
def test_append_rows_preserves_existing_lines_and_appends(tmp_path):
    ledger = tmp_path / "outcomes.jsonl"
    ledger.write_text('{"request_id":"0","status":"open","checked_ts":1}\n', encoding="utf-8")
    ot.append_rows(ledger, [{"request_id": "1", "status": "open", "checked_ts": 2}])
    lines = ledger.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["request_id"] == "0"
    assert json.loads(lines[1])["request_id"] == "1"


def test_append_rows_noop_on_empty_list(tmp_path):
    ledger = tmp_path / "outcomes.jsonl"
    ot.append_rows(ledger, [])
    assert not ledger.exists()


# ─── run (end-to-end orchestration, browser stubbed) ──────────────────────────────
def test_run_records_wins_without_a_browser_visit_and_checks_the_rest(tmp_path):
    applied_path = tmp_path / "applied.jsonl"
    ledger_path = tmp_path / "outcomes.jsonl"
    projects_root = tmp_path / "projects"
    _write_jsonl(applied_path, [
        {"requestId": "1", "status": "applied", "ts": 100, "url": "https://coconala.com/requests/1"},
        {"requestId": "2", "status": "applied", "ts": 200, "url": "https://coconala.com/requests/2"},
    ])
    (projects_root / "1").mkdir(parents=True)  # request 1 = confirmed win

    observed_ids = []

    def fake_observe(ids):
        observed_ids.extend(ids)
        return {rid: {"page_state": "observed", "accepting": False, "contracted_count": 0, "applicants_count": 3} for rid in ids}

    summary = ot.run(
        applied_path=applied_path,
        ledger_path=ledger_path,
        projects_root=projects_root,
        batch_limit=10,
        cooldown_secs=100,
        now=1000,
        observe_fn=fake_observe,
    )

    # Request 1 is a known win -> recorded from project state, no page visit needed.
    assert observed_ids == ["2"]
    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
    by_id = {row["request_id"]: row for row in rows}
    assert by_id["1"]["status"] == ot.STATUS_WE_WON
    assert by_id["2"]["status"] == ot.STATUS_CLOSED_UNFILLED
    assert summary["applied_total"] == 2
    assert summary["won_rows_appended"] == 1
    assert summary["batch_size"] == 1
    # zero-must-record-how-it-looked: counts are always present, even at zero.
    assert summary["status_counts_this_run"][ot.STATUS_OPEN] == 0
    assert summary["status_counts_this_run"][ot.STATUS_CLOSED_UNFILLED] == 1


def test_run_is_idempotent_within_cooldown_second_call_visits_nothing(tmp_path):
    applied_path = tmp_path / "applied.jsonl"
    ledger_path = tmp_path / "outcomes.jsonl"
    projects_root = tmp_path / "projects"
    _write_jsonl(applied_path, [
        {"requestId": "1", "status": "applied", "ts": 100, "url": "https://coconala.com/requests/1"},
    ])

    calls = []

    def fake_observe(ids):
        calls.append(list(ids))
        return {rid: {"page_state": "observed", "accepting": True, "contracted_count": None, "applicants_count": 1} for rid in ids}

    ot.run(
        applied_path=applied_path, ledger_path=ledger_path, projects_root=projects_root,
        batch_limit=10, cooldown_secs=500, now=1000, observe_fn=fake_observe,
    )
    ot.run(
        applied_path=applied_path, ledger_path=ledger_path, projects_root=projects_root,
        batch_limit=10, cooldown_secs=500, now=1100, observe_fn=fake_observe,
    )
    assert calls == [["1"]]  # second run within cooldown: nothing to check


def test_run_never_visits_a_browser_when_batch_is_empty(tmp_path):
    applied_path = tmp_path / "applied.jsonl"
    ledger_path = tmp_path / "outcomes.jsonl"
    projects_root = tmp_path / "projects"

    def boom(_ids):
        raise AssertionError("observe_fn must not be called with an empty batch")

    summary = ot.run(
        applied_path=applied_path, ledger_path=ledger_path, projects_root=projects_root,
        batch_limit=10, cooldown_secs=100, now=1000, observe_fn=boom,
    )
    assert summary["batch_size"] == 0
    assert summary["applied_total"] == 0
