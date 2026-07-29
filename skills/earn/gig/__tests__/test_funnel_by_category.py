"""test_funnel_by_category.py — RED (Phase 2a, feature gig-feasibility-volume).
PROP-012 / REQ-GFV-011 — `summarize_gig_funnel_by_category(rows)`: partitions deduped rows by
`row.get("category") or "uncategorized"`, then applies the EXISTING `summarize_gig_funnel` bucketing
independently within each partition. Invariant: sum of `applied` across all returned categories ==
`summarize_gig_funnel`'s `applied` for the same input rows (partitioning never changes the total).
PROP-013 / REQ-GFV-011 (static, included here as a cheap grep companion since this test file already
imports funnel.py) — `_WON_STATUSES`/`_PAID_STATUSES` are defined exactly ONCE in funnel.py, reused
(not redefined) by the new per-category function.

`funnel.py` does not export `summarize_gig_funnel_by_category` yet -> AttributeError -> RED.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import funnel  # noqa: E402
from funnel import summarize_gig_funnel  # noqa: E402

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


by_category = funnel.summarize_gig_funnel_by_category  # RED: AttributeError, does not exist yet

chk("empty input -> {}", by_category([]), {})
chk("absent input (None) -> {}", by_category(None), {})

rows = [
    {"status": "applied", "category": "PPT/スライド"},
    {"status": "replied", "category": "PPT/スライド"},
    {"status": "applied", "category": "記事/blog"},
    {"status": "applied"},  # no category -> uncategorized
]
result = by_category(rows)
chk("row with no category lands in 'uncategorized'",
    result.get("uncategorized", {}).get("applied"), 1)
chk("PPT/スライド bucket: applied=2 (cumulative, includes the replied row), replied=1",
    (result["PPT/スライド"]["applied"], result["PPT/スライド"]["replied"]), (2, 1))
chk("記事/blog bucket: applied=1", result["記事/blog"]["applied"], 1)

# Partition-invariance property test: sum of `applied` across categories == whole-set `applied`.
random.seed(42)
statuses = ["applied", "replied", "受注", "成約", "検収完了", "支払", "no_action", "applied_0"]
categories = ["PPT/スライド", "資料作成", "記事/blog", None, "コード"]
for trial in range(20):
    synthetic_rows = [
        {"status": random.choice(statuses), **({"category": random.choice(categories)} if random.choice(categories) else {})}
        for _ in range(random.randint(0, 15))
    ]
    whole = summarize_gig_funnel(synthetic_rows)
    per_cat = by_category(synthetic_rows)
    summed_applied = sum(v["applied"] for v in per_cat.values())
    chk(f"partition-invariance trial {trial}: sum(applied) across categories == whole-set applied",
        summed_applied, whole["applied"])

# PROP-013: _WON_STATUSES / _PAID_STATUSES defined exactly once in funnel.py's source text (grep).
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "funnel.py")
src = open(src_path, encoding="utf-8").read()
chk("PROP-013: _WON_STATUSES defined exactly once in funnel.py (no duplicated vocabulary)",
    src.count("_WON_STATUSES = {"), 1)
chk("PROP-013: _PAID_STATUSES defined exactly once in funnel.py (no duplicated vocabulary)",
    src.count("_PAID_STATUSES = {"), 1)

print(f"=== test_funnel_by_category: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
