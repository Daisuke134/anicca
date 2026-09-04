from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


RUNNER_DIR = Path(__file__).resolve().parents[4] / "runtime/agent-runner"
sys.path.insert(0, str(RUNNER_DIR))
SPEC = importlib.util.spec_from_file_location("gig_agent_runner_claude_payload_test", RUNNER_DIR / "agent_runner.py")
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_claude_json_document_strips_a_clean_whole_string_fence() -> None:
    payload = '```json\n{"decision": "change", "service_id": "4371816"}\n```'
    assert runner.claude_json_document(payload) == '{"decision": "change", "service_id": "4371816"}'


def test_claude_json_document_leaves_a_fence_with_trailing_prose_untouched() -> None:
    # Only a whole document is accepted; trailing prose after the fence must fail loudly
    # upstream instead of silently keeping the first of several objects (see docstring).
    payload = (
        '```json\n{"decision": "change", "service_id": "4371816"}\n```\n\n'
        "body差替のみ。理由: gap=body/inquiries"
    )
    assert runner.claude_json_document(payload) == payload


def test_parse_contract_result_salvages_the_object_from_that_untouched_payload() -> None:
    # Measured 2026-09-04 on the storefront proposal agent: Claude answered inside a ```json
    # fence and appended a Japanese one-line rationale after the closing fence.
    # claude_json_document intentionally leaves this text alone (test above); the runner still
    # selects the answer because parse_contract_result's salvage decodes the first balanced
    # JSON object regardless of what surrounds it.
    payload = (
        '```json\n{"decision": "change", "service_id": "4371816"}\n```\n\n'
        "body差替のみ。理由: gap=body/inquiries"
    )
    result = runner.parse_contract_result(payload, salvage=True)
    assert result == {"decision": "change", "service_id": "4371816"}
