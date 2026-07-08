"""test_gig_evaluator_by_category.py — RED (Phase 2a, feature gig-feasibility-volume).
PROP-016 / REQ-GFV-013 — `evaluator.py::evaluate_stage1`'s existing signature/return-shape/behavior
is UNCHANGED (regression) on a funnel-shaped fixture ledger identical in shape to one used BEFORE
this feature (top-level applied/replied/won/paid_jpy keys, no by_category). NOTE: this is a
DIFFERENT, narrower fixture than the generic (non-funnel-shaped) one in the pre-existing
test_loop_evaluators.py (which stays untouched/green and only exercises the sandbox-boundary +
generic-ledger determinism invariants, never the funnel-shaped `_funnel_score` branch this file
pins with an exact golden value).
PROP-018 / REQ-GFV-013 — the NEW per-category scoring function: given `gig-funnel.jsonl` row dicts
(already parsed) -> `{category: {reply_rate, win_rate, paid_jpy}}`. A `by_category`-less (old-schema)
row fed into it contributes ZERO to every category tally without raising (backward-compat with rows
written before this feature shipped).

`gig/evaluator.py` does not export `evaluate_by_category` yet -> AttributeError -> RED.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../skills/self/self-improve
sys.path.insert(0, HERE)
from gig import evaluator  # noqa: E402

P = 0
F = 0


def chk(name, got, want):
    global P, F
    if got == want:
        print(f"  ok {name} ({got})")
        P += 1
    else:
        print(f"  FAIL {name} want={want} got={got}")
        F += 1


def make_funnel_fixture():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    rows = [
        {"ts": 1700000000, "pass_id": "p1", "applied": 4, "replied": 2, "won": 1, "paid": 0},
        {"ts": 1700003600, "pass_id": "p2", "applied": 6, "replied": 3, "won": 1, "paid": 1, "paid_jpy": 8000},
    ]
    with os.fdopen(fd, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return path


# --- PROP-016: golden-output regression pin, funnel-shaped fixture (pre-existing _funnel_score math) ---
fixture = make_funnel_fixture()
try:
    result = evaluator.evaluate_stage1(fixture)
    chk("PROP-016: evaluate_stage1 still returns dict with combined_score + rows_evaluated (shape unchanged)",
        set(result.keys()) >= {"combined_score", "rows_evaluated"}, True)
    chk("PROP-016: rows_evaluated == 2 (unchanged counting behavior)", result["rows_evaluated"], 2)
    # golden value pinned from the EXISTING, unmodified _funnel_score formula:
    # applied=10, replied=5, won=2, paid_jpy=8000 -> reply_rate=0.5, win_rate=0.4, score=8000.9
    expected_score = round((5 / 10) + (2 / 5) + 8000, 6)
    chk("PROP-016: combined_score golden value unchanged by this feature (_funnel_score formula pinned)",
        round(result["combined_score"], 6), expected_score)
finally:
    os.unlink(fixture)

# --- PROP-018: new per-category function ---------------------------------------------------
evaluate_by_category = evaluator.evaluate_by_category  # RED: AttributeError, does not exist yet

rows_with_category = [
    {"ts": 1, "by_category": {"PPT/スライド": {"applied": 4, "replied": 2, "won": 1, "paid": 0}}},
    {"ts": 2, "by_category": {"PPT/スライド": {"applied": 2, "replied": 1, "won": 1, "paid": 1},
                               "資料作成": {"applied": 3, "replied": 0, "won": 0, "paid": 0}}},
]
by_cat = evaluate_by_category(rows_with_category)
chk("evaluate_by_category returns a dict keyed by category",
    isinstance(by_cat, dict) and "PPT/スライド" in by_cat, True)
chk("evaluate_by_category: PPT/スライド reply_rate/win_rate are floats",
    isinstance(by_cat["PPT/スライド"]["reply_rate"], float), True)
chk("evaluate_by_category: 資料作成 present with zero reply/win rates",
    (by_cat["資料作成"]["reply_rate"], by_cat["資料作成"]["win_rate"]), (0.0, 0.0))

# Mixed-schema: an OLD row lacking by_category entirely must not raise and contributes zero.
rows_mixed = [
    {"ts": 0, "applied": 5, "replied": 2, "won": 1, "paid": 1},  # old-schema row, no by_category
    {"ts": 1, "by_category": {"コード": {"applied": 1, "replied": 1, "won": 0, "paid": 0}}},
]
try:
    by_cat_mixed = evaluate_by_category(rows_mixed)
    chk("PROP-018: mixed-schema (old row without by_category) does not raise",
        isinstance(by_cat_mixed, dict), True)
    chk("PROP-018: old-schema row contributes zero (only コード from the new-schema row appears)",
        list(by_cat_mixed.keys()), ["コード"])
except Exception as e:
    chk(f"PROP-018: mixed-schema must not raise, but got {type(e).__name__}: {e}", False, True)

print(f"=== test_gig_evaluator_by_category: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
