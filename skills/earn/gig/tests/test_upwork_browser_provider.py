from __future__ import annotations

import sys
import json
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
PROVIDERS = SCRIPTS / "providers"
for directory in (SCRIPTS, PROVIDERS):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from upwork_browser_provider import parse_connects, parse_inventory  # noqa: E402


def test_parses_zero_connects_without_inventing_a_reward():
    state = parse_connects(
        "Connects History\nMy balance\n0 Connects\nNo Connects transactions.\n"
    )
    assert state == {"balance": 0, "transactions_empty": True}


def test_parses_complete_zero_effect_inventory_and_account_task():
    state = parse_inventory(
        "Offers  (0)\nInvites from clients (0)\n0 connects to apply to these jobs\n"
        "Active proposals  (0)\nSubmitted proposals  (0)\n"
        "To do: Take the working style assessment.\n"
    )
    assert state == {
        "offers": 0,
        "invites": 0,
        "active_proposals": 0,
        "submitted_proposals": 0,
        "account_tasks": ["working_style_assessment"],
    }


@pytest.mark.parametrize("parser,text", [
    (parse_connects, "Connects History unavailable"),
    (parse_inventory, "Proposals and Offers loading"),
])
def test_partial_provider_pages_fail_closed(parser, text):
    with pytest.raises(ValueError, match="upwork_readback_incomplete"):
        parser(text)


def test_launchd_job_is_zero_spend_and_runs_every_five_minutes():
    manifest = json.loads((SCRIPTS.parent / "config" / "launchd-jobs.json").read_text())
    job = next(item for item in manifest["jobs"] if item["lane"] == "upwork-free")
    command = " ".join(job["program"]).lower()
    assert job["StartInterval"] == 300
    assert "upwork_browser_provider.py" in command
    assert all(term not in command for term in ("buy", "billing", "plus", "boost"))
