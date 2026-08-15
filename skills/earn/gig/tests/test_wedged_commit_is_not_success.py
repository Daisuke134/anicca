from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


# 2026-08-05 23:12, 23:18, 23:24: three consecutive passes returned {"ok":true,"results":34}
# and recorded no application. Every eligible candidate in them died the same way --
#
#   91000101  cdp_Page.navigate_timeout_after_30s
#   91000095  cdp_Page.enable_timeout_after_30s
#   91000094  cdp_Page.enable_timeout_after_30s
#   91000097  cdp_Page.enable_timeout_after_30s
#
# -- because one leased target is held for the whole commit section, so a renderer that
# wedges on the first 応募 form takes every later candidate in the same pass with it.
#
# The pass already knows how to restart a wedged browser and retry, but it keys that on the
# parent failing, and a parent that scored all four candidates as runtime failures still
# reported success. A commit in which the browser died for every single attempt is not a
# successful commit; calling it one is what let the loop repeat the same dead hour.

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "application_parent.py"


def load_module():
    scripts_dir = str(MODULE_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("application_parent", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wedged(request_id, error="cdp_Page.enable_timeout_after_30s"):
    return {
        "request_id": request_id,
        "status": "submission_runtime_failed:ParentContractError",
        "error": error,
        "error_at": "application_parent.py:435",
    }


def test_the_real_pass_that_applied_to_nothing_is_reported_as_wedged() -> None:
    m = load_module()
    results = [{"request_id": str(i), "status": "ineligible"} for i in range(30)]
    results += [
        wedged("91000101", "cdp_Page.navigate_timeout_after_30s"),
        wedged("91000095"),
        wedged("91000094"),
        wedged("91000097"),
    ]
    assert m.commit_browser_wedged(results) is True


def test_one_application_through_means_the_browser_was_not_the_problem() -> None:
    m = load_module()
    results = [
        {"request_id": "1", "status": "ineligible"},
        {"request_id": "2", "status": "applied"},
        wedged("3"),
    ]
    assert m.commit_browser_wedged(results) is False


def test_a_pass_with_nothing_eligible_is_a_quiet_market_not_a_wedge() -> None:
    # 30 ineligible and no attempt at all is the ordinary shape of a thin hour. Calling it a
    # browser fault would restart the browser every pass and hide the real thing.
    m = load_module()
    results = [{"request_id": str(i), "status": "ineligible"} for i in range(30)]
    assert m.commit_browser_wedged(results) is False


def test_a_form_that_rejected_the_proposal_is_not_a_wedge() -> None:
    # A submission that failed for a reason of its own is a business outcome, and restarting
    # the browser would neither fix it nor say anything true about it.
    m = load_module()
    results = [
        {"request_id": "1", "status": "ineligible"},
        {"request_id": "2", "status": "submission_failed:proposal_rejected"},
    ]
    assert m.commit_browser_wedged(results) is False


def test_pre_submit_abort_is_a_wedge_only_for_a_cdp_timeout() -> None:
    m = load_module()
    result = {
        "request_id": "1",
        "status": "pre_submit_aborted:open_form:ParentContractError",
        "error": "cdp_Page.navigate_timeout_after_30s",
    }
    assert m.commit_browser_wedged([result]) is True
    result["error"] = "form_readback_mismatch"
    assert m.commit_browser_wedged([result]) is False


# The real 00:00 tally from gig-pass-1786201210-10819/agent-B2/parent-commit.json: 23
# ineligible + 4 quarantined_wedging_form + 1 cdp timeout + 1 confirmed application
# (request_id 91000053, a real HIT that landed in applied.jsonl). This was misreported as
# "cdp_browser_wedged_for_every_attempt" three times overnight (00:00, 02:28, 03:18) while
# applied.jsonl kept growing -- because "confirmed" matched none of the attempted-status
# prefixes and was silently dropped from the tally, leaving the lone timeout as the only
# candidate commit_browser_wedged ever saw. request_ids and statuses below are copied
# verbatim from that evidence file.
REAL_00_00_TALLY = [
    {"request_id": rid, "status": "ineligible"}
    for rid in (
        "91000121", "91000120", "91000123", "91000115", "91000122", "91000113", "91000114",
        "91000110", "91000105", "91000106", "91000117", "91000116", "91000119", "91000099",
        "91000096", "91000092", "91000091", "91000090", "91000089", "91000088", "91000086",
        "91000076", "91000082",
    )
] + [
    {"request_id": rid, "status": "quarantined_wedging_form:count=3"}
    for rid in ("91000118", "91000111", "91000112", "91000098")
] + [
    wedged("91000124", "cdp_Page.navigate_timeout_after_30s"),
    {
        "request_id": "91000053",
        "status": "confirmed",
        "application": {"request_id": "91000053", "price_jpy": 120000},
    },
]


def test_the_real_00_00_tally_that_applied_successfully_is_not_wedged() -> None:
    # 23 ineligible + 4 quarantined + 1 timeout + 1 confirmed. One candidate wedging is not
    # the browser dying for every attempt when another candidate in the same commit landed.
    m = load_module()
    assert len(REAL_00_00_TALLY) == 29
    statuses = [row["status"] for row in REAL_00_00_TALLY]
    assert statuses.count("ineligible") == 23
    assert sum(s.startswith("quarantined_wedging_form") for s in statuses) == 4
    assert sum(s.startswith("submission_runtime_failed") for s in statuses) == 1
    assert statuses.count("confirmed") == 1
    assert m.commit_browser_wedged(REAL_00_00_TALLY) is False


def test_recovered_prepared_confirmed_also_proves_the_browser_worked() -> None:
    m = load_module()
    results = [
        {"request_id": "1", "status": "ineligible"},
        wedged("2"),
        {"request_id": "3", "status": "recovered_prepared_confirmed"},
    ]
    assert m.commit_browser_wedged(results) is False


def test_reconciled_confirmed_also_proves_the_browser_worked() -> None:
    m = load_module()
    results = [wedged("1"), {"request_id": "2", "status": "reconciled_confirmed"}]
    assert m.commit_browser_wedged(results) is False


def test_all_attempts_wedged_with_quarantine_noise_still_raises() -> None:
    # Quarantined and ineligible rows are not attempts and must not dilute a real
    # all-wedged commit into a false pass.
    m = load_module()
    results = [{"request_id": str(i), "status": "ineligible"} for i in range(10)]
    results.append({"request_id": "q1", "status": "quarantined_wedging_form:count=3"})
    results += [wedged("91000101"), wedged("91000095"), wedged("91000094")]
    assert m.commit_browser_wedged(results) is True


def inconclusive(request_id, error="cdp_Page.navigate_timeout_after_30s"):
    return {
        "request_id": request_id,
        "status": "readback_inconclusive:ReadbackScanTimeout",
        "error": error,
        "error_at": "application_parent.py:1005",
    }


def test_every_attempt_inconclusive_on_cdp_timeouts_is_a_wedged_browser() -> None:
    # §FG' B3: a commit in which every attempted candidate's readback died on a CDP timeout
    # is the permanent-neighbour-hang scenario -- the browser is the problem, and the
    # pass-level restart must fire. Before this, readback_inconclusive rows fell outside
    # "attempted" entirely, so an all-inconclusive commit reported ok and the loop repeated
    # the same dead hour.
    m = load_module()
    results = [{"request_id": str(i), "status": "ineligible"} for i in range(30)]
    results += [inconclusive("95000015"), inconclusive("95000013")]
    assert m.commit_browser_wedged(results) is True


def test_one_application_through_beside_inconclusive_rows_is_not_a_wedge() -> None:
    m = load_module()
    results = [
        {"request_id": "1", "status": "confirmed"},
        inconclusive("2"),
    ]
    assert m.commit_browser_wedged(results) is False


def test_all_truncation_inconclusive_is_not_a_browser_wedge() -> None:
    # Truncation (page budget exhausted, next link remains) is not a browser fault; a
    # restart would neither fix it nor say anything true about it.
    m = load_module()
    results = [
        inconclusive("1", "official_readback_truncated_after_10_pages_next_page_remains"),
    ]
    assert m.commit_browser_wedged(results) is False
