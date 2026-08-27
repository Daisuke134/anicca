from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUNNER_DIR = Path(__file__).resolve().parents[1] / "agent-runner"
sys.path.insert(0, str(RUNNER_DIR))
SPEC = importlib.util.spec_from_file_location("gig_account_failover", RUNNER_DIR / "agent_runner.py")
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_config_and_candidate_order_is_account_one_then_account_two() -> None:
    config = json.loads((RUNNER_DIR / "config.json").read_text(encoding="utf-8"))
    accounts = config["providers"]["codex"]["accounts"]
    assert [account["alias"] for account in accounts] == ["account-1", "account-2"]
    candidates = runner.expand_codex_candidates(
        [{"provider": "codex", "model": "fixture"}, {"provider": "claude", "model": "fallback"}],
        config["providers"],
    )
    assert [(row["provider"], row.get("account")) for row in candidates[:3]] == [
        ("codex", "account-1"), ("codex", "account-2"), ("claude", None),
    ]


def test_only_pre_effect_quota_or_auth_retries_account() -> None:
    assert runner.should_retry_next_codex_account("transient_quota", False)
    assert runner.should_retry_next_codex_account("transient_auth", False)
    assert not runner.should_retry_next_codex_account("transient_timeout", False)
    assert not runner.should_retry_next_codex_account("transient_quota", True)


def test_effect_detection_uses_machine_events() -> None:
    message = json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "run command"}})
    effect = json.dumps({"type": "item.started", "item": {"type": "command_execution", "command": "true"}})
    assert not runner.codex_effect_started(message)
    assert runner.codex_effect_started(effect)
