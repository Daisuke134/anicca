"""Tests for application_report. Run: python3 tests/test_application_report.py

X8b (2026-07-27). Measured before this existed: applied.jsonl held 224 rows and only
27 carried a category, so category_bandit's arms saw reward for almost nothing -- the
two attributed payments landed on category=None and never reached an arm.

The cause was that nothing in code ever recorded what an application WAS. The apply
lane wrote its own ledger row from a prompt, so the category field simply drifted out
of existence. This module closes that: the model REPORTS applications in its step
result, and code writes the ledger row.

The properties pinned here are the ones that make the number trustworthy rather than
merely present:
  * a report without a submission screenshot is never written (no invented applications)
  * a report without a category still gets a row, with category=None (no invented labels)
  * where a category came from is recorded, so self-report can be told from evidence
  * running twice does not duplicate or mutate anything
"""

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "application_report.py"
SCHEMA_PATH = ROOT / "schemas" / "gig_b2_result.schema.json"

spec = importlib.util.spec_from_file_location("application_report", SCRIPT)
ar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ar)

FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  {detail}" if not ok else ""))
    if not ok:
        FAILURES.append(label)


NOW = 1_785_120_000.0
PASS_ID = "1785119405-48257"

REPORT = [{
    "request_id": "5176621",
    "bucket": "single",
    "category": "動画編集・映像制作",
    "title": "Remotion動画生成｜AIへの指示書作成者募集",
    "price_jpy": 8000,
    "deliver_date": "2026-07-30",
    # X24: strict structured outputs make the model answer every key, so an unknown
    # value arrives as null rather than as an absent key. The fixture matches what
    # the wire will actually carry.
    "url": None,
    "compensation_type": None,
    "weekly_days": None,
    "weekly_hours_min": None,
    "weekly_hours_max": None,
}]

CURRENT_B2 = {
    "context_path": "/tmp/b2-context.json",
    "context_sha256": "a" * 64,
    "marketplace_url": "https://coconala.com/requests?sort=new",
    "marketplace_screenshot_path": "/tmp/requests.png",
    "marketplace_live_dom_path": "/tmp/requests.json",
    "inspected_requests": [],
    "search_sources": [],
}


def plan(report, existing=(), proven=frozenset({"5176621"}), dom=None):
    return ar.plan(
        report=report,
        existing_rows=[dict(r) for r in existing],
        proven=set(proven),
        dom_categories=dict(dom or {}),
        now=NOW,
        pass_id=PASS_ID,
    )


# --- the row code writes, not the model -----------------------------------------
rows, stats = plan(REPORT)
check("a proven reported application becomes a ledger row", len(rows) == 1, str(rows))
row = rows[0] if rows else {}
check("the row carries the category the model reported",
      row.get("category") == "動画編集・映像制作", str(row))
check("a self-reported category is labelled as such",
      row.get("category_source") == "agent", str(row))
check("the row is countable by existing readers (ts + status)",
      row.get("status") == "applied" and row.get("ts") == int(NOW), str(row))
check("the row keys on the 募集 id the same way applied.jsonl already does",
      row.get("requestId") == "5176621", str(row))
check("the pass that produced it is recorded", row.get("pass_id") == PASS_ID, str(row))
check("one append is counted", stats.get("appended") == 1, str(stats))

# --- it must never be able to invent an application ------------------------------
rows, stats = plan(REPORT, proven=frozenset())
check("without a submission screenshot no row is written", rows == [], str(rows))
check("the unproven report is counted, not silently dropped",
      stats.get("unproven") == 1, str(stats))

rows, _ = plan([{"request_id": "", "category": "x"}], proven=frozenset({""}))
check("a report with no request id is refused", rows == [], str(rows))

# --- a missing category must not become a fabricated one -------------------------
rows, stats = plan([{"request_id": "5176621", "title": "t"}])
check("a category-less application still gets a row", len(rows) == 1, str(rows))
check("the missing category stays null rather than guessed",
      rows[0].get("category") is None, str(rows[0]))
check("a null category has no source", rows[0].get("category_source") is None,
      str(rows[0]))
check("the gap is visible as a metric", stats.get("category_missing") == 1, str(stats))

rows, _ = plan([{"request_id": "5176621", "category": "   "}])
check("a blank category is treated as missing, not as a label",
      rows[0].get("category") is None, str(rows[0]))

# --- evidence outranks self-report ------------------------------------------------
rows, stats = plan(REPORT, dom={"5176621": "経理・財務・税務代行"})
check("a category read off the page beats the model's own claim",
      rows[0].get("category") == "経理・財務・税務代行", str(rows[0]))
check("an evidence-derived category is labelled dom",
      rows[0].get("category_source") == "dom", str(rows[0]))
check("dom and agent sources are counted separately",
      stats.get("category_dom") == 1 and stats.get("category_agent") == 0, str(stats))

# --- duplicates: the model may also have written its own row ----------------------
mine = {"requestId": "5176621", "ts": 1785078000, "status": "applied", "title": "t"}
rows, stats = plan(REPORT, existing=[mine])
check("an application already in the ledger is not appended twice",
      len(rows) == 1, str(rows))
check("the duplicate is counted", stats.get("skipped_duplicate") == 1, str(stats))
check("the existing row is enriched with the missing category instead",
      rows[0].get("category") == "動画編集・映像制作"
      and rows[0].get("category_source") == "agent", str(rows[0]))
check("the enrichment is counted", stats.get("enriched") == 1, str(stats))

labelled = dict(mine, category="経理・財務・税務代行", category_source="agent")
rows, stats = plan(REPORT, existing=[labelled])
check("a category already on the row is never overwritten",
      rows[0].get("category") == "経理・財務・税務代行", str(rows[0]))
check("nothing is counted as enriched when nothing changed",
      stats.get("enriched") == 0, str(stats))

# A paid_progress row keys on the TALKROOM id and can collide with a 募集 id. It is
# not an application row, so it must not suppress the application's own row.
progress = {"requestId": "5176621", "ts": 1785047809, "status": "replied",
            "action": "paid_progress"}
rows, stats = plan(REPORT, existing=[progress])
check("an action row does not masquerade as the application row",
      len(rows) == 2 and stats.get("appended") == 1, str(rows))
check("the action row is left exactly as it was",
      rows[0] == progress, str(rows[0]))

# --- torn ledger lines survive ----------------------------------------------------
rows, _ = plan(REPORT, existing=[{"_unparsed": "{broken"}])
check("a torn line is preserved, not dropped",
      rows[0] == {"_unparsed": "{broken"}, str(rows[0]))

# --- reading the model's report out of the runner summary -------------------------
work = Path(tempfile.mkdtemp())
step_evidence = work / "agent-B2"
step_evidence.mkdir()
result_path = step_evidence / "attempt-01.result.json"
result_path.write_text(json.dumps({
    "status": "ok", "summary": "applied to 1", "evidence": ["x.png"],
    "eligible_count": 1, "applications": REPORT,
}, ensure_ascii=False), encoding="utf-8")
(step_evidence / "summary.json").write_text(json.dumps({
    "status": "success", "task_label": "gig-B2", "result_path": str(result_path),
}), encoding="utf-8")

check("the report is read from the validated step result",
      ar.read_report(step_evidence / "summary.json", step_evidence) == REPORT)
check("a summary pointing outside its own evidence dir is refused",
      ar.read_report(step_evidence / "nope.json", step_evidence) == [])

foreign = work / "elsewhere.json"
foreign.write_text(json.dumps({"applications": REPORT}), encoding="utf-8")
(step_evidence / "summary-foreign.json").write_text(json.dumps({
    "status": "success", "task_label": "gig-B2", "result_path": str(foreign),
}), encoding="utf-8")
check("a result file outside the step evidence dir is not trusted",
      ar.read_report(step_evidence / "summary-foreign.json", step_evidence) == [])

(step_evidence / "summary-failed.json").write_text(json.dumps({
    "status": "failure", "task_label": "gig-B2", "result_path": str(result_path),
}), encoding="utf-8")
check("a failed step reports nothing",
      ar.read_report(step_evidence / "summary-failed.json", step_evidence) == [])

# --- dom category discovery -------------------------------------------------------
evidence = work / "evidence"
evidence.mkdir()
(evidence / "gig-72130-B2-5176621-submitted.png").write_bytes(b"x")
(evidence / "gig-72130-B2-5176621-fresh.json").write_text(json.dumps(
    {"url": "https://coconala.com/requests/5176621", "not_found": False,
     "observed": True, "title": "t"}, ensure_ascii=False), encoding="utf-8")
check("today's snapshot carries no category, so nothing is claimed from it",
      ar.dom_categories(evidence) == {}, str(ar.dom_categories(evidence)))

(evidence / "gig-72130-B2-5176778-fresh.json").write_text(json.dumps(
    {"url": "https://coconala.com/requests/5176778", "not_found": False,
     "observed": True, "title": "t", "category": "経理・財務・税務代行"},
    ensure_ascii=False), encoding="utf-8")
check("a snapshot that does carry a category is picked up",
      ar.dom_categories(evidence) == {"5176778": "経理・財務・税務代行"},
      str(ar.dom_categories(evidence)))

# --- end to end, on disk, idempotent ----------------------------------------------
ledger = work / "applied.jsonl"
ledger.write_text("", encoding="utf-8")

sys.argv = ["x", "--runner-summary", str(step_evidence / "summary.json"),
            "--step-evidence", str(step_evidence), "--ledger", str(ledger),
            "--evidence-root", str(evidence), "--pass-id", PASS_ID]
ar.main()
first = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
check("the application reaches the ledger on disk",
      len(first) == 1 and first[0].get("category") == "動画編集・映像制作", str(first))

ar.main()
second = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
check("a second run changes nothing", first == second, str(second))
check("no temp file is left behind", not list(ledger.parent.glob("*.tmp")),
      str(list(ledger.parent.glob("*.tmp"))))

# --- the schema opens the channel without gating the step -------------------------
schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
check("the step result may carry applications",
      "applications" in schema.get("properties", {}), str(list(schema.get("properties", {}))))
# The application may already be submitted in the browser by the time the model
# answers. The nullable field keeps strict generation possible, while
# application_report recovers a minimal row from fresh submit proof and the B2
# postcondition gate refuses to call a contradictory result successful.
#
# X24 (2026-07-28): that invariant was first expressed by keeping `applications` out
# of `required`, and it took the whole lane down. OpenAI's strict structured outputs
# reject a schema whose `required` omits any property, so B2 died with HTTP 400 every
# four hours -- worse than under-reporting: no applications at all. Under strict mode
# optionality is carried by a NULLABLE TYPE, not by omission.
check("a silent model can answer null for code-owned proof recovery",
      "null" in (schema["properties"]["applications"].get("type") or []),
      str(schema["properties"]["applications"].get("type")))
check("and applications is listed in required, which strict structured outputs demand",
      "applications" in schema.get("required", []), str(schema.get("required")))
check("a B2 report cannot exceed the seven-per-hour application cap",
      schema["properties"]["applications"].get("maxItems") == 7,
      str(schema["properties"]["applications"].get("maxItems")))

try:
    import jsonschema

    # X24: under strict structured outputs B2 must answer the key, so silence is
    # `applications: null` rather than an absent key. Every OTHER lane keeps the
    # shared schema, which has no applications at all -- that is what stops this
    # contract from spreading to lanes that never apply to anything.
    jsonschema.validate({"status": "ok", "summary": "s", "evidence": ["e"],
                         "eligible_count": 0,
                         "applications": None,
                         "current_b2": CURRENT_B2}, schema)
    check("a B2 step that applied to nothing still validates", True)
    shared = json.loads((ROOT / "schemas" / "gig_step_result.schema.json")
                        .read_text(encoding="utf-8"))
    jsonschema.validate({"status": "ok", "summary": "s", "evidence": ["e"]}, shared)
    check("a non-B2 lane never has to mention applications", True)
    jsonschema.validate({"status": "ok", "summary": "s", "evidence": ["e"],
                         "eligible_count": 1,
                         "applications": REPORT,
                         "current_b2": CURRENT_B2}, schema)
    check("a step result with applications validates", True)
    try:
        jsonschema.validate({"status": "ok", "summary": "s", "evidence": ["e"],
                             "eligible_count": 1,
                             "applications": [{"category": "x"}],
                             "current_b2": CURRENT_B2}, schema)
        check("an application without a request_id is rejected by the schema", False,
              "validated")
    except jsonschema.ValidationError:
        check("an application without a request_id is rejected by the schema", True)
except ImportError:
    print("SKIP  jsonschema not installed")

print()
if FAILURES:
    print(f"{len(FAILURES)} failed: {FAILURES}")
    sys.exit(1)
print("all application_report tests passed")
