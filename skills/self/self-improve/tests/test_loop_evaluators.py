"""test_loop_evaluators.py — RED (Phase 2a, feature claude-p-loop-verification).
PROP-LV-023 / REQ-LV-110 — per-loop evaluators (clip/affiliate/video/gig/bounty), each a
`__REPO_ROOT__/skills/self/self-improve/<loop>/evaluator.py` copy+tweaked from
`__REPO_ROOT__/skills/earn/self-improve/evaluator.py`'s pattern: `evaluate_stage1(ledger_path) -> dict`
with a `combined_score` key. Two invariants tested per loop (Tier1, no I/O beyond reading the
read-only fixture, no LLM judge — Verifier's Law):
  1. DETERMINISM — same fixture in -> byte-identical combined_score out, twice.
  2. SANDBOX BOUNDARY — the evaluator module's own source text must never import an
     order/post/execution module (place_order, run.sh-style dispatch, browser drivers) — evaluated
     via source-text grep (matches earn/self-improve/evaluator.py's own documented sandbox
     contract: "NEVER imports any order-execution module").

None of the 5 `__REPO_ROOT__/skills/self/self-improve/<loop>/evaluator.py` files exist yet ->
ImportError for every loop -> RED.
"""
import sys, os, json, tempfile, importlib

HERE = os.path.dirname(os.path.dirname(__file__))  # .../skills/self/self-improve
sys.path.insert(0, HERE)

LOOPS = ["clip", "affiliate", "video", "gig", "bounty"]
FORBIDDEN_IMPORT_SUBSTRINGS = ["place_order", "run.sh", "cdp_apply", "browser", "playwright", "selenium"]

P = 0
F = 0


def chk(name, cond):
    global P, F
    if cond:
        print(f"  ok {name}")
        P += 1
    else:
        print(f"  FAIL {name}")
        F += 1


def make_fixture():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps({"ts": 1700000000, "views": 1000, "earn_usdc": 0.5}) + "\n")
        f.write(json.dumps({"ts": 1700003600, "views": 2000, "earn_usdc": 0.3}) + "\n")
    return path


for loop in LOOPS:
    print(f"--- loop: {loop} ---")
    fixture = make_fixture()
    try:
        mod = importlib.import_module(f"{loop}.evaluator")
        r1 = mod.evaluate_stage1(fixture)
        r2 = mod.evaluate_stage1(fixture)
        chk(f"{loop}: evaluate_stage1 returns a dict with combined_score",
            isinstance(r1, dict) and "combined_score" in r1)
        chk(f"{loop}: evaluate_stage1 is deterministic (same fixture -> same result twice)",
            r1 == r2)
        src_path = os.path.join(HERE, loop, "evaluator.py")
        src = open(src_path).read() if os.path.exists(src_path) else ""
        chk(f"{loop}: evaluator.py source does not import an order/execution module (sandbox boundary)",
            os.path.exists(src_path) and not any(s in src for s in FORBIDDEN_IMPORT_SUBSTRINGS))
    except Exception as e:
        chk(f"{loop}: evaluator module importable ({loop}/evaluator.py must exist)", False)
        print(f"    ({type(e).__name__}: {e})")
    finally:
        os.unlink(fixture)

print(f"=== test_loop_evaluators: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
