from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


# On 2026-08-05 22:49 the B2 lane finally ran clean end to end and still applied to nothing:
# 35 offers, 33 ineligible, 2 attempted, both recorded as
#
#     {"request_id": "91000095", "status": "submission_runtime_failed:ParentContractError"}
#
# ParentContractError is raised in more than a dozen places in this file. The class name alone
# cannot say whether the click never landed, the readback transport died, or the form rejected
# the proposal — so the one thing the operator needs, why the application did not go through,
# is the one thing the record throws away. This is the same defect the B2 boundary had before
# parent-error.json existed, one layer further in.

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


def raise_here(module):
    """Raise from a known frame so the recorded location can be checked."""
    try:
        raise module.ParentContractError("cdp_Runtime.evaluate_timeout_after_30s")
    except module.ParentContractError as error:
        return error


def test_the_status_still_names_the_exception_class() -> None:
    m = load_module()
    row = m.submission_failure_result("91000095", raise_here(m))
    assert row["request_id"] == "91000095"
    assert row["status"] == "submission_runtime_failed:ParentContractError"


def test_the_row_carries_the_message_so_the_cause_is_readable() -> None:
    m = load_module()
    row = m.submission_failure_result("91000095", raise_here(m))
    assert row["error"] == "cdp_Runtime.evaluate_timeout_after_30s"


def test_the_row_says_where_it_came_from() -> None:
    m = load_module()
    row = m.submission_failure_result("91000095", raise_here(m))
    assert "test_submission_failure_detail.py:" in row["error_at"]


def test_a_message_less_exception_still_produces_something_findable() -> None:
    # An exception raised with no message used to serialise as "", which groups with every
    # other empty failure and can be counted as none of them.
    m = load_module()
    try:
        raise m.ParentContractError()
    except m.ParentContractError as error:
        row = m.submission_failure_result("91000097", error)
    assert row["error"]
    assert row["status"] == "submission_runtime_failed:ParentContractError"
