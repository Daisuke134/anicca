from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


# B2-3. application_intent_planner_failed fired ten times and said nothing else.
#
# The call captures the runner's stdout and stderr — capture_output=True — and then raises
# on a non-zero return code without looking at either. The planner's own explanation of why
# it failed was collected and thrown away, ten times.
#
# Same shape as B2-2: the failure is recorded, the reason is discarded. A quota error, a
# timeout, a bad schema and a crashed provider all arrive as the same six words.

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


def completed(returncode: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(args=["runner"], returncode=returncode, stdout=stdout, stderr=stderr)


def test_the_exit_code_is_reported() -> None:
    m = load_module()
    detail = m.runner_failure_detail(completed(7))
    assert "7" in detail


def test_stderr_reaches_the_error() -> None:
    m = load_module()
    detail = m.runner_failure_detail(completed(1, stderr="transient_quota: codex exhausted"))
    assert "transient_quota" in detail


def test_stdout_is_used_when_stderr_is_empty() -> None:
    # Some runners report on stdout. Losing the message because it came out of the other pipe
    # is the same bug wearing a different hat.
    m = load_module()
    detail = m.runner_failure_detail(completed(1, stdout="schema validation failed"))
    assert "schema validation failed" in detail


def test_a_silent_runner_still_produces_a_reason() -> None:
    # Never empty. An unexplained failure is the thing being removed.
    m = load_module()
    detail = m.runner_failure_detail(completed(9))
    assert detail.strip() != ""
    assert "9" in detail


def test_the_tail_is_kept_not_the_head() -> None:
    # Stack traces put the useful line last, and the log line has to stay bounded.
    m = load_module()
    detail = m.runner_failure_detail(completed(1, stderr="noise\n" * 500 + "RateLimitError: retry after 60s"))
    assert "RateLimitError" in detail
    assert len(detail) < 1200


def test_newlines_are_flattened_so_the_record_stays_one_line() -> None:
    # This ends up in a JSONL log; a multi-line reason splits one failure into many rows.
    m = load_module()
    detail = m.runner_failure_detail(completed(1, stderr="line one\nline two"))
    assert "\n" not in detail
