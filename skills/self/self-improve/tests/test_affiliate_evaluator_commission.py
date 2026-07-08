"""test_affiliate_evaluator_commission.py — F-ITER3-4 fix regression test. affiliate_verify.py
(REQ-LV-014) writes rows shaped {ts, slideshow_url, views, commission_jpy, ok} to
~/.cloak/affiliate-metrics.jsonl — NOT earn_usdc/earn_jpy. Before the fix, ledger_metrics.py's
score_from_rows() only checked earn_usdc/earn_jpy, so a real, non-null commission_jpy value was
silently ignored and the affiliate evaluator's combined_score was views-only forever, contradicting
its own docstring ("views weight + commission earn weight"). This proves the earn term now
actually responds to commission_jpy.
"""
import importlib.util
import json
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../self-improve
sys.path.insert(0, _HERE)
_spec = importlib.util.spec_from_file_location("affiliate_evaluator", os.path.join(_HERE, "affiliate", "evaluator.py"))
AFF_EVAL = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(AFF_EVAL)

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


def write_ledger(rows):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return path


# real affiliate_verify.py row shape: {ts, slideshow_url, views, commission_jpy, ok}
zero_commission = write_ledger([
    {"ts": 1700000000, "slideshow_url": "https://www.instagram.com/p/A/", "views": None, "commission_jpy": None, "ok": True},
])
score_zero = AFF_EVAL.evaluate_stage1(zero_commission)["combined_score"]
chk("commission_jpy=null (per-post attribution genuinely impossible) -> earn term contributes 0",
    score_zero, 0.0)

with_commission = write_ledger([
    {"ts": 1700000000, "slideshow_url": "https://www.instagram.com/p/A/", "views": 100, "commission_jpy": 500.0, "ok": True},
])
score_with = AFF_EVAL.evaluate_stage1(with_commission)["combined_score"]
chk("F-ITER3-4 fix: a real commission_jpy value now DOES move combined_score "
    "(100 views + 500 commission_jpy = 600.0, not 100.0)", score_with, 600.0)

os.unlink(zero_commission)
os.unlink(with_commission)

print(f"=== test_affiliate_evaluator_commission: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
