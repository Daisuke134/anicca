#!/usr/bin/env python3
"""loop-improve.py — REQ-C2: read tail-50 lessons + produce strategy.json.next.

Production wires this to an LLM call (= Reflexion-style verbal-RL) that takes the
brief, the strategy snapshot, and the lessons tail and writes a candidate next-strategy.

This sprint-1 implementation is the SCAFFOLD: read + write valid candidate based on
deterministic heuristic. Sprint-2 wires the LLM call.

Usage: loop-improve.py <slot>
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path


def main(slot: str) -> int:
    loop_dir = Path.home() / "loops" / slot
    lessons = loop_dir / "lessons.jsonl"
    strategy = loop_dir / "strategy.json"
    candidate = loop_dir / "strategy.json.next"

    if not strategy.exists():
        # First-pass: seed from defaults
        strategy.write_text(json.dumps({
            "priority_categories": [],
            "skip_categories": [],
            "max_apply_per_pass": 3,
            "proposal_templates": {},
            "price_defaults": {},
            "pass_count": 0,
            "improve_cadence_passes": 5,
        }, indent=2))

    cur = json.loads(strategy.read_text())

    # Read tail-50 lessons (REQ-C2)
    if lessons.exists():
        rows = [json.loads(l) for l in lessons.read_text().splitlines() if l.strip()][-50:]
    else:
        rows = []

    # Sprint-1 scaffold heuristic: bump pass_count; do not mutate priorities yet.
    # Sprint-2 wires LLM call: argv[1:] contains brief; LLM reads `rows` + `cur` and proposes.
    nxt = dict(cur)
    nxt["pass_count"] = int(cur.get("pass_count", 0)) + 1
    nxt["_last_lessons_seen"] = len(rows)
    nxt["_proposed_at"] = int(time.time())

    candidate.write_text(json.dumps(nxt, indent=2))
    print(f"loop-improve: strategy.json.next written ({len(rows)} lessons read)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "gig"))
