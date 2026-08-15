from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


# B2-2. Twenty-four of the application lane's failures were recorded as
# {"ok":false,"error":""} — a failure that refuses to say what it was.
#
# The cause is one line: the top-level handler records str(error) and nothing else, so an
# exception raised without a message becomes an empty string, and the type, the location and
# the traceback are all discarded. Twenty-four passes died with no way to tell which of five
# exception classes fired or where.
#
# This is the same failure shape the paid lane spent the day removing — an outcome that
# produces no row — living inside the error channel itself. A failure that cannot name itself
# cannot be counted, cannot be grouped, and cannot be fixed.

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


def raised(exc: BaseException) -> BaseException:
    """Return the exception with a real traceback attached, as the handler would see it."""
    try:
        raise exc
    except BaseException as error:  # noqa: BLE001 - deliberately capturing what was raised
        return error


def test_a_message_is_kept_as_is() -> None:
    m = load_module()
    described = m.describe_error(raised(ValueError("lease_acquire_contract_invalid")))
    assert described["error"] == "lease_acquire_contract_invalid"


def test_an_exception_with_no_message_still_says_something() -> None:
    # This is the whole bug: str(ValueError()) is "".
    m = load_module()
    described = m.describe_error(raised(ValueError()))
    assert described["error"] != ""
    assert "ValueError" in described["error"]


def test_the_type_is_always_recorded_separately() -> None:
    # Five exception classes share one handler. Without the type, "" could be any of them.
    m = load_module()
    assert m.describe_error(raised(OSError("disk gone")))["error_type"] == "OSError"
    assert m.describe_error(raised(ValueError()))["error_type"] == "ValueError"


def test_where_it_came_from_is_recorded() -> None:
    # A named failure with no location still costs a grep across 1800 lines.
    m = load_module()
    described = m.describe_error(raised(ValueError("boom")))
    assert ":" in described["error_at"]
    assert "test_application_error_description" in described["error_at"]


def test_an_exception_never_raised_is_still_describable() -> None:
    # Defensive: no traceback attached must not crash the handler that reports the failure.
    m = load_module()
    described = m.describe_error(ValueError("constructed, not raised"))
    assert described["error"] == "constructed, not raised"
    assert described["error_at"] == "unknown"


def test_whitespace_only_messages_count_as_empty() -> None:
    m = load_module()
    described = m.describe_error(raised(ValueError("   ")))
    assert described["error"].strip() != ""
    assert "ValueError" in described["error"]


def test_it_points_at_our_code_not_the_standard_library() -> None:
    # The deepest frame of a JSON error is decoder.py:361, which tells nobody which of our
    # 1800 lines called it. The useful answer is the deepest frame we own.
    import json as _json

    m = load_module()
    described = m.describe_error(raised_from_our_code())
    assert "decoder.py" not in described["error_at"]
    assert described["error_at"].startswith("test_application_error_description.py:")


def raised_from_our_code() -> BaseException:
    import json as _json

    try:
        _json.loads("{bad")
    except BaseException as error:  # noqa: BLE001
        return error
