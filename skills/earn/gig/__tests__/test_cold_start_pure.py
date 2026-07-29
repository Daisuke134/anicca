"""test_cold_start_pure.py — RED (Phase 2a, feature gig-feasibility-volume).
PROP-022 / REQ-GFV-017 — the `cold_start` sum-and-compare sub-logic, factored out to be pure
(callable with an in-memory `earnings_rows` list, per verification-architecture.md §1's Purity
Boundary Map). Reuses `run.sh`'s EXISTING `SETTLED` status set and `jnum()` tolerant-numeric-parse
convention verbatim, rather than redefining them (DRY — one status-set literal).

Design contract this test locks in:
    passprep.compute_cold_start(earnings_rows) -> bool
True WHEN cumulative sum of `jpy` across rows whose `status` is in SETTLED = {検収,支払,検収完了,
completed,paid} AND carry a non-empty `evidence` field AND `jpy>0` (after jnum-style tolerant parse)
is 0, else False. cold_start is cumulative-to-date, never derived from a trailing window.

`passprep.py` does not export `compute_cold_start` yet -> ImportError -> RED.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import passprep  # noqa: E402  RED: compute_cold_start does not exist yet

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


chk("0 SETTLED-status rows (empty list) -> cold_start:true",
    passprep.compute_cold_start([]), True)

chk("absent earnings_rows (None) -> cold_start:true",
    passprep.compute_cold_start(None), True)

one_settled_row = [{"status": "検収", "jpy": 1, "evidence": "https://example.com/proof.png"}]
chk("exactly one SETTLED row, jpy:1, non-empty evidence -> cold_start:false",
    passprep.compute_cold_start(one_settled_row), False)

string_jpy_row = [{"status": "支払", "jpy": "¥40,000", "evidence": "invoice-42.pdf"}]
chk("jpy as '¥40,000'-style string parses via jnum() convention -> contributes 40000, cold_start:false",
    passprep.compute_cold_start(string_jpy_row), False)

empty_evidence_row = [{"status": "検収完了", "jpy": 5000, "evidence": ""}]
chk("SETTLED row with EMPTY evidence does NOT count (matches run.sh's own exclusion) -> cold_start:true",
    passprep.compute_cold_start(empty_evidence_row), True)

non_settled_row = [{"status": "見積中", "jpy": 5000, "evidence": "x"}]
chk("non-SETTLED status row does not count -> cold_start:true",
    passprep.compute_cold_start(non_settled_row), True)

zero_jpy_row = [{"status": "completed", "jpy": 0, "evidence": "x"}]
chk("SETTLED row with jpy<=0 does not count -> cold_start:true",
    passprep.compute_cold_start(zero_jpy_row), True)

mixed_rows = [
    {"status": "no_action"},
    {"status": "検収", "jpy": 3000, "evidence": "y"},
    {"status": "検収完了", "jpy": "", "evidence": "z"},  # unparseable jpy -> 0, never crash
]
chk("mixed rows: unparseable jpy string never crashes, contributes 0; one real settled row -> cold_start:false",
    passprep.compute_cold_start(mixed_rows), False)

print(f"=== test_cold_start_pure: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
