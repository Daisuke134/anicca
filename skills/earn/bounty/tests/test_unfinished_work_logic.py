"""Deterministic reference reimplementation of bounty-cli.sh STARTUP step (0)'s
"CHECK FOR UNFINISHED WORK FIRST" NL-prompt logic (docs/superpowers/specs/
2026-07-05-affiliate-bounty-state-machine-design.md §3/§5). This does NOT prove the
LLM will actually follow the prompt text -- it proves the described algorithm itself
is logically sound (no infinite duplication, no permanent deadlock) against 3 fixtures.
Run: python3 test_unfinished_work_logic.py
"""
import sys

BOUNTY_STALE_DAYS = 7
SECONDS_PER_DAY = 86400


def decide_unfinished_work_action(attempts, now):
    """attempts: list of dicts (jsonl lines, in file order). Returns one of:
    "no-unfinished-work" | "abandon:<key>" | "continue-pr:<key>" | "skip-resolved"
    Mirrors the exact predicate in bounty-cli.sh STARTUP step (0)."""
    stalled_keys = {a["key"] for a in attempts if a.get("status") == "stalled" and a.get("key")}
    for a in attempts:
        key = a.get("key")
        if not key or key in stalled_keys:
            continue  # already resolved, never re-evaluate (this is the FIND-1 fix)
        if a.get("status") == "claim" and a.get("pr") is None:
            wake = a.get("wake")
            try:
                wake_f = float(wake)
                is_stale = (now - wake_f) >= BOUNTY_STALE_DAYS * SECONDS_PER_DAY
            except (TypeError, ValueError):
                is_stale = False  # missing/non-numeric wake -> treat as fresh, never crash
            if is_stale:
                return f"abandon:{key}"
            return f"continue-pr:{key}"
    return "no-unfinished-work"


NOW = 1_700_000_000


def test_stale_claim_no_stalled_line_yet_abandons():
    attempts = [{"key": "o/r#1", "status": "claim", "pr": None, "wake": str(NOW - 8 * SECONDS_PER_DAY)}]
    assert decide_unfinished_work_action(attempts, NOW) == "abandon:o/r#1"


def test_stale_claim_already_stalled_is_skipped_not_reabandoned():
    """The exact bug GATE 1 round 4 found: must NOT re-trigger abandon for an
    already-resolved key on a later day."""
    attempts = [
        {"key": "o/r#1", "status": "claim", "pr": None, "wake": str(NOW - 8 * SECONDS_PER_DAY)},
        {"key": "o/r#1", "status": "stalled"},
    ]
    assert decide_unfinished_work_action(attempts, NOW) == "no-unfinished-work"
    # even many days later, still no re-abandonment
    assert decide_unfinished_work_action(attempts, NOW + 30 * SECONDS_PER_DAY) == "no-unfinished-work"


def test_fresh_claim_under_7_days_continues_pr():
    attempts = [{"key": "o/r#2", "status": "claim", "pr": None, "wake": str(NOW - 3 * SECONDS_PER_DAY)}]
    assert decide_unfinished_work_action(attempts, NOW) == "continue-pr:o/r#2"


def test_boundary_exactly_7_days_is_stale():
    attempts = [{"key": "o/r#3", "status": "claim", "pr": None, "wake": str(NOW - 7 * SECONDS_PER_DAY)}]
    assert decide_unfinished_work_action(attempts, NOW) == "abandon:o/r#3"


def test_missing_wake_treated_as_fresh_not_crash():
    attempts = [{"key": "o/r#4", "status": "claim", "pr": None}]  # no wake field
    assert decide_unfinished_work_action(attempts, NOW) == "continue-pr:o/r#4"


def test_non_numeric_wake_treated_as_fresh_not_crash():
    attempts = [{"key": "o/r#5", "status": "claim", "pr": None, "wake": "test-wake-1"}]
    assert decide_unfinished_work_action(attempts, NOW) == "continue-pr:o/r#5"


def test_claim_with_pr_set_is_not_unfinished():
    attempts = [{"key": "o/r#6", "status": "claim", "pr": 42, "wake": str(NOW - 30 * SECONDS_PER_DAY)}]
    assert decide_unfinished_work_action(attempts, NOW) == "no-unfinished-work"


def test_empty_attempts_is_no_unfinished_work():
    assert decide_unfinished_work_action([], NOW) == "no-unfinished-work"


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"  ok  {fn.__name__}")
        except Exception:
            failed += 1; print(f"  FAIL {fn.__name__}"); traceback.print_exc()
    print(f"\n{len(fns)-failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
