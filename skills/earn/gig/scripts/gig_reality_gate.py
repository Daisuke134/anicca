#!/usr/bin/env python3
"""gig_reality_gate.py — deterministic evidence gate (feature gig-reality-verify, behavioral-spec
REQ-007, fresh-adversary FIND-002 fix: "stop being report-blind one level up").

`gig_reality_verify.sh` must NEVER accept the fresh judge's self-reported JudgementResult JSON on
faith alone. This script reads the ACTUAL trajectory.jsonl rows the deterministic nav helper
(cdp_nav_snapshot.py) wrote during THIS run (scoped by pass_id + a min_ts run-start bound) and applies
`gig_judge.gate_verdict` — a pure, no-LLM override that downgrades an unbacked verdict:true to false.
This is the caller-side check that closes the recursive report-blind gap: the judge's own self-report
is never the last word; independently observed evidence is.

Usage:
  python3 gig_reality_gate.py <judge_raw_text> <pass_id> <required_evidence_count> <min_ts> [trajectory_root] [claims_checked]

Reads: <trajectory_root|~/gig/trajectory>/<pass_id>/trajectory.jsonl
Prints: the final gated row JSON to stdout (what gig_reality_verify.sh appends to audit-reality.jsonl)
"""
import json
import os
import re
import sys
import time

_SELF_DIR = os.path.dirname(os.path.abspath(__file__))       # .../earn/gig/scripts
_GIG_DIR = os.path.dirname(_SELF_DIR)                          # .../earn/gig
if _GIG_DIR not in sys.path:
    sys.path.insert(0, _GIG_DIR)
import gig_judge  # noqa: E402  (gig_judge.py lives one directory up)


def extract_json_obj(text: str) -> dict:
    # the judge is instructed to print ONLY the JSON object; tolerate stray whitespace/fencing.
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("no JSON object found in judge output")
    return json.loads(m.group(0))


def count_evidence_rows(pass_id: str, min_ts: int, trajectory_root: str = "~/gig/trajectory") -> int:
    """Count trajectory rows for `pass_id` with ts >= min_ts (i.e. captured DURING this run, not a
    stale leftover from a previous run reusing the same pass_id). Never counts another pass_id's rows
    — evidence is strictly scoped to the run it claims to back."""
    p = os.path.join(os.path.expanduser(trajectory_root), pass_id, "trajectory.jsonl")
    if not os.path.exists(p):
        return 0
    n = 0
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        try:
            row_ts = int(row.get("ts", 0))
        except (TypeError, ValueError):
            row_ts = 0
        if row_ts >= min_ts:
            n += 1
    return n


def build_gated_row(
    raw_text: str,
    pass_id: str,
    required_count: int,
    min_ts: int,
    trajectory_root: str = "~/gig/trajectory",
    claims_checked: int | None = None,
) -> dict:
    """Parse the judge's raw stdout, apply the deterministic evidence gate, and return the final row
    dict gig_reality_verify.sh should append to ~/gig/audit-reality.jsonl."""
    try:
        d = extract_json_obj(raw_text)
        jr = gig_judge.JudgementResult.from_dict(d)
    except Exception as e:  # noqa: BLE001 — never crash the caller on bad judge output
        jr = gig_judge.JudgementResult(verdict=False, failure_reason=f"unparseable_judge_output: {e}")

    evidence_count = count_evidence_rows(pass_id, min_ts, trajectory_root)
    gated = gig_judge.gate_verdict(jr, evidence_count, required_count)

    row = {
        "ts": int(time.time()),
        "verdict": gated.verdict,
        "reasoning": gated.reasoning,
        "failure_reason": gated.failure_reason,
        "impossible_task": gated.impossible_task,
        "reached_captcha": gated.reached_captcha,
        "pass_id": pass_id,
        "evidence_captured": evidence_count,
        "evidence_required": required_count,
    }
    if claims_checked is not None:
        row["claims_checked"] = claims_checked
    return row


def main():
    if len(sys.argv) < 5:
        print(json.dumps({
            "ts": int(time.time()), "verdict": False,
            "failure_reason": "gig_reality_gate.py: usage error (need judge_raw_text pass_id required_count min_ts)",
        }, ensure_ascii=False))
        sys.exit(1)

    raw_text, pass_id = sys.argv[1], sys.argv[2]
    required_count = int(sys.argv[3])
    min_ts = int(sys.argv[4])
    trajectory_root = sys.argv[5] if len(sys.argv) > 5 else "~/gig/trajectory"
    claims_checked = int(sys.argv[6]) if len(sys.argv) > 6 and sys.argv[6] != "" else None

    row = build_gated_row(raw_text, pass_id, required_count, min_ts, trajectory_root, claims_checked)
    print(json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()
