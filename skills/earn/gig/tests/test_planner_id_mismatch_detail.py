from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


# B2-4. decision_request_ids_not_one_to_one fired ten times and named no id.
#
# The planner must return one decision per request in its snapshot. When the sets differ the
# contract records only that they differed — not which ids were missing, not which were
# invented. With batches of ten and a hundred and eighteen recorded runs, that is a bare
# assertion that something was wrong somewhere.
#
# Measured across every saved planner result: exactly one had a duplicate id, matching the
# single decision_request_ids_duplicate in the log. So the ten one-to-one failures are set
# differences, and nothing on disk says which ones — the expected set is not saved beside
# the result. Rather than guess at the cause, make the violation describe itself so the next
# occurrence is diagnosable in one step.

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "application_planner.py"


def load_module():
    # application_planner imports its siblings by bare name.
    scripts_dir = str(MODULE_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("application_planner", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def decision(request_id: str) -> dict:
    return {
        "request_id": request_id,
        "eligibility": "ineligible",
        "reason_codes": ["out_of_scope"],
        "proposal_text": None,
        "price_jpy": None,
        "deliver_date": None,
    }


def snapshot(*ids: str) -> dict:
    return {"request_details": [{"request_id": i} for i in ids]}


def errors_for(module, expected: tuple[str, ...], actual: tuple[str, ...]) -> list[str]:
    if set(expected) == set(actual):
        return []
    return [module.id_mismatch_error(list(expected), list(actual))]


def test_a_dropped_request_is_named() -> None:
    m = load_module()
    errors = errors_for(m, ("111", "222", "333"), ("111", "333"))
    joined = " ".join(errors)
    assert "not_one_to_one" in joined
    assert "222" in joined


def test_an_invented_request_is_named() -> None:
    # A hallucinated id is a different bug from a dropped one and needs a different fix.
    m = load_module()
    errors = errors_for(m, ("111", "222"), ("111", "222", "999"))
    joined = " ".join(errors)
    assert "999" in joined


def test_both_directions_are_reported_at_once() -> None:
    m = load_module()
    joined = " ".join(errors_for(m, ("111", "222"), ("111", "999")))
    assert "222" in joined and "999" in joined


def test_a_matching_set_reports_nothing() -> None:
    m = load_module()
    assert not [e for e in errors_for(m, ("111", "222"), ("222", "111")) if "one_to_one" in e]


def test_the_message_stays_bounded_with_many_ids() -> None:
    # Batches are ten today but older runs carried thirty-nine. The reason has to stay
    # readable in a log line.
    m = load_module()
    expected = tuple(str(100000 + i) for i in range(40))
    joined = " ".join(e for e in errors_for(m, expected, ()) if "one_to_one" in e)
    assert len(joined) < 400
