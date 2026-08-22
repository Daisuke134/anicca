import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from no_contact_policy import (  # noqa: E402
    NoContactPolicyError,
    load_registry,
    match_thread,
    validate_registry,
)


def _registry():
    return {
        "version": 1,
        "entries": [{
            "policy_id": "operator-owned-1",
            "counterparty_user_id": "12345",
            "thread_path": "/mypage/direct_message/90001",
        }],
    }


def test_exact_private_identity_matches_without_storing_a_name(tmp_path):
    path = tmp_path / "no-contact.json"
    path.write_text(json.dumps(_registry()), encoding="utf-8")
    registry = load_registry(path)
    assert match_thread(
        registry, thread_path="/mypage/direct_message/90001",
        counterparty_user_id="12345",
    )["policy_id"] == "operator-owned-1"


def test_thread_match_can_stop_work_before_opening_the_counterparty(tmp_path):
    registry = _registry()
    assert match_thread(
        registry, thread_path="/mypage/direct_message/90001",
    ) is not None
    assert match_thread(
        registry, thread_path="/mypage/direct_message/90002",
    ) is None


def test_counterparty_mismatch_fails_closed():
    with pytest.raises(NoContactPolicyError, match="identity_mismatch"):
        match_thread(
            _registry(), thread_path="/mypage/direct_message/90001",
            counterparty_user_id="67890",
        )


@pytest.mark.parametrize("mutation", [
    lambda entry: entry.pop("counterparty_user_id"),
    lambda entry: entry.update(thread_path="https://coconala.com/mypage/direct_message/90001"),
    lambda entry: entry.update(counterparty_name="private"),
])
def test_registry_rejects_incomplete_noncanonical_or_named_entries(mutation):
    registry = _registry()
    mutation(registry["entries"][0])
    with pytest.raises(NoContactPolicyError):
        validate_registry(registry)
