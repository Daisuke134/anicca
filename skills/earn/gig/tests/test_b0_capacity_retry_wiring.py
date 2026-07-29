from pathlib import Path


PASS = Path(__file__).resolve().parents[1] / "gig_pass.sh"


def test_capacity_rejection_retries_b0_once_without_accepting_noop():
    source = PASS.read_text(encoding="utf-8")
    assert "B0_RECOVERY_RETRY_COUNT=0" in source
    assert "b0-capacity-gate-result" in source
    assert "retry-context" in source
    assert 'return 4' in source
    assert (
        '[ "$lane_step_rc" -eq 4 ] && [ "$1" = "B0" ]'
        in source
    )
    assert "capacity_recovery_requires_existing_effect" in (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "b0_result_gate.py"
    ).read_text(encoding="utf-8")
