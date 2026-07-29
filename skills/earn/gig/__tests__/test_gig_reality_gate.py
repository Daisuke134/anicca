"""test_gig_reality_gate.py — RED (Phase 2a, feature gig-reality-verify, fresh-adversary fix round).
REQ-007/PROP-010 (specs/behavioral-spec.md, verification-architecture.md): a dedicated,
directly-testable script that reads the REAL trajectory file for a pass_id and applies
`gig_judge.gate_verdict` before `gig_reality_verify.sh` is allowed to accept a verdict:true as a clean
pass. `scripts/gig_reality_gate.py` does not exist yet -> RED.

Adversary's explicit ask: "Add a test: fake a verdict:true + empty trajectory -> script must NOT
accept it as a clean pass." Uses a TEMP trajectory root (never touches the real ~/gig/trajectory), so
this is runnable in any environment without a live browser/LLM.

Plain-assert style (repo convention), runnable directly: `python3 test_gig_reality_gate.py`.
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SELF_DIR = os.path.dirname(_TESTS_DIR)  # .../earn/gig
_GATE_PATH = os.path.join(_SELF_DIR, "scripts", "gig_reality_gate.py")

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


if not os.path.exists(_GATE_PATH):
    print(f"  FAIL scripts/gig_reality_gate.py does not exist yet at {_GATE_PATH}")
    print("=== test_gig_reality_gate: 0 passed 1 failed (RED: module missing) ===")
    sys.exit(1)

_spec = importlib.util.spec_from_file_location("gig_reality_gate", _GATE_PATH)
gate_mod = importlib.util.module_from_spec(_spec)
sys.modules["gig_reality_gate"] = gate_mod
_spec.loader.exec_module(gate_mod)  # RED until file exists / imports cleanly

chk("gig_reality_gate exposes count_evidence_rows", hasattr(gate_mod, "count_evidence_rows"))
chk("gig_reality_gate exposes build_gated_row", hasattr(gate_mod, "build_gated_row"))

_tmp = tempfile.mkdtemp(prefix="gig_reality_gate_test_")
try:
    PASS_ID = "test-pass-001"
    run_start = int(time.time())

    # ─── the adversary's explicit case: verdict:true + EMPTY trajectory -> NOT a clean pass ───────
    empty_raw = json.dumps({"verdict": True, "reasoning": "looked fine", "failure_reason": ""})
    row = gate_mod.build_gated_row(empty_raw, PASS_ID, required_count=3, min_ts=run_start, trajectory_root=_tmp)
    chk("verdict:true + empty trajectory dir -> gated row is NOT verdict:true (rejected as unbacked)",
        row.get("verdict") is False)
    chk("gated row explains WHY (evidence-missing failure_reason)",
        "evidence" in (row.get("failure_reason") or "").lower())
    chk("gated row reports evidence_captured == 0", row.get("evidence_captured") == 0)

    # ─── trajectory dir exists but has ZERO rows for this run (file present, empty) ────────────────
    pdir = os.path.join(_tmp, PASS_ID)
    os.makedirs(pdir, exist_ok=True)
    open(os.path.join(pdir, "trajectory.jsonl"), "w").close()
    row2 = gate_mod.build_gated_row(empty_raw, PASS_ID, required_count=3, min_ts=run_start, trajectory_root=_tmp)
    chk("verdict:true + trajectory.jsonl present but 0 rows -> still gated to false",
        row2.get("verdict") is False)

    # ─── trajectory rows exist but are STALE (before this run's min_ts) -> do not count ────────────
    with open(os.path.join(pdir, "trajectory.jsonl"), "a") as f:
        for i in range(3):
            f.write(json.dumps({"ts": run_start - 1000, "pass_id": PASS_ID, "seq": str(i)}) + "\n")
    row3 = gate_mod.build_gated_row(empty_raw, PASS_ID, required_count=3, min_ts=run_start, trajectory_root=_tmp)
    chk("verdict:true + 3 STALE (pre-run) trajectory rows -> still gated to false (not counted)",
        row3.get("verdict") is False)

    # ─── sufficient FRESH evidence (>= required_count, ts >= min_ts) -> accepted, stays true ────────
    with open(os.path.join(pdir, "trajectory.jsonl"), "a") as f:
        for i in range(3):
            f.write(json.dumps({"ts": run_start + 5 + i, "pass_id": PASS_ID, "seq": f"fresh{i}"}) + "\n")
    row4 = gate_mod.build_gated_row(empty_raw, PASS_ID, required_count=3, min_ts=run_start, trajectory_root=_tmp)
    chk("verdict:true + 3 FRESH trajectory rows (== required_count) -> accepted (still true)",
        row4.get("verdict") is True)
    chk("accepted row reports evidence_captured >= required_count",
        row4.get("evidence_captured", 0) >= 3)

    # ─── a genuinely false verdict is reported as false regardless of evidence ─────────────────────
    false_raw = json.dumps({"verdict": False, "failure_reason": "typo still present"})
    row5 = gate_mod.build_gated_row(false_raw, PASS_ID, required_count=3, min_ts=run_start, trajectory_root=_tmp)
    chk("verdict:false from the judge stays false even with full evidence",
        row5.get("verdict") is False and row5.get("failure_reason") == "typo still present")

    # ─── unparseable judge output -> gated row is false with a clear reason, never crashes ─────────
    row6 = gate_mod.build_gated_row("not json at all", PASS_ID, required_count=3, min_ts=run_start, trajectory_root=_tmp)
    chk("unparseable judge output -> gated row verdict:false, no crash",
        row6.get("verdict") is False and "unparseable" in (row6.get("failure_reason") or "").lower())

    # ─── count_evidence_rows directly: different pass_id's rows never leak into this run's count ───
    other_dir = os.path.join(_tmp, "other-pass-id")
    os.makedirs(other_dir, exist_ok=True)
    with open(os.path.join(other_dir, "trajectory.jsonl"), "w") as f:
        for i in range(5):
            f.write(json.dumps({"ts": run_start + 100, "pass_id": "other-pass-id", "seq": str(i)}) + "\n")
    n = gate_mod.count_evidence_rows(PASS_ID, run_start, _tmp)
    chk("count_evidence_rows(PASS_ID) unaffected by a DIFFERENT pass_id's trajectory dir", n == 3)
finally:
    shutil.rmtree(_tmp, ignore_errors=True)

print(f"=== test_gig_reality_gate: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
