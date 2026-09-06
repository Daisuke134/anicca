import json
from types import SimpleNamespace

from skills.earn.gig.scripts import paid_direct as paid


def test_terminal_reconciliation_is_one_rotating_candidate_per_wake(
    tmp_path, monkeypatch
):
    projects = tmp_path / "projects"
    evidence = tmp_path / "evidence"
    for room in ("100", "200", "300"):
        root = projects / room
        root.mkdir(parents=True)
        (root / "state.json").write_text(json.dumps({
            "talkroom_id": room, "buyer": f"buyer-{room}",
        }))
    calls = []
    monkeypatch.setattr(paid, "_collector", lambda *_args: ["collector"])

    def fail(*_args, **_kwargs):
        calls.append(True)
        raise paid.Failure("terminal_reconciliation")

    monkeypatch.setattr(paid, "_run", fail)
    monkeypatch.setattr(paid.subprocess, "run", lambda *_args, **_kwargs: None)
    args = SimpleNamespace(
        projects_root=projects,
        evidence_dir=evidence,
        cdp_helper=tmp_path / "cdp_default_tab.py",
        cdp_lock_dir=tmp_path / "cdp-locks",
    )

    result = paid._reconcile_absent_talkrooms(args, [])

    assert len(calls) == 1
    assert len(result["results"]) == 1
    assert result["remaining_candidates"] == 2


def test_terminal_reconciliation_budget_stays_below_half_paid_cadence():
    worst_case = paid.PAID_TERMINAL_RECONCILES_PER_WAKE * (
        paid.TERMINAL_RECONCILIATION_TIMEOUT_SECONDS
        + paid.TERMINAL_RECONCILIATION_CLEANUP_TIMEOUT_SECONDS
    )
    assert worst_case < 150
