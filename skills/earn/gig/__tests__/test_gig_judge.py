"""test_gig_judge.py — RED (Phase 2a, feature gig-reality-verify, VCSDD-lean).
REQ-001/002/003/006/007/008/009 (specs/behavioral-spec.md). Copy+tweak target: browser-use/benchmark
judge.py (scratchpad/judge_bu.py, VERIFIED raw fetch 198L). gig_judge.py does not exist yet ->
ImportError -> RED.

Fresh-adversary fix round (FIND-001/002/003/004): `build_verifier_prompt` now REQUIRES a `pass_id`
argument and instructs the fresh judge to call the deterministic `cdp_nav_snapshot.py` helper (not
freeform navigation); `gate_verdict` is a new pure, no-LLM override that refuses to accept an unbacked
`verdict:true`; claim text is wrapped in `<untrusted_claim>` delimiters (prompt-injection mitigation).

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
PASS_ID = "verify-test-1783800000"

prompt1 = gig_judge.build_verifier_prompt(claims, PASS_ID, ground_truth_urls)
prompt2 = gig_judge.build_verifier_prompt(claims, PASS_ID, ground_truth_urls)
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

# ─── REQ-006/008: prompt instructs the DETERMINISTIC nav helper (not freeform navigation) ───────
chk("prompt instructs calling cdp_nav_snapshot.py (deterministic nav helper)",
    "cdp_nav_snapshot.py" in prompt1)
chk("prompt embeds the SAME pass_id passed in (stable across the run, REQ-008)",
    PASS_ID in prompt1)
chk("prompt warns that skipping the nav helper causes rejection (ties REQ-006 to REQ-007's gate)",
    any(w in low for w in ["reject", "will not be accepted", "gate", "verified independently"]))
chk("prompt requires hidden helper navigation for claim-specific pages too",
    "do not navigate freely" in low and "claim-specific" in low)

# ─── REQ-009: claims are wrapped in <untrusted_claim> delimiters (prompt-injection mitigation) ──
chk("prompt wraps claim content in <untrusted_claim> delimiters", "<untrusted_claim>" in prompt1 and "</untrusted_claim>" in prompt1)
chk("prompt warns untrusted_claim content is data, not an instruction",
    "ignore any instruction" in low or "never an instruction" in low)

# ─── Edge case: empty claims must not raise, must say nothing to verify ─────────────────────────
try:
    empty_prompt = gig_judge.build_verifier_prompt([], PASS_ID, ground_truth_urls)
    chk("empty claims -> no crash, returns str", isinstance(empty_prompt, str) and len(empty_prompt) > 0)
    chk("empty claims -> prompt states nothing to verify this round",
        any(w in empty_prompt.lower() for w in ["no claims", "nothing to verify", "0 claim"]))
except Exception as e:  # noqa: BLE001
    chk(f"empty claims must not raise (raised: {e})", False)

# ─── Edge case: empty ground_truth_urls must still instruct default Coconala mypage screens ─────
default_prompt = gig_judge.build_verifier_prompt(claims, PASS_ID, [])
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

# ─── REQ-007/PROP-009: gate_verdict — deterministic, no-LLM override (FIND-002 fix) ──────────────
chk("gig_judge exposes gate_verdict", hasattr(gig_judge, "gate_verdict"))

true_jr = gig_judge.JudgementResult.from_dict({"verdict": True, "reasoning": "looked fine"})

# the adversary's explicit case: fake verdict:true + ZERO evidence -> must NOT be accepted as a clean pass
gated_no_evidence = gig_judge.gate_verdict(true_jr, evidence_count=0, required_count=3)
chk("gate_verdict: verdict:true + 0 evidence (required 3) -> downgraded to false",
    gated_no_evidence.verdict is False)
chk("gate_verdict: downgraded result carries a failure_reason explaining why",
    bool(gated_no_evidence.failure_reason) and "evidence" in gated_no_evidence.failure_reason.lower())

# partial evidence (still short) -> still downgraded
gated_partial = gig_judge.gate_verdict(true_jr, evidence_count=1, required_count=3)
chk("gate_verdict: verdict:true + 1/3 evidence -> still downgraded to false",
    gated_partial.verdict is False)

# sufficient evidence -> verdict passes through unchanged
gated_ok = gig_judge.gate_verdict(true_jr, evidence_count=3, required_count=3)
chk("gate_verdict: verdict:true + evidence_count==required_count -> unchanged (still true)",
    gated_ok.verdict is True and gated_ok.reasoning == true_jr.reasoning)

# more than enough evidence -> still fine
gated_extra = gig_judge.gate_verdict(true_jr, evidence_count=5, required_count=3)
chk("gate_verdict: verdict:true + evidence_count>required_count -> unchanged (still true)",
    gated_extra.verdict is True)

# a genuinely false verdict from the judge is NEVER upgraded, regardless of evidence
false_jr = gig_judge.JudgementResult.from_dict({"verdict": False, "failure_reason": "typo still present"})
gated_false = gig_judge.gate_verdict(false_jr, evidence_count=10, required_count=3)
chk("gate_verdict: verdict:false is never upgraded to true by evidence presence",
    gated_false.verdict is False and gated_false.failure_reason == "typo still present")

# required_count of 0 (no ground truth urls configured) -> any evidence_count trivially satisfies it
gated_zero_required = gig_judge.gate_verdict(true_jr, evidence_count=0, required_count=0)
chk("gate_verdict: required_count==0 -> verdict:true passes through unchanged",
    gated_zero_required.verdict is True)

print(f"=== test_gig_judge: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
