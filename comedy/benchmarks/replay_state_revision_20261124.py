"""Replay one authored development contrast, without network or model calls."""
import json
from pathlib import Path
import validate_run as vr
import audit_improv_relevance as ir
import check_injury_2min as sc
base = Path(__file__).resolve().parent
data = json.loads((base / "runs/2026-11-24-0855-state-revision.json").read_text(encoding="utf-8"))
tasks = data["tasks"]
responses = data["responses"]
audit = ir.audit(tasks, responses, candidates_per_task=3)
rows = []
for item in audit["items"]:
    r = next(x for x in responses if (x["task_id"], x["candidate"]) == (item["task_id"], item["candidate"]))
    c = next(x for x in data["cases"] if x["id"] == r["task_id"])
    t = next(x for x in tasks if x["id"] == r["task_id"])
    rows.append({"id": c["id"], "candidate": r["candidate"], "format_pass": not vr.score(t, r["response"]), "lexical_pass": item["gate"] == "PASS", "old_word_absent": c["old"] not in r["response"], "expected_state_consistent_by_author": r["candidate"] != "negative"})
assert rows == data["rows"], "development result drift"
fixed = {t["id"]: t for t in vr.jsonl(base / "injury-stage-exact-2026-11-23.jsonl")}
for r in data["fixed_stage_synthetic"]:
    assert (not vr.score(fixed[r["task_id"]], r["positive"])) == r["positive_accepted"]
    assert bool(vr.score(fixed[r["task_id"]], r["negative"])) == r["negative_rejected"]
md = (base.parent / "sagi-injury-help-2min-live.md").read_text(encoding="utf-8")
turns = sc.extract_dialogues(md)
assert {"issues": sc.check(md), "turns": len(turns), "characters": sum(len(s) for _, s in turns)} == data["script_static"]
print("REPLAY MATCH: 12 authored development texts, 6 synthetic fixed checks, script static")

