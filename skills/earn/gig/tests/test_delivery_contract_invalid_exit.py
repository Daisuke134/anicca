"""A contract rejected before the browser opens is not a delivery attempt.

Measured 2026-08-08 22:04 (gig-pass-1786194006-85231, order 91000002): the progress
browser crashed at validate_progress_contract (progress_blockers_invalid) with rc=1
before any tab existed, gig_pass.sh booked it as a delivery attempt, and the per-target
counter reached 9/3 exhausted -- our own validation bug spent the order's real retry
budget. Same principle as the gc brake: record only after a real attempt.

Mirrors tests/test_formal_delivery_awaiting_buyer_confirmation.py: in-process main()
driving plus bash-branch-reading pins, applied to CONTRACT_INVALID_EXIT.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import coconala_formal_delivery_browser as formal_browser  # noqa: E402
import coconala_paid_progress_browser as progress_browser  # noqa: E402

PASS_SH = (Path(__file__).resolve().parents[1] / "gig_pass.sh").read_text(encoding="utf-8")


def test_the_two_browsers_agree_on_the_exit_code():
    assert progress_browser.CONTRACT_INVALID_EXIT == formal_browser.CONTRACT_INVALID_EXIT == 9
    # Distinct from the formal browser's other typed exits and the CDP lock wrapper's
    # 64/75/78, or the branches blur back together.
    assert formal_browser.CONTRACT_INVALID_EXIT not in (
        formal_browser.ROUTED_TO_ASK_EXIT,
        formal_browser.AWAITING_BUYER_CONFIRMATION_EXIT,
        64, 75, 78,
    )


def test_progress_main_returns_contract_invalid_before_any_browser(tmp_path, monkeypatch, capsys):
    queue_path = tmp_path / "queue.json"
    # delivery_action=formal in the progress browser: rejected on the first contract line.
    queue_path.write_text(json.dumps({"delivery_action": "formal"}), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")

    def no_browser(*_a, **_k):
        raise AssertionError("a browser tab was opened for an invalid contract")

    monkeypatch.setattr(progress_browser.collector, "DefaultTab", no_browser)
    monkeypatch.setattr(sys, "argv", [
        "coconala_paid_progress_browser.py",
        "--queue-item", str(queue_path),
        "--manifest", str(manifest_path),
        "--evidence-dir", str(tmp_path / "evidence"),
        "--default-tab-helper", str(tmp_path / "cdp_default_tab.py"),
    ])
    assert progress_browser._main() == progress_browser.CONTRACT_INVALID_EXIT
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["ok"] is False
    assert "delivery_action_not_progress" in payload["contract_invalid"]


def test_formal_main_returns_contract_invalid_before_any_browser(tmp_path, monkeypatch, capsys):
    queue_path = tmp_path / "queue.json"
    queue_path.write_text(json.dumps({"delivery_action": "progress"}), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")

    def no_browser(*_a, **_k):
        raise AssertionError("a browser tab was opened for an invalid contract")

    monkeypatch.setattr(formal_browser.collector, "DefaultTab", no_browser)
    monkeypatch.setattr(sys, "argv", [
        "coconala_formal_delivery_browser.py",
        "--queue-item", str(queue_path),
        "--manifest", str(manifest_path),
        "--project-root", str(tmp_path),
        "--evidence-dir", str(tmp_path / "evidence"),
        "--ledger", str(tmp_path / "events.jsonl"),
        "--default-tab-helper", str(tmp_path / "cdp_default_tab.py"),
    ])
    assert formal_browser.main() == formal_browser.CONTRACT_INVALID_EXIT
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["ok"] is False
    assert "queue_not_formal" in payload["contract_invalid"]


def test_bash_branches_on_the_number_and_before_the_generic_arm():
    """The exit code is written in two languages; only one has a type checker."""
    for var in ("progress_rc", "formal_rc"):
        needle = f'"${var}" -eq 9 ]'
        assert needle in PASS_SH, var
        # Placed above the generic -ne 0 arm or the branch is unreachable.
        assert PASS_SH.index(needle) < PASS_SH.index(f'"${var}" -ne 0 ]'), var


def test_bash_skips_attempt_recording_only_for_the_contract_invalid_reason():
    assert '"${LAST_FAILURE_REASON:-}" != "paid_delivery_contract_invalid"' in PASS_SH
    # The skip wraps record_delivery_attempt_failed inside the assess_paid_queue abort arm;
    # the reason itself must be recorded as a typed pass failure in both branches.
    assert PASS_SH.count('record_failure "paid_delivery_contract_invalid" "PAID_QUEUE_DELIVERY"') == 2
