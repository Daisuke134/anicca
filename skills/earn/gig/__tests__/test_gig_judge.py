"""test_gig_judge.py — RED (Phase 2a, feature gig-reality-verify, VCSDD-lean).
REQ-001/002/003 (specs/behavioral-spec.md). Copy+tweak target: browser-use/benchmark judge.py
(scratchpad/judge_bu.py, VERIFIED raw fetch 198L). gig_judge.py does not exist yet -> ImportError -> RED.

Plain-assert style, matching this repo's existing convention (skills/self/tests/test_gig_ts_parser.py) —
no pytest/hypothesis dependency, runnable directly: `python3 test_gig_judge.py`.
"""
import importlib.util
import os
import sys

_SELF_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../earn/gig
_MODULE_PATH = os.path.join(_SELF_DIR, "gig_judge.py")

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


# ─── REQ-001: module must import with stdlib only, and expose a pure function ──────────────────
if not os.path.exists(_MODULE_PATH):
    print(f"  FAIL gig_judge.py does not exist yet at {_MODULE_PATH}")
    print("=== test_gig_judge: 0 passed 1 failed (RED: module missing) ===")
    sys.exit(1)

_spec = importlib.util.spec_from_file_location("gig_judge", _MODULE_PATH)
gig_judge = importlib.util.module_from_spec(_spec)
sys.modules["gig_judge"] = gig_judge  # dataclass needs the module registered in sys.modules
_spec.loader.exec_module(gig_judge)  # RED until file exists / imports cleanly

chk("gig_judge exposes build_verifier_prompt", hasattr(gig_judge, "build_verifier_prompt"))
chk("gig_judge exposes JudgementResult", hasattr(gig_judge, "JudgementResult"))

# ─── REQ-001/002: build_verifier_prompt is pure and report-skeptical ────────────────────────────
claims = [
    {"kind": "shuppin", "title": "業務自動化スクリプト Python/Node.js", "status": "published", "price_jpy": 10000},
    {"kind": "earnings", "requestId": "999", "jpy": 40000, "status": "検収完了", "evidence": "screenshot.png"},
]
ground_truth_urls = [
    "https://coconala.com/mypage/services_lists",
    "https://coconala.com/mypage/received_orders/open",
]

prompt1 = gig_judge.build_verifier_prompt(claims, ground_truth_urls)
prompt2 = gig_judge.build_verifier_prompt(claims, ground_truth_urls)
chk("build_verifier_prompt returns a non-empty str", isinstance(prompt1, str) and len(prompt1) > 0)
chk("build_verifier_prompt is pure (same input -> identical output)", prompt1 == prompt2)

low = prompt1.lower()
chk("prompt contains a doubtful/skeptical-class phrase",
    any(w in low for w in ["doubtful", "skeptic", "be initially doubtful"]))
chk("prompt contains a ground truth phrase", "ground truth" in low or "ground_truth" in low)
chk("prompt instructs mismatch -> verdict must be false",
    "false" in low and ("must be false" in low or "verdict.*false" in low or "should be false" in low or "verdict must be false" in low))
chk("prompt instructs binary true/false verdict (not a rubric/score)",
    "true" in low and "false" in low and ("binary" in low or ("true or false" in low)))
chk("prompt includes the ground_truth_urls verbatim", all(u in prompt1 for u in ground_truth_urls))
chk("prompt includes claim content verbatim (Japanese preserved)",
    "業務自動化スクリプト" in prompt1 and "40000" in prompt1)

# ─── Edge case: empty claims must not raise, must say nothing to verify ─────────────────────────
try:
    empty_prompt = gig_judge.build_verifier_prompt([], ground_truth_urls)
    chk("empty claims -> no crash, returns str", isinstance(empty_prompt, str) and len(empty_prompt) > 0)
    chk("empty claims -> prompt states nothing to verify this round",
        any(w in empty_prompt.lower() for w in ["no claims", "nothing to verify", "0 claim"]))
except Exception as e:  # noqa: BLE001
    chk(f"empty claims must not raise (raised: {e})", False)

# ─── Edge case: empty ground_truth_urls must still instruct default Coconala mypage screens ─────
default_prompt = gig_judge.build_verifier_prompt(claims, [])
chk("empty ground_truth_urls -> prompt still names default Coconala mypage screens",
    "services_lists" in default_prompt and "received_orders" in default_prompt)

# ─── REQ-003: JudgementResult ────────────────────────────────────────────────────────────────────
jr = gig_judge.JudgementResult.from_dict({"verdict": True})
chk("JudgementResult.from_dict minimal dict -> verdict True", jr.verdict is True)
chk("JudgementResult.from_dict defaults reasoning to None", jr.reasoning is None)
chk("JudgementResult.from_dict defaults failure_reason to None", jr.failure_reason is None)
chk("JudgementResult.from_dict defaults impossible_task to False", jr.impossible_task is False)
chk("JudgementResult.from_dict defaults reached_captcha to False", jr.reached_captcha is False)

jr2 = gig_judge.JudgementResult.from_dict({
    "verdict": False, "reasoning": "screen shows draft, not published",
    "failure_reason": "listing still draft", "impossible_task": False, "reached_captcha": False,
})
chk("JudgementResult.from_dict full dict round-trips verdict", jr2.verdict is False)
chk("JudgementResult.from_dict full dict round-trips failure_reason", jr2.failure_reason == "listing still draft")

try:
    gig_judge.JudgementResult.from_dict({})
    chk("JudgementResult.from_dict({}) must raise (missing required verdict)", False)
except Exception:
    chk("JudgementResult.from_dict({}) raises on missing verdict", True)

print(f"=== test_gig_judge: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
