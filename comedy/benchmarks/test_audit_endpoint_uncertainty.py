#!/usr/bin/env python3
"""15 smoke/regression assertions for synthetic annotation-boundary sensitivity."""
from audit_endpoint_uncertainty import audit


def fixture(gap=50, ai_end=300, stage_end=1000):
    return {
        "scenario_id": "synthetic-endpoint-jitter",
        "gate": "PASS",
        "timing_audit": {"reply_gap_ms": [{"ai_event": 2, "dais_event": 1, "gap_ms": gap}]},
        "normalized_events": [
            {"speaker": "dais", "cue": "start", "text": "痛い", "start_ms": 0, "end_ms": 100},
            {"speaker": "ai", "text": "はい", "start_ms": 150, "end_ms": ai_end},
            {"speaker": "dais", "cue": "end", "text": "もういい", "start_ms": stage_end - 100, "end_ms": stage_end},
        ],
    }


def run_smoke():
    cases = [
        (50, 100, "BOUNDARY_SENSITIVE"),
        (-50, 100, "BOUNDARY_SENSITIVE"),
        (400, 100, "ROBUST_NONOVERLAP_FOR_TESTED_BOUNDARIES"),
        (-400, 100, "ROBUST_OVERLAP_PRESENT"),
        (200, 100, "ROBUST_NONOVERLAP_FOR_TESTED_BOUNDARIES"),
        (-200, 100, "BOUNDARY_SENSITIVE"),
        (0, 0, "ROBUST_NONOVERLAP_FOR_TESTED_BOUNDARIES"),
    ]
    for gap, error, wanted in cases:
        result = audit(fixture(gap=gap), endpoint_error_ms=error)
        assert result["robustness"] == wanted, (gap, error, result["robustness"], wanted)
    assert audit(fixture(gap=400, ai_end=1050), endpoint_error_ms=100)["robustness"] == "BOUNDARY_SENSITIVE"
    assert audit(fixture(gap=400, ai_end=1400), endpoint_error_ms=100)["robustness"] == "ROBUST_OVERLAP_PRESENT"
    assert audit(fixture(gap=400, ai_end=600), endpoint_error_ms=100)["robustness"] == "ROBUST_NONOVERLAP_FOR_TESTED_BOUNDARIES"
    missing = fixture(gap=400)
    missing["normalized_events"][-1]["cue"] = None
    assert audit(missing, endpoint_error_ms=100)["robustness"] == "NOT_ASSESSABLE"
    for bad in [-1, True, "100"]:
        try:
            audit(fixture(), endpoint_error_ms=bad)
        except ValueError:
            pass
        else:
            raise AssertionError("bad error accepted " + repr(bad))
    try:
        audit({"normalized_events": [], "timing_audit": {"reply_gap_ms": [{"gap_ms": True}]}}, endpoint_error_ms=10)
    except ValueError:
        pass
    else:
        raise AssertionError("boolean gap accepted")
    print("REGRESSION_PASS", len(cases) + 3 + 1 + 3 + 1)


if __name__ == "__main__":
    run_smoke()
