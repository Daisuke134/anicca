"""Behavior tests for the deterministic B2 completion gate.

The production break this catches is pass 1785218402-40018: B2 called a request
with 29 applicants eligible even though the frozen live limit was 12, then returned
eligible_count=1 with applications=[] and the pass recorded success.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "b2_result_gate.py"


def run_gate(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        capture_output=True,
        text=True,
    )


def build_context(
    tmp_path: Path, *, applied_ids: tuple[str, ...] = (), target: int | None = None
) -> Path:
    prep = {
        "max_apply_per_pass": 7,
        **({"target_apply_per_pass": target} if target is not None else {}),
        "category_order": ["PPT/スライド"],
        "apply_skip_thresholds": {
            "max_applicants": 12,
            "min_contracted_to_skip": 1,
            "min_budget_jpy": 3000,
        },
    }
    applied = tmp_path / "applied.jsonl"
    applied.write_text(
        "".join(json.dumps({"requestId": request_id}) + "\n" for request_id in applied_ids),
        encoding="utf-8",
    )
    output = tmp_path / "b2-context.json"
    proc = run_gate(
        "build",
        "--prep-json",
        json.dumps(prep),
        "--applied",
        applied,
        "--output",
        output,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return output


def test_empty_category_order_builds_only_the_official_open_stream(tmp_path: Path):
    applied = tmp_path / "applied.jsonl"
    applied.write_text("", encoding="utf-8")
    output = tmp_path / "direct-context.json"
    prep = {
        "target_apply_per_pass": 20,
        "max_apply_per_pass": 20,
        "category_order": [],
        "apply_skip_thresholds": {"min_budget_jpy": 0},
    }

    proc = run_gate(
        "build", "--prep-json", json.dumps(prep),
        "--applied", applied, "--output", output,
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout
    context = json.loads(output.read_text(encoding="utf-8"))
    assert context["required_search_source_ids"] == ["single:new"]
    assert context["target_applications"] == 20
    assert context["max_applications"] == 20
    assert context["min_budget_jpy"] == 0


def request(
    request_id: str,
    *,
    applicants: int,
    contracted: int = 0,
    budget_max_jpy: int | None = 10000,
    accepting_applications: bool = True,
    outcome: str,
    bucket: str = "single",
) -> dict:
    return {
        "request_id": request_id,
        "bucket": bucket,
        "url": (
            f"https://coconala.com/requests/{request_id}"
            if bucket == "single"
            else f"https://coconala.com/job_matching/outsources/{request_id}"
        ),
        "applicants": applicants,
        "contracted": contracted,
        "budget_max_jpy": budget_max_jpy,
        "compensation_type": None if bucket == "single" else "hourly",
        "compensation_min_jpy": None if bucket == "single" else 3000,
        "compensation_max_jpy": None if bucket == "single" else 5000,
        "weekly_days": None if bucket == "single" else 2,
        "weekly_hours_min": None if bucket == "single" else 1,
        "weekly_hours_max": None if bucket == "single" else 10,
        "remote": None if bucket == "single" else True,
        "synchronous_interview_required": None if bucket == "single" else False,
        "human_identity_required": None if bucket == "single" else False,
        "accepting_applications": accepting_applications,
        "outcome": outcome,
        "reason": None,
    }


def application(request_id: str, *, bucket: str = "single") -> dict:
    return {
        "request_id": request_id,
        "bucket": bucket,
        "category": "システム開発・制作",
        "title": "fixture",
        "price_jpy": 8000,
        "deliver_date": "2026-07-29",
        "url": (
            f"https://coconala.com/requests/{request_id}"
            if bucket == "single"
            else f"https://coconala.com/job_matching/outsources/{request_id}"
        ),
        "compensation_type": None if bucket == "single" else "hourly",
        "weekly_days": None if bucket == "single" else 2,
        "weekly_hours_min": None if bucket == "single" else 1,
        "weekly_hours_max": None if bucket == "single" else 10,
    }


def write_result(
    tmp_path: Path,
    context: Path,
    *,
    inspected: list[dict],
    eligible_count: int | None,
    applications: list[dict] | None,
    exhaustive_search: bool = False,
) -> tuple[Path, Path]:
    evidence_dir = tmp_path / "agent-B2"
    evidence_dir.mkdir(exist_ok=True)
    marketplace_shot = evidence_dir / "requests.png"
    marketplace_shot.write_bytes(b"fresh marketplace screenshot")
    marketplace_dom = evidence_dir / "requests.json"
    marketplace_dom.write_text(
        json.dumps(
            {
                "url": "https://coconala.com/requests?sort=new",
                "not_found": False,
                "observed": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    search_sources: list[dict] = []
    if exhaustive_search:
        frozen = json.loads(context.read_text(encoding="utf-8"))
        for index, source_id in enumerate(frozen["required_search_source_ids"]):
            source_shot = evidence_dir / f"search-{index}.png"
            source_shot.write_bytes(b"fresh search screenshot")
            source_dom = evidence_dir / f"search-{index}.json"
            source_url = (
                "https://coconala.com/requests?sort=new"
                if source_id == "single:new"
                else f"https://coconala.com/requests?source={index}"
            )
            source_dom.write_text(json.dumps({
                "url": source_url, "observed": True, "not_found": False,
            }) + "\n", encoding="utf-8")
            search_sources.append({
                "source_id": source_id,
                "url": source_url,
                "screenshot_path": str(source_shot.resolve()),
                "live_dom_path": str(source_dom.resolve()),
                "inspected_count": 1,
                "has_next": False,
                "exhausted": True,
            })
    result = evidence_dir / "attempt-01.result.json"
    result.write_text(
        json.dumps(
            {
                "status": "ok",
                "summary": "fixture",
                "evidence": ["fixture evidence"],
                "eligible_count": eligible_count,
                "applications": applications,
                "current_b2": {
                    "context_path": str(context.resolve()),
                    "context_sha256": hashlib.sha256(context.read_bytes()).hexdigest(),
                    "marketplace_url": "https://coconala.com/requests?sort=new",
                    "marketplace_screenshot_path": str(marketplace_shot.resolve()),
                    "marketplace_live_dom_path": str(marketplace_dom.resolve()),
                    "inspected_requests": inspected,
                    "search_sources": search_sources,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    summary = evidence_dir / "summary.json"
    summary.write_text(
        json.dumps(
            {
                "status": "success",
                "task_label": "gig-B2",
                "result_path": str(result.resolve()),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return evidence_dir, summary


def validate(
    tmp_path: Path,
    context: Path,
    evidence_dir: Path,
    summary: Path,
    *,
    ledger_rows: list[dict] | None = None,
    min_mtime: float = 0,
    pass_id: str | None = None,
    cursor_contract: Path | None = None,
    min_new_inspections: int = 0,
    deferred_coverage_cursor: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    ledger = tmp_path / "applied-ledger.jsonl"
    ledger.write_text(
        "".join(json.dumps(row) + "\n" for row in (ledger_rows or [])),
        encoding="utf-8",
    )
    args: list[object] = [
        "validate",
        "--context",
        context,
        "--runner-summary",
        summary,
        "--evidence-dir",
        evidence_dir,
        "--evidence-root",
        tmp_path,
        "--ledger",
        ledger,
        "--min-mtime",
        min_mtime,
        "--min-new-inspections",
        min_new_inspections,
    ]
    if pass_id is not None:
        args.extend(("--pass-id", pass_id))
    if cursor_contract is not None:
        args.extend(("--cursor-contract", cursor_contract))
    if deferred_coverage_cursor is not None:
        args.extend(("--deferred-coverage-cursor", deferred_coverage_cursor))
    return run_gate(*args)


def errors(proc: subprocess.CompletedProcess[str]) -> list[str]:
    payload = json.loads((proc.stdout or proc.stderr).strip().splitlines()[-1])
    return payload["errors"]


def test_build_freezes_volume_budget_floor_sources_and_dedupe_ids(tmp_path):
    context = build_context(tmp_path, applied_ids=("91000019",))
    frozen = json.loads(context.read_text(encoding="utf-8"))
    assert frozen == {
        "version": 7,
        # Dais 2026-08-06: quantity is the strategy -- most posters never pick a winner
        # (measured: 47 of ~80 recent ineligibles were 募集終了), so the per-application
        # hit rate is structurally low and volume is the lever.
        "target_applications": 8,
        # A3 (2026-07-30): zero, and 継続 is absent from the required sweep below.
        "target_retainer_applications": 0,
        "max_applications": 8,
        "min_budget_jpy": 3000,
        "fulfillment_capabilities": {
            "asynchronous_text": True,
            "scheduled_recurring_text": True,
            "durable_follow_up_queue": True,
            "authorized_owner_profile_facts": True,
            "external_account_operations": True,
            "synchronous_voice_video_or_live_presence": False,
            "human_voice_recording": False,
            "physical_presence": False,
        },
        "active_strategy_experiment": None,
        "already_applied_request_ids": ["91000019"],
        "required_search_source_ids": [
            "single:new",
            "single:category:PPT/スライド",
            "single:keyword",
        ],
    }


def test_build_dedupes_retainer_ulid_identity(tmp_path):
    retainer_id = "01KYKDECET9WAY0CKRBCKH81RC"
    context = build_context(tmp_path, applied_ids=(retainer_id,))
    frozen = json.loads(context.read_text(encoding="utf-8"))
    assert frozen["already_applied_request_ids"] == [retainer_id]


def test_build_does_not_dedupe_unverified_proof_recovery_row(tmp_path):
    prep = {
        "max_apply_per_pass": 7,
        "category_order": ["PPT/スライド"],
        "apply_skip_thresholds": {
            "max_applicants": 12,
            "min_contracted_to_skip": 1,
            "min_budget_jpy": 3000,
        },
    }
    applied = tmp_path / "applied.jsonl"
    applied.write_text(
        "\n".join(
            [
                json.dumps({"requestId": "91000019"}),
                json.dumps({
                    "requestId": "91000026",
                    "recorded_by": "application_report_proof_recovery",
                    "submit_verified": False,
                    "applied_page_verified": False,
                }),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "b2-context.json"

    proc = run_gate(
        "build",
        "--prep-json",
        json.dumps(prep),
        "--applied",
        applied,
        "--output",
        output,
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout
    frozen = json.loads(output.read_text(encoding="utf-8"))
    assert frozen["already_applied_request_ids"] == ["91000019"]


def test_under_target_without_exhaustive_search_evidence_fails(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000054", applicants=29, outcome="ineligible")],
        eligible_count=0,
        applications=[],
    )
    proc = validate(tmp_path, context, evidence, summary)
    assert proc.returncode != 0
    assert "under_target_search_not_exhausted" in errors(proc)


def test_nullable_eligible_count_is_derived_from_inspected_rows(tmp_path):
    """A redundant nullable count must not turn valid pagination into a hard stop.

    Production pass 1785290401 inspected fifteen live details and classified every
    row ineligible, but strict output returned ``eligible_count=null``.  The rows
    already determine an exact count of zero, so the only gate error should remain
    the recoverable instruction to continue searching.
    """
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[
            request("91000069", applicants=28, outcome="ineligible"),
            request("91000068", applicants=0, outcome="ineligible"),
        ],
        eligible_count=None,
        applications=[],
    )

    proc = validate(tmp_path, context, evidence, summary)

    assert errors(proc) == ["under_target_search_not_exhausted"]


def test_under_target_cannot_relabel_one_url_as_every_required_source(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000054", applicants=29, outcome="ineligible")],
        eligible_count=0,
        applications=[],
        exhaustive_search=True,
    )
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    repeated_url = "https://coconala.com/requests?sort=new"
    for source in result["current_b2"]["search_sources"]:
        source["url"] = repeated_url
        dom_path = Path(source["live_dom_path"])
        dom = json.loads(dom_path.read_text(encoding="utf-8"))
        dom["url"] = repeated_url
        dom_path.write_text(json.dumps(dom) + "\n", encoding="utf-8")
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")

    proc = validate(tmp_path, context, evidence, summary)

    assert proc.returncode != 0
    assert "search_source_url_duplicate" in errors(proc)


def test_official_category_search_route_is_valid_exhaustion_evidence(tmp_path):
    """A real /requests/categories/<id> source must not stop B2 continuation."""
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000054", applicants=29, outcome="ineligible")],
        eligible_count=0,
        applications=[],
        exhaustive_search=True,
    )
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    category_source = next(
        source
        for source in result["current_b2"]["search_sources"]
        if source["source_id"].startswith("single:category:")
    )
    category_url = "https://coconala.com/requests/categories/646?sort=new&recruiting=true"
    category_source["url"] = category_url
    dom_path = Path(category_source["live_dom_path"])
    dom = json.loads(dom_path.read_text(encoding="utf-8"))
    dom["url"] = category_url
    dom_path.write_text(json.dumps(dom) + "\n", encoding="utf-8")
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")

    proc = validate(tmp_path, context, evidence, summary)

    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_official_category_route_is_valid_top_level_marketplace_evidence(tmp_path):
    """The live source shown at return time may be an official category page.

    Production pass 1785308400 inspected a valid category source last and bound
    both top-level screenshot/DOM fields to it.  Search-source validation
    accepted that exact route, while the older top-level validator rejected it
    and stopped a safe under-target continuation.
    """
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000026", applicants=16, outcome="ineligible")],
        eligible_count=0,
        applications=[],
        exhaustive_search=True,
    )
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    category_source = next(
        source
        for source in result["current_b2"]["search_sources"]
        if source["source_id"].startswith("single:category:")
    )
    category_url = "https://coconala.com/requests/categories/279?sort=new"
    category_source["url"] = category_url
    dom_path = Path(category_source["live_dom_path"])
    dom = json.loads(dom_path.read_text(encoding="utf-8"))
    dom["url"] = category_url
    dom_path.write_text(json.dumps(dom) + "\n", encoding="utf-8")
    result["current_b2"].update({
        "marketplace_url": category_url,
        "marketplace_screenshot_path": category_source["screenshot_path"],
        "marketplace_live_dom_path": category_source["live_dom_path"],
    })
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")

    proc = validate(tmp_path, context, evidence, summary)

    assert proc.returncode == 0, proc.stderr or proc.stdout


def _mark_source_not_observed(result_path: Path, source_id: str) -> None:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    source = next(
        row
        for row in result["current_b2"]["search_sources"]
        if row["source_id"] == source_id
    )
    dom_path = Path(source["live_dom_path"])
    dom = json.loads(dom_path.read_text(encoding="utf-8"))
    dom["observed"] = False
    dom_path.write_text(json.dumps(dom) + "\n", encoding="utf-8")


def test_deferred_coverage_cursor_excuses_the_source_it_defers(tmp_path):
    """A source the durable coverage cursor has not reached yet is not a defect.

    b2_search_objective.py's cursor walks required_search_source_ids in order
    across hourly wakes; a source at or after the cursor's position has
    legitimately not been swept this wake, so an unobserved snapshot for it
    must not block the pass the way a genuinely missing observation does.
    """
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000054", applicants=29, outcome="ineligible")],
        eligible_count=0,
        applications=[],
        exhaustive_search=True,
    )
    result_path = evidence / "attempt-01.result.json"
    _mark_source_not_observed(result_path, "single:keyword")

    proc_without_cursor = validate(tmp_path, context, evidence, summary)
    assert proc_without_cursor.returncode != 0
    assert "search_source_not_observed:single:keyword" in errors(proc_without_cursor)

    cursor = tmp_path / "b2-deferred-coverage-cursor.json"
    cursor.write_text(
        json.dumps(
            {
                "source_id": "single:keyword",
                "previous_url": "",
                "next_url": "https://coconala.com/requests?keyword=AI&recruiting=true",
                "reason": "inspect_missing_source_by_keyword",
            }
        ),
        encoding="utf-8",
    )
    proc_with_cursor = validate(
        tmp_path, context, evidence, summary, deferred_coverage_cursor=cursor
    )
    assert "search_source_not_observed:single:keyword" not in errors(proc_with_cursor)
    assert proc_with_cursor.returncode == 0, proc_with_cursor.stderr or proc_with_cursor.stdout


def test_deferred_coverage_cursor_does_not_excuse_a_source_before_it(tmp_path):
    """Deferral only covers the cursor's position onward, not earlier sources.

    A source ahead of the cursor in required_search_source_ids order was
    supposed to be swept before the cursor could advance past it, so an
    unobserved snapshot for it stays a real defect even with a cursor present.
    """
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000054", applicants=29, outcome="ineligible")],
        eligible_count=0,
        applications=[],
        exhaustive_search=True,
    )
    result_path = evidence / "attempt-01.result.json"
    _mark_source_not_observed(result_path, "single:new")

    cursor = tmp_path / "b2-deferred-coverage-cursor.json"
    cursor.write_text(
        json.dumps(
            {
                "source_id": "single:keyword",
                "previous_url": "",
                "next_url": "https://coconala.com/requests?keyword=AI&recruiting=true",
                "reason": "inspect_missing_source_by_keyword",
            }
        ),
        encoding="utf-8",
    )
    proc = validate(
        tmp_path, context, evidence, summary, deferred_coverage_cursor=cursor
    )
    assert proc.returncode != 0
    assert "search_source_not_observed:single:new" in errors(proc)


def test_missing_deferred_coverage_cursor_stays_strict(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000054", applicants=29, outcome="ineligible")],
        eligible_count=0,
        applications=[],
        exhaustive_search=True,
    )
    result_path = evidence / "attempt-01.result.json"
    _mark_source_not_observed(result_path, "single:keyword")

    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        deferred_coverage_cursor=tmp_path / "does-not-exist.json",
    )
    assert proc.returncode != 0
    assert "search_source_not_observed:single:keyword" in errors(proc)


def test_unparseable_deferred_coverage_cursor_stays_strict(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000054", applicants=29, outcome="ineligible")],
        eligible_count=0,
        applications=[],
        exhaustive_search=True,
    )
    result_path = evidence / "attempt-01.result.json"
    _mark_source_not_observed(result_path, "single:keyword")

    cursor = tmp_path / "b2-deferred-coverage-cursor.json"
    cursor.write_text("{not json", encoding="utf-8")

    proc = validate(
        tmp_path, context, evidence, summary, deferred_coverage_cursor=cursor
    )
    assert proc.returncode != 0
    assert "search_source_not_observed:single:keyword" in errors(proc)


def test_under_target_with_recoverable_search_error_remains_continuable(tmp_path):
    """One malformed search source must trigger more search, not end the pass."""
    context = build_context(tmp_path)
    gate_result = tmp_path / "gate-result.json"
    gate_result.write_text(json.dumps({
        "ok": False,
        "errors": [
            "search_source_url_invalid:single:category:CRMマーケティング・ツール",
            "under_target_inspection_quantity_too_low:actual=3:minimum=12",
            "under_target_search_not_exhausted",
        ],
    }) + "\n", encoding="utf-8")
    ledger = tmp_path / "applied-ledger.jsonl"
    ledger.write_text("", encoding="utf-8")

    proc = run_gate(
        "continuable",
        "--gate-result",
        gate_result,
        "--ledger",
        ledger,
        "--context",
        context,
        "--pass-id",
        "pass-1",
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert json.loads(proc.stdout)["continuable"] is True


def test_under_target_with_top_level_marketplace_binding_error_remains_continuable(
    tmp_path,
):
    """Presentation metadata must not discard three verified applications.

    Production pass 1785332612 verified three submissions and returned valid
    paginated search-source evidence for page 5.  The model bound the redundant
    top-level marketplace fields to a category snapshot whose saved DOM URL did
    not match.  That diagnostic is useful, but it must send the same pass to the
    code-owned next cursor instead of ending B2 below its four-application target.
    """
    context = build_context(tmp_path, target=4)
    gate_result = tmp_path / "gate-result.json"
    gate_result.write_text(json.dumps({
        "ok": False,
        "errors": [
            "marketplace_url_invalid",
            "marketplace_live_dom_url_mismatch",
            "under_target_search_not_exhausted",
        ],
    }) + "\n", encoding="utf-8")
    ledger = tmp_path / "applied-ledger.jsonl"
    ledger.write_text("".join(
        json.dumps({
            "pass_id": "pass-1",
            "requestId": request_id,
            "bucket": "retainer" if not request_id.isdigit() else "single",
            "submit_verified": True,
            "applied_page_verified": True,
        }) + "\n"
        for request_id in (
            "91000052",
            "91000041",
            "01KYHAKS8W0X42WM9T63MHA4J3",
        )
    ), encoding="utf-8")

    proc = run_gate(
        "continuable",
        "--gate-result",
        gate_result,
        "--ledger",
        ledger,
        "--context",
        context,
        "--pass-id",
        "pass-1",
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["continuable"] is True
    assert payload["verified_count"] == 3
    assert payload["target"] == 4


def test_under_target_unsubmitted_eligible_candidate_remains_continuable(tmp_path):
    """A form-level blocker must send B2 back to search, not terminate the pass.

    Production pass 1785321031 found an otherwise eligible retainer, but its
    canonical form did not expose the controls required by the submit helper.
    The gate correctly observed zero new submits, then incorrectly made that
    cardinality diagnostic non-retryable while the pass still owned only three.
    """
    context = build_context(tmp_path)
    gate_result = tmp_path / "gate-result.json"
    gate_result.write_text(json.dumps({
        "ok": False,
        "errors": [
            "application_count_mismatch:expected=1:actual=0",
            "under_target_search_not_exhausted",
        ],
    }) + "\n", encoding="utf-8")
    ledger = tmp_path / "applied-ledger.jsonl"
    ledger.write_text("".join(
        json.dumps({
            "pass_id": "pass-1",
            "requestId": request_id,
            "submit_verified": True,
            "applied_page_verified": True,
        }) + "\n"
        for request_id in ("91000067", "91000047", "91000039")
    ), encoding="utf-8")

    proc = run_gate(
        "continuable",
        "--gate-result",
        gate_result,
        "--ledger",
        ledger,
        "--context",
        context,
        "--pass-id",
        "pass-1",
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["continuable"] is True
    assert payload["verified_count"] == 3


def test_under_target_model_dedupe_miss_remains_continuable(tmp_path):
    """Code-owned dedupe must skip the known ID and keep searching this pass."""
    context = build_context(tmp_path)
    gate_result = tmp_path / "gate-result.json"
    gate_result.write_text(json.dumps({
        "ok": False,
        "errors": [
            "eligible_already_applied:91000064",
            "under_target_search_not_exhausted",
        ],
    }) + "\n", encoding="utf-8")
    ledger = tmp_path / "applied-ledger.jsonl"
    ledger.write_text("", encoding="utf-8")

    proc = run_gate(
        "continuable",
        "--gate-result",
        gate_result,
        "--ledger",
        ledger,
        "--context",
        context,
        "--pass-id",
        "pass-1",
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert json.loads(proc.stdout)["continuable"] is True


def test_under_target_repeated_ineligible_observation_remains_continuable(tmp_path):
    """Safe cumulative duplicate rows must not terminate pagination."""
    context = build_context(tmp_path)
    gate_result = tmp_path / "gate-result.json"
    gate_result.write_text(json.dumps({
        "ok": False,
        "errors": [
            "inspected_request_duplicate:91000028",
            "under_target_search_not_exhausted",
        ],
    }) + "\n", encoding="utf-8")
    ledger = tmp_path / "applied-ledger.jsonl"
    ledger.write_text("", encoding="utf-8")

    proc = run_gate(
        "continuable",
        "--gate-result",
        gate_result,
        "--ledger",
        ledger,
        "--context",
        context,
        "--pass-id",
        "pass-1",
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert json.loads(proc.stdout)["continuable"] is True


def test_under_target_with_submit_proof_error_is_not_continuable(tmp_path):
    """Continuation may absorb search evidence faults, never missing submit proof."""
    context = build_context(tmp_path)
    gate_result = tmp_path / "gate-result.json"
    gate_result.write_text(json.dumps({
        "ok": False,
        "errors": [
            "application_submit_evidence_missing:91000042",
            "under_target_search_not_exhausted",
        ],
    }) + "\n", encoding="utf-8")
    ledger = tmp_path / "applied-ledger.jsonl"
    ledger.write_text("", encoding="utf-8")

    proc = run_gate(
        "continuable",
        "--gate-result",
        gate_result,
        "--ledger",
        ledger,
        "--context",
        context,
        "--pass-id",
        "pass-1",
    )

    assert proc.returncode == 1
    assert json.loads(proc.stdout)["continuable"] is False


def test_unchanged_cursor_failure_remains_retryable_within_the_same_pass(tmp_path):
    context = build_context(tmp_path)
    gate_result = tmp_path / "gate-result.json"
    gate_result.write_text(json.dumps({
        "ok": False,
        "errors": [
            "continuation_cursor_not_advanced:single:new",
            "under_target_search_not_exhausted",
        ],
    }) + "\n", encoding="utf-8")
    ledger = tmp_path / "applied-ledger.jsonl"
    ledger.write_text("", encoding="utf-8")

    proc = run_gate(
        "continuable",
        "--gate-result",
        gate_result,
        "--ledger",
        ledger,
        "--context",
        context,
        "--pass-id",
        "pass-1",
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert json.loads(proc.stdout)["continuable"] is True


def test_four_single_applications_no_longer_buy_a_retainer_continuation(tmp_path):
    """A3 (2026-07-30): the single target now DOES terminate the wake.

    Until A3 this was the opposite rule -- production pass 1785273897 submitted
    four verified single jobs and was granted an extra model call to finish a
    retainer sweep. With 継続 applications refused in code, that extra call buys
    an outcome that cannot happen, so the wake ends on its single evidence.
    """
    context = build_context(tmp_path)
    gate_result = tmp_path / "gate-result.json"
    gate_result.write_text(json.dumps({
        "ok": False,
        "errors": ["retainer_search_not_exhausted"],
    }) + "\n", encoding="utf-8")
    ledger = tmp_path / "applied-ledger.jsonl"
    ledger.write_text("".join(
        json.dumps({
            "pass_id": "pass-1",
            "requestId": request_id,
            "bucket": "single",
            "submit_verified": True,
            "applied_page_verified": True,
        }) + "\n"
        for request_id in ("91000043", "91000044", "91000045", "91000046")
    ), encoding="utf-8")

    proc = run_gate(
        "continuable",
        "--gate-result",
        gate_result,
        "--ledger",
        ledger,
        "--context",
        context,
        "--pass-id",
        "pass-1",
    )

    assert proc.returncode == 1, proc.stdout or proc.stderr


def test_a_pre_a3_retainer_row_in_the_ledger_does_not_reopen_continuation(tmp_path):
    """Ledgers still hold retainer rows submitted before A3 (2026-07-30).

    Reading one back must not resurrect the retainer continuation branch -- the
    wake ends on its single evidence exactly as it would with no retainer row at
    all. This is the A4 boundary in the gate: old retainer work stays readable,
    it just cannot ask for another model call.
    """
    context = build_context(tmp_path)
    gate_result = tmp_path / "gate-result.json"
    gate_result.write_text(json.dumps({
        "ok": False,
        "errors": ["retainer_search_not_exhausted"],
    }) + "\n", encoding="utf-8")
    ledger = tmp_path / "applied-ledger.jsonl"
    rows = [
        {
            "pass_id": "pass-1",
            "requestId": request_id,
            "bucket": "single",
            "submit_verified": True,
            "applied_page_verified": True,
        }
        for request_id in ("91000043", "91000044", "91000045", "91000046")
    ]
    rows.append({
        "pass_id": "pass-1",
        "requestId": "01KYKDECET9WAY0CKRBCKH81RC",
        "bucket": "retainer",
        "submit_verified": True,
        "applied_page_verified": True,
    })
    ledger.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )

    proc = run_gate(
        "continuable",
        "--gate-result",
        gate_result,
        "--ledger",
        ledger,
        "--context",
        context,
        "--pass-id",
        "pass-1",
    )

    assert proc.returncode == 1
    assert json.loads(proc.stdout)["continuable"] is False


def test_first_incomplete_attempt_is_sent_back_to_newest_exactly_once(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[],
        eligible_count=0,
        applications=[],
    )
    contract = tmp_path / "b2-next-cursor.json"

    proc = run_gate(
        "next-cursor",
        "--runner-summary",
        summary,
        "--context",
        context,
        "--output",
        contract,
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert json.loads(contract.read_text(encoding="utf-8")) == {
        "source_id": "single:new",
        "previous_url": "",
        "next_url": "https://coconala.com/requests?sort=new&recruiting=true",
        "reason": "inspect_missing_source",
    }


def test_parent_computes_the_exact_next_page_for_a_continuation(tmp_path):
    """The model must receive one code-owned next URL, not choose where to resume."""
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000054", applicants=29, outcome="ineligible")],
        eligible_count=0,
        applications=[],
    )
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["current_b2"]["search_sources"] = [{
        "source_id": "single:new",
        "url": "https://coconala.com/requests?sort=new",
        "screenshot_path": str((evidence / "requests.png").resolve()),
        "live_dom_path": str((evidence / "requests.json").resolve()),
        "inspected_count": 40,
        "has_next": True,
        "exhausted": False,
    }]
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    contract = tmp_path / "b2-next-cursor.json"

    proc = run_gate(
        "next-cursor",
        "--runner-summary",
        summary,
        "--context",
        context,
        "--output",
        contract,
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout
    payload = json.loads(contract.read_text(encoding="utf-8"))
    assert payload == {
        "source_id": "single:new",
        "previous_url": "https://coconala.com/requests?sort=new",
        "next_url": "https://coconala.com/requests?sort=new&page=2",
        "reason": "next_page",
        "prior_inspected_request_ids": ["91000054"],
    }


def test_production_incident_recovers_the_first_missing_required_category(tmp_path):
    """1785650535 had exhausted returned rows but many frozen categories remained."""
    context = build_context(tmp_path)
    frozen = json.loads(context.read_text(encoding="utf-8"))
    frozen["required_search_source_ids"] = [
        "single:new",
        "single:category:プログラミング・ソフト開発",
        "single:category:その他(動画編集・映像制作)",
        "single:category:AI生成画像の加工・レタッチ",
        "single:keyword",
    ]
    context.write_text(json.dumps(frozen) + "\n", encoding="utf-8")
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[
            request(str(91000077 + index), applicants=index, outcome="ineligible")
            for index in range(4)
        ],
        eligible_count=0,
        applications=[],
    )
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["current_b2"]["search_sources"] = [
        {
            "source_id": source_id,
            "url": url,
            "screenshot_path": str((evidence / "requests.png").resolve()),
            "live_dom_path": str((evidence / "requests.json").resolve()),
            "inspected_count": inspected_count,
            "has_next": False,
            "exhausted": True,
        }
        for source_id, url, inspected_count in (
            ("single:new", "https://coconala.com/requests?sort=new&page=75", 60),
            (
                "single:category:プログラミング・ソフト開発",
                "https://coconala.com/requests/categories/231?recruiting=true",
                3,
            ),
            (
                "single:category:その他(動画編集・映像制作)",
                "https://coconala.com/requests/categories/218?recruiting=true",
                1,
            ),
        )
    ]
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    contract = tmp_path / "b2-next-cursor.json"

    proc = run_gate(
        "next-cursor",
        "--runner-summary",
        summary,
        "--context",
        context,
        "--output",
        contract,
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert json.loads(contract.read_text(encoding="utf-8")) == {
        "source_id": "single:category:AI生成画像の加工・レタッチ",
        "previous_url": "",
        "next_url": "https://coconala.com/requests?" + urlencode({
            "keyword": "AI生成画像の加工・レタッチ",
            "recruiting": "true",
        }),
        "reason": "inspect_missing_source_by_keyword",
        "prior_inspected_request_ids": [
            "91000077",
            "91000078",
            "91000079",
            "91000080",
        ],
    }


def test_the_continuation_cursor_never_points_at_the_retainer_bucket(tmp_path):
    """A3 (2026-07-30): 継続 is not a place the cursor may send the next wake.

    This inverts the pre-A3 rule, which deliberately steered continuation onto
    retainer:new once four singles were verified so the lane could not be trapped
    on infinite single pagination. Now that retainer submits are refused in code,
    steering there would spend the continuation on a dead end, so the cursor stays
    inside the single program even when the model volunteered a retainer sweep.
    """
    context = build_context(tmp_path)
    single_ids = ("91000043", "91000044", "91000045", "91000046")
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[
            *[
                request(request_id, applicants=1, outcome="eligible")
                for request_id in single_ids
            ],
            request(
                "01KYNMYGYT3H04VS64P0R27Z21",
                applicants=0,
                outcome="ineligible",
                bucket="retainer",
            ),
        ],
        eligible_count=4,
        applications=[application(request_id) for request_id in single_ids],
    )
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["current_b2"]["search_sources"] = [
        {
            "source_id": "single:new",
            "url": "https://coconala.com/requests?sort=new&page=8",
            "screenshot_path": str((evidence / "requests.png").resolve()),
            "live_dom_path": str((evidence / "requests.json").resolve()),
            "inspected_count": 153,
            "has_next": True,
            "exhausted": False,
        },
        {
            "source_id": "retainer:new",
            "url": "https://coconala.com/job_matching/outsources",
            "screenshot_path": str((evidence / "requests.png").resolve()),
            "live_dom_path": str((evidence / "requests.json").resolve()),
            "inspected_count": 56,
            "has_next": True,
            "exhausted": False,
        },
    ]
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    contract = tmp_path / "b2-next-cursor.json"

    proc = run_gate(
        "next-cursor",
        "--runner-summary",
        summary,
        "--context",
        context,
        "--output",
        contract,
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout
    payload = json.loads(contract.read_text(encoding="utf-8"))
    assert payload["source_id"] == "single:new"
    assert "job_matching/outsources" not in payload["next_url"]
    assert payload["reason"] == "next_page"


def test_exhausted_zero_result_sources_do_not_retry_the_same_page(tmp_path):
    """A final empty page is observed evidence of exhaustion, not work to retry."""
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[],
        eligible_count=0,
        applications=[],
        exhaustive_search=True,
    )
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    for source in result["current_b2"]["search_sources"]:
        source["inspected_count"] = 0
        if source["source_id"] == "single:new":
            source["url"] = "https://coconala.com/requests?page=95&sort=new"
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    contract = tmp_path / "b2-next-cursor.json"

    proc = run_gate(
        "next-cursor",
        "--runner-summary",
        summary,
        "--context",
        context,
        "--output",
        contract,
    )

    assert proc.returncode != 0
    assert "continuation_cursor_unavailable" in proc.stderr
    assert not contract.exists()


def test_under_target_attempt_must_inspect_twelve_new_live_details(tmp_path):
    """Production pass 1785284583 returned after three details despite 40 live cards."""
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[
            request(str(91000066 + index), applicants=index, outcome="ineligible")
            for index in range(3)
        ],
        eligible_count=0,
        applications=[],
    )

    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        min_new_inspections=12,
    )

    assert "under_target_inspection_quantity_too_low:actual=3:minimum=12" in errors(proc)


def test_continuation_quantity_counts_only_new_request_details(tmp_path):
    context = build_context(tmp_path)
    prior_ids = [str(91000066 + index) for index in range(12)]
    current_ids = prior_ids + ["91000201", "91000202", "91000203"]
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[
            request(request_id, applicants=1, outcome="ineligible")
            for request_id in current_ids
        ],
        eligible_count=0,
        applications=[],
    )
    cursor = tmp_path / "b2-next-cursor.json"
    cursor.write_text(json.dumps({
        "source_id": "single:new",
        "previous_url": "https://coconala.com/requests?sort=new",
        "next_url": "https://coconala.com/requests?sort=new",
        "reason": "inspect_current_page",
        "prior_inspected_request_ids": prior_ids,
    }) + "\n", encoding="utf-8")

    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        cursor_contract=cursor,
        min_new_inspections=12,
    )

    assert "under_target_inspection_quantity_too_low:actual=3:minimum=12" in errors(proc)


def test_continuation_gate_rejects_the_same_search_cursor(tmp_path):
    """Production pass 1785265474 revisited page 1 instead of advancing."""
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000054", applicants=29, outcome="ineligible")],
        eligible_count=0,
        applications=[],
    )
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["current_b2"]["search_sources"] = [{
        "source_id": "single:new",
        "url": "https://coconala.com/requests?sort=new",
        "screenshot_path": str((evidence / "requests.png").resolve()),
        "live_dom_path": str((evidence / "requests.json").resolve()),
        "inspected_count": 40,
        "has_next": True,
        "exhausted": False,
    }]
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    contract = tmp_path / "b2-next-cursor.json"
    contract.write_text(json.dumps({
        "source_id": "single:new",
        "previous_url": "https://coconala.com/requests?sort=new",
        "next_url": "https://coconala.com/requests?sort=new&page=2",
        "reason": "next_page",
    }) + "\n", encoding="utf-8")

    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        cursor_contract=contract,
    )

    assert proc.returncode != 0
    assert "continuation_cursor_not_advanced:single:new" in errors(proc)


def test_continuation_accepts_monotonic_pages_for_the_same_search_source(tmp_path):
    """Cumulative page evidence may repeat a source id when its URL advances.

    Production pass 1785321031 carried ``single:new`` page 2 and added page 6.
    Treating the second row as a duplicate discarded the current cursor and
    converted a safe under-target continuation into a terminal failure.
    """
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000029", applicants=2, outcome="ineligible")],
        eligible_count=0,
        applications=[],
    )
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    sources = []
    for page in (2, 6):
        shot = evidence / f"single-new-page{page}.png"
        shot.write_bytes(b"fresh marketplace screenshot")
        dom = evidence / f"single-new-page{page}.json"
        url = f"https://coconala.com/requests?sort=new&page={page}"
        dom.write_text(json.dumps({
            "url": url,
            "observed": True,
            "not_found": False,
        }) + "\n", encoding="utf-8")
        sources.append({
            "source_id": "single:new",
            "url": url,
            "screenshot_path": str(shot.resolve()),
            "live_dom_path": str(dom.resolve()),
            "inspected_count": page * 40,
            "has_next": True,
            "exhausted": False,
        })
    result["current_b2"]["search_sources"] = sources
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    cursor = tmp_path / "b2-next-cursor.json"
    cursor.write_text(json.dumps({
        "source_id": "single:new",
        "previous_url": "https://coconala.com/requests?sort=new&page=5",
        "next_url": "https://coconala.com/requests?sort=new&page=6",
        "reason": "next_page",
    }) + "\n", encoding="utf-8")

    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        cursor_contract=cursor,
    )

    observed = errors(proc)
    assert "search_source_duplicate:single:new" not in observed
    assert "continuation_cursor_not_advanced:single:new" not in observed
    assert observed == ["under_target_search_not_exhausted"]


def test_continuation_accepts_coconala_query_reordering(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000029", applicants=2, outcome="ineligible")],
        eligible_count=0,
        applications=[],
        exhaustive_search=True,
    )
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    source = next(
        row for row in result["current_b2"]["search_sources"]
        if row["source_id"] == "single:new"
    )
    landed_url = "https://coconala.com/requests?recruiting=true&sort=new"
    source["url"] = landed_url
    dom_path = Path(source["live_dom_path"])
    dom = json.loads(dom_path.read_text(encoding="utf-8"))
    dom["url"] = landed_url
    dom_path.write_text(json.dumps(dom) + "\n", encoding="utf-8")
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    cursor = tmp_path / "b2-refresh-cursor.json"
    cursor.write_text(json.dumps({
        "source_id": "single:new",
        "previous_url": "",
        "next_url": "https://coconala.com/requests?sort=new&recruiting=true",
        "reason": "newest_first_each_wake",
    }) + "\n", encoding="utf-8")

    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        cursor_contract=cursor,
    )

    assert "continuation_cursor_not_advanced:single:new" not in errors(proc)
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_continuation_accepts_same_filtered_source_after_multi_page_advance(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000029", applicants=2, outcome="ineligible")],
        eligible_count=0,
        applications=[],
        exhaustive_search=True,
    )
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    source = next(
        row for row in result["current_b2"]["search_sources"]
        if row["source_id"] == "single:new"
    )
    landed_url = "https://coconala.com/requests?page=8&recruiting=true&sort=new"
    source["url"] = landed_url
    source["has_next"] = False
    source["exhausted"] = True
    dom_path = Path(source["live_dom_path"])
    dom = json.loads(dom_path.read_text(encoding="utf-8"))
    dom["url"] = landed_url
    dom["next_url"] = None
    dom_path.write_text(json.dumps(dom) + "\n", encoding="utf-8")
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    cursor = tmp_path / "b2-refresh-cursor.json"
    cursor.write_text(json.dumps({
        "source_id": "single:new",
        "previous_url": "",
        "next_url": "https://coconala.com/requests?sort=new&recruiting=true",
        "reason": "newest_first_each_wake",
    }) + "\n", encoding="utf-8")

    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        cursor_contract=cursor,
    )

    assert errors(proc) == []
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_direct_duplicate_fence_does_not_demand_an_application(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000029", applicants=2, outcome="eligible")],
        eligible_count=1,
        applications=[],
        exhaustive_search=True,
    )
    (evidence / "parent-commit.json").write_text(json.dumps({
        "snapshot_sha256": "a" * 64,
        "planner_missing_request_ids": [],
        "results": [{
            "request_id": "91000029",
            "status": "prepared_unconfirmed",
            "business_class": "duplicate_fenced",
        }],
    }) + "\n", encoding="utf-8")

    proc = validate(tmp_path, context, evidence, summary)

    assert "application_count_mismatch:expected=1:actual=0" not in errors(proc)
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_competition_counts_do_not_close_an_open_application(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[
            request(
                "91000054",
                applicants=62,
                contracted=1,
                accepting_applications=True,
                outcome="eligible",
            )
        ],
        eligible_count=1,
        applications=[],
    )
    proc = validate(tmp_path, context, evidence, summary)
    assert proc.returncode != 0
    assert "eligible_max_applicants_exceeded:91000054" not in errors(proc)
    assert "eligible_contracted_threshold_reached:91000054" not in errors(proc)
    assert "application_count_mismatch:expected=1:actual=0" in errors(proc)


def test_open_request_with_quote_requested_budget_can_be_eligible(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[
            request(
                "91000054",
                applicants=3,
                budget_max_jpy=None,
                accepting_applications=True,
                outcome="eligible",
            )
        ],
        eligible_count=1,
        applications=[],
    )
    proc = validate(tmp_path, context, evidence, summary)
    assert proc.returncode != 0
    assert "eligible_budget_missing:91000054" not in errors(proc)
    assert "application_count_mismatch:expected=1:actual=0" in errors(proc)


def test_closed_request_cannot_be_reported_eligible(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[
            request(
                "91000054",
                applicants=3,
                accepting_applications=False,
                outcome="eligible",
            )
        ],
        eligible_count=1,
        applications=[],
    )
    proc = validate(tmp_path, context, evidence, summary)
    assert proc.returncode != 0
    assert "eligible_marketplace_closed:91000054" in errors(proc)


def test_zero_eligible_with_an_explicit_ineligible_observation_passes(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000054", applicants=29, outcome="ineligible")],
        eligible_count=0,
        applications=[],
        exhaustive_search=True,
    )
    proc = validate(tmp_path, context, evidence, summary)
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_one_eligible_application_with_exhaustion_and_readback_passes(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000042", applicants=1, outcome="eligible")],
        eligible_count=1,
        applications=[application("91000042")],
        exhaustive_search=True,
    )
    proof = tmp_path / "gig-fixture-B2-91000042-submitted.png"
    proof.write_bytes(b"fresh submitted proof")
    readback = evidence / "code-applied-readback.json"
    readback.write_text(json.dumps({
        "source": "code_owned_cdp_readback",
        "url": "https://coconala.com/mypage/job_matching/applied/offers",
        "observed": True,
        "not_found": False,
        "request_ids": ["91000042"],
    }) + "\n", encoding="utf-8")
    started = min(proof.stat().st_mtime, readback.stat().st_mtime) - 0.1
    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        ledger_rows=[{
            "requestId": "91000042",
            "status": "applied",
            "submit_verified": True,
            "applied_page_verified": True,
        }],
        min_mtime=started,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_canonical_readback_closes_submit_intent_when_helper_ack_is_lost(tmp_path):
    request_id = "91000021"
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request(request_id, applicants=1, outcome="eligible")],
        eligible_count=1,
        applications=[],
        exhaustive_search=True,
    )
    intent = evidence / f"gig-fixture-B2-{request_id}-submitted.intent.json"
    intent.write_text(json.dumps({
        "request_id": request_id,
        "bucket": "single",
        "url": f"https://coconala.com/requests/{request_id}",
        "title": "AIツール活用のWebサイト制作",
        "state": "prepared",
    }) + "\n", encoding="utf-8")
    readback = evidence / "code-applied-readback.json"
    readback.write_text(json.dumps({
        "source": "code_owned_cdp_readback",
        "url": "https://coconala.com/mypage/job_matching/applied/offers",
        "observed": True,
        "not_found": False,
        "request_ids": [request_id],
    }) + "\n", encoding="utf-8")
    started = min(intent.stat().st_mtime, readback.stat().st_mtime) - 0.1

    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        ledger_rows=[{
            "pass_id": "pass-1",
            "requestId": request_id,
            "bucket": "single",
            "status": "applied",
            "recorded_by": "application_report_intent_recovery",
            "submit_verified": True,
            "applied_page_verified": True,
        }],
        min_mtime=started,
        pass_id="pass-1",
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout


def _prepared_intent_only_pass(tmp_path: Path, request_id: str, absent: bool):
    """A pre-click intent with no submit proof, plus a code-owned readback."""
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request(request_id, applicants=1, outcome="eligible")],
        eligible_count=1,
        applications=[],
        exhaustive_search=True,
    )
    intent = evidence / f"gig-fixture-B2-{request_id}-submitted.intent.json"
    intent.write_text(json.dumps({
        "request_id": request_id,
        "bucket": "single",
        "url": f"https://coconala.com/requests/{request_id}",
        "title": None,
        "state": "prepared",
    }) + "\n", encoding="utf-8")
    payload = {
        "source": "code_owned_cdp_readback",
        "url": "https://coconala.com/mypage/job_matching/applied/offers",
        "urls": ["https://coconala.com/mypage/job_matching/applied/offers"],
        "observed": True,
        "not_found": False,
        "request_ids": ["91000019"],
    }
    if absent:
        payload["applied_page_absent_request_ids"] = [request_id]
    readback = evidence / "code-applied-readback.json"
    readback.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    started = min(intent.stat().st_mtime, readback.stat().st_mtime) - 0.1
    return validate(
        tmp_path,
        context,
        evidence,
        summary,
        ledger_rows=[{
            "pass_id": "pass-1",
            "requestId": request_id,
            "bucket": "single",
            "status": "reconcile_pending",
            "recorded_by": "application_report_intent_recovery",
            "submit_verified": False,
            "applied_page_verified": False,
        }],
        min_mtime=started,
        pass_id="pass-1",
    )


def test_a_candidate_stamped_absent_is_still_neither_deduped_nor_counted(tmp_path):
    """No duplicate-submit path: absence stamps change no decision, only the record.

    `already_applied_request_ids` is what stops a re-application; a row that still
    fails the verified test must stay out of it (or a never-submitted request would
    be blacklisted forever) and equally must never be counted as an application.
    """
    applied = tmp_path / "applied.jsonl"
    row = {
        "pass_id": "p1",
        "requestId": "91000025",
        "status": "reconcile_pending",
        "recorded_by": "application_report_intent_recovery",
        "submit_verified": False,
        "applied_page_verified": False,
        "applied_page_absent_at": 1785421900,
        "applied_page_absent_checks": 2,
    }
    applied.write_text(json.dumps(row) + "\n", encoding="utf-8")
    output = tmp_path / "b2-context.json"
    proc = run_gate(
        "build",
        "--prep-json",
        json.dumps({
            "max_apply_per_pass": 7,
            "category_order": ["PPT/スライド"],
            "apply_skip_thresholds": {
                "max_applicants": 12,
                "min_contracted_to_skip": 1,
                "min_budget_jpy": 3000,
            },
        }),
        "--applied",
        applied,
        "--output",
        output,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    frozen = json.loads(output.read_text(encoding="utf-8"))
    assert frozen["already_applied_request_ids"] == []


def test_a_prepared_intent_proved_absent_by_the_readback_is_not_an_unreported_submit(tmp_path):
    """A pre-click marker whose click provably never landed is not a hidden submit.

    cdp_nav_snapshot writes state="prepared" immediately BEFORE the irreversible
    click, so it only ever means "outcome unknown".  Once the code-owned readback
    has independently proved the identity is absent from the canonical applied
    page, calling it unreported submit evidence is a permanent, unresolvable RED.
    """
    proc = _prepared_intent_only_pass(tmp_path, "91000042", absent=True)
    assert "unreported_submit_evidence:91000042" not in errors(proc)


def test_a_prepared_intent_not_proved_absent_is_still_an_unreported_submit(tmp_path):
    """Without a readback verdict the ambiguity stands and the gate still fails."""
    proc = _prepared_intent_only_pass(tmp_path, "91000042", absent=False)
    assert "unreported_submit_evidence:91000042" in errors(proc)


def test_a_pre_a3_retainer_submission_still_counts_in_its_own_ledger(tmp_path):
    """A4 boundary: a retainer application that WAS submitted stays accounted for.

    Named for what it now proves. Before A3 (2026-07-30) this pinned the opposite
    intent -- that the hourly target REQUIRED one verified retainer. New retainer
    applications are refused in code now, but a wake replaying a retainer identity
    that was already submitted must still close cleanly rather than treat proven
    history as an unreported submission.
    """
    context = build_context(tmp_path, target=4)
    single_ids = ("91000043", "91000044", "91000045")
    retainer_id = "01KYKDECET9WAY0CKRBCKH81RC"
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[
            *[
                request(request_id, applicants=1, outcome="eligible")
                for request_id in single_ids
            ],
            request(
                retainer_id,
                applicants=0,
                budget_max_jpy=1500,
                outcome="eligible",
                bucket="retainer",
            ),
        ],
        eligible_count=4,
        applications=[
            *[application(request_id) for request_id in single_ids],
            application(retainer_id, bucket="retainer"),
        ],
    )
    retainer_shot = evidence / "retainer-new.png"
    retainer_shot.write_bytes(b"fresh retainer marketplace screenshot")
    retainer_dom = evidence / "retainer-new.json"
    retainer_dom.write_text(json.dumps({
        "url": "https://coconala.com/job_matching/outsources",
        "observed": True,
        "not_found": False,
    }) + "\n", encoding="utf-8")
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["current_b2"]["search_sources"] = [
        {
            "source_id": "single:new",
            "url": "https://coconala.com/requests?sort=new",
            "screenshot_path": str((evidence / "requests.png").resolve()),
            "live_dom_path": str((evidence / "requests.json").resolve()),
            "inspected_count": 40,
            "has_next": True,
            "exhausted": False,
        },
        {
            "source_id": "retainer:new",
            "url": "https://coconala.com/job_matching/outsources",
            "screenshot_path": str(retainer_shot.resolve()),
            "live_dom_path": str(retainer_dom.resolve()),
            "inspected_count": 40,
            "has_next": True,
            "exhausted": False,
        },
    ]
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    all_ids = (*single_ids, retainer_id)
    for request_id in all_ids:
        (tmp_path / f"gig-fixture-B2-{request_id}-submitted.png").write_bytes(
            b"fresh submitted proof"
        )
    readback = evidence / "code-applied-readback.json"
    readback.write_text(json.dumps({
        "source": "code_owned_cdp_readback",
        "url": "https://coconala.com/mypage/job_matching/applied/offers",
        "urls": [
            "https://coconala.com/mypage/job_matching/applied/offers",
            (
                "https://coconala.com/mypage/job_matching/applied/"
                "outsource_applications"
            ),
        ],
        "observed": True,
        "not_found": False,
        "request_ids": list(all_ids),
    }) + "\n", encoding="utf-8")
    started = min(
        (tmp_path / f"gig-fixture-B2-{request_id}-submitted.png").stat().st_mtime
        for request_id in all_ids
    ) - 0.1
    rows = [{
        "requestId": request_id,
        "bucket": "single" if request_id.isdigit() else "retainer",
        "status": "applied",
        "submit_verified": True,
        "applied_page_verified": True,
    } for request_id in all_ids]

    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        ledger_rows=rows,
        min_mtime=started,
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_single_job_still_obeys_the_total_budget_floor(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[
            request(
                "91000043",
                applicants=0,
                budget_max_jpy=1500,
                outcome="eligible",
            )
        ],
        eligible_count=1,
        applications=[],
        exhaustive_search=True,
    )

    proc = validate(tmp_path, context, evidence, summary)

    assert "eligible_budget_below_minimum:91000043" in errors(proc)


def test_same_pass_verified_applications_accumulate_to_hourly_target(tmp_path):
    """A continuation attempt may report one new submit while the pass owns four."""
    context = build_context(tmp_path, target=4)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000046", applicants=1, outcome="eligible")],
        eligible_count=1,
        applications=[application("91000046")],
    )
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["current_b2"]["search_sources"] = [{
        "source_id": "single:new",
        "url": "https://coconala.com/requests?sort=new",
        "screenshot_path": str((evidence / "requests.png").resolve()),
        "live_dom_path": str((evidence / "requests.json").resolve()),
        "inspected_count": 1,
        "has_next": True,
        "exhausted": False,
    }]
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    ids = ("91000043", "91000044", "91000045", "91000046")
    for request_id in ids:
        (tmp_path / f"gig-fixture-B2-{request_id}-submitted.png").write_bytes(
            b"fresh submitted proof"
        )
    readback = evidence / "code-applied-readback.json"
    readback.write_text(json.dumps({
        "source": "code_owned_cdp_readback",
        "url": "https://coconala.com/mypage/job_matching/applied/offers",
        "observed": True,
        "not_found": False,
        "request_ids": list(ids),
    }) + "\n", encoding="utf-8")
    rows = [{
        "pass_id": "pass-1",
        "requestId": request_id,
        "status": "applied",
        "submit_verified": True,
        "applied_page_verified": True,
    } for request_id in ids]
    started = min(
        (tmp_path / f"gig-fixture-B2-{request_id}-submitted.png").stat().st_mtime
        for request_id in ids
    ) - 0.1

    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        ledger_rows=rows,
        min_mtime=started,
        pass_id="pass-1",
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_continuation_can_carry_a_same_pass_verified_application(tmp_path):
    """A cumulative continuation payload must not reclassify prior submit as new."""
    context = build_context(tmp_path, applied_ids=("91000063",))
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000063", applicants=65, outcome="eligible")],
        eligible_count=0,
        applications=[application("91000063")],
    )
    proof = tmp_path / "gig-fixture-B2-91000063-submitted.png"
    proof.write_bytes(b"fresh submitted proof")
    readback = evidence / "code-applied-readback.json"
    readback.write_text(json.dumps({
        "source": "code_owned_cdp_readback",
        "url": "https://coconala.com/mypage/job_matching/applied/offers",
        "observed": True,
        "not_found": False,
        "request_ids": ["91000063"],
    }) + "\n", encoding="utf-8")
    started = min(proof.stat().st_mtime, readback.stat().st_mtime) - 0.1

    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        ledger_rows=[{
            "pass_id": "pass-1",
            "requestId": "91000063",
            "status": "applied",
            "submit_verified": True,
            "applied_page_verified": True,
        }],
        min_mtime=started,
        pass_id="pass-1",
    )

    assert errors(proc) == ["under_target_search_not_exhausted"]


def test_continuation_accepts_carried_application_without_reinspecting_it(tmp_path):
    """A verified prior submit need not be re-opened on every pagination call.

    Production pass 1785272404 correctly carried its one same-pass application in
    ``applications`` while inspecting only new ineligible requests on page 4.
    Requiring the carried request to appear in every later ``inspected_requests``
    payload converted valid durable evidence into a non-retryable B2 failure.
    """
    carried_id = "91000017"
    context = build_context(tmp_path, applied_ids=(carried_id,))
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000039", applicants=34, outcome="ineligible")],
        eligible_count=1,
        applications=[application(carried_id)],
    )
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["current_b2"]["marketplace_url"] = (
        "https://coconala.com/requests?sort=new&page=4"
    )
    result["current_b2"]["search_sources"] = [{
        "source_id": "single:new",
        "url": "https://coconala.com/requests?sort=new&page=4",
        "screenshot_path": str((evidence / "requests.png").resolve()),
        "live_dom_path": str((evidence / "requests.json").resolve()),
        "inspected_count": 160,
        "has_next": True,
        "exhausted": False,
    }]
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    (evidence / "requests.json").write_text(json.dumps({
        "url": "https://coconala.com/requests?sort=new&page=4",
        "observed": True,
        "not_found": False,
    }) + "\n", encoding="utf-8")
    proof = tmp_path / f"gig-fixture-B2-{carried_id}-submitted.png"
    proof.write_bytes(b"fresh submitted proof")
    readback = evidence / "code-applied-readback.json"
    readback.write_text(json.dumps({
        "source": "code_owned_cdp_readback",
        "url": "https://coconala.com/mypage/job_matching/applied/offers",
        "observed": True,
        "not_found": False,
        "request_ids": [carried_id],
    }) + "\n", encoding="utf-8")
    cursor = tmp_path / "b2-next-cursor.json"
    cursor.write_text(json.dumps({
        "source_id": "single:new",
        "previous_url": "https://coconala.com/requests?sort=new&page=2",
        "next_url": "https://coconala.com/requests?sort=new&page=3",
        "reason": "next_page",
    }) + "\n", encoding="utf-8")
    started = min(proof.stat().st_mtime, readback.stat().st_mtime) - 0.1

    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        ledger_rows=[{
            "pass_id": "pass-1",
            "requestId": carried_id,
            "status": "applied",
            "submit_verified": True,
            "applied_page_verified": True,
        }],
        min_mtime=started,
        pass_id="pass-1",
        cursor_contract=cursor,
    )

    observed_errors = errors(proc)
    assert "eligible_count_mismatch:reported=1:observed_cumulative=0:observed_new=0" not in observed_errors
    assert f"application_not_eligible:{carried_id}" not in observed_errors
    assert observed_errors == ["under_target_search_not_exhausted"]


def test_continuation_accepts_two_carried_and_two_new_applications_at_target(tmp_path):
    """The final cumulative payload may contain two carried and two new submits."""
    carried_ids = ("91000065", "91000038")
    new_ids = ("91000054", "91000020")
    all_ids = carried_ids + new_ids
    # target=4 pins the AT-TARGET semantics this test is about, independent of the
    # production default (8 since 2026-08-06).
    context = build_context(tmp_path, applied_ids=carried_ids, target=4)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[
            request(request_id, applicants=1, outcome="eligible")
            for request_id in all_ids
        ],
        eligible_count=4,
        applications=[application(request_id) for request_id in all_ids],
    )
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["current_b2"]["search_sources"] = [{
        "source_id": "single:new",
        "url": "https://coconala.com/requests?sort=new",
        "screenshot_path": str((evidence / "requests.png").resolve()),
        "live_dom_path": str((evidence / "requests.json").resolve()),
        "inspected_count": 40,
        "has_next": True,
        "exhausted": False,
    }]
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    for request_id in all_ids:
        (tmp_path / f"gig-fixture-B2-{request_id}-submitted.png").write_bytes(
            b"fresh submitted proof"
        )
    readback = evidence / "code-applied-readback.json"
    readback.write_text(json.dumps({
        "source": "code_owned_cdp_readback",
        "url": "https://coconala.com/mypage/job_matching/applied/offers",
        "observed": True,
        "not_found": False,
        "request_ids": list(all_ids),
    }) + "\n", encoding="utf-8")
    rows = [{
        "pass_id": "pass-1",
        "requestId": request_id,
        "status": "applied",
        "submit_verified": True,
        "applied_page_verified": True,
    } for request_id in all_ids]
    started = min(
        (tmp_path / f"gig-fixture-B2-{request_id}-submitted.png").stat().st_mtime
        for request_id in all_ids
    ) - 0.1

    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        ledger_rows=rows,
        min_mtime=started,
        pass_id="pass-1",
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_an_eligible_request_cannot_already_be_in_the_application_ledger(tmp_path):
    context = build_context(tmp_path, applied_ids=("91000054",))
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000054", applicants=1, outcome="eligible")],
        eligible_count=1,
        applications=[application("91000054")],
    )
    proc = validate(tmp_path, context, evidence, summary)
    assert proc.returncode != 0
    assert "eligible_already_applied:91000054" in errors(proc)


def test_known_application_is_removed_from_expected_new_application_count(tmp_path):
    """A model dedupe miss is observable but must not demand a duplicate submit."""
    context = build_context(tmp_path, applied_ids=("91000064",))
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000064", applicants=17, outcome="eligible")],
        eligible_count=1,
        applications=[],
    )

    proc = validate(tmp_path, context, evidence, summary)
    observed = errors(proc)

    assert "eligible_already_applied:91000064" in observed
    assert not any(error.startswith("application_count_mismatch:") for error in observed)
    assert "under_target_search_not_exhausted" in observed


def test_repeated_ineligible_observation_is_safe_but_conflict_is_not(tmp_path):
    context = build_context(tmp_path)
    first = request("91000028", applicants=5, outcome="ineligible")
    repeated = {**first, "reason": "a second safe exclusion reason"}
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[first, repeated],
        eligible_count=0,
        applications=[],
    )

    safe_proc = validate(tmp_path, context, evidence, summary)
    safe_errors = errors(safe_proc)
    assert "inspected_request_duplicate:91000028" in safe_errors
    assert "inspected_request_conflict:91000028" not in safe_errors

    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["current_b2"]["inspected_requests"][1]["outcome"] = "eligible"
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")

    conflict_proc = validate(tmp_path, context, evidence, summary)
    assert "inspected_request_conflict:91000028" in errors(conflict_proc)


def test_reported_application_requires_fresh_submit_proof_and_ledger_row(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000042", applicants=1, outcome="eligible")],
        eligible_count=1,
        applications=[application("91000042")],
    )
    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        ledger_rows=[{"requestId": "91000042", "status": "applied"}],
        min_mtime=time.time() - 1,
    )
    assert proc.returncode != 0
    assert "application_submit_evidence_missing:91000042" in errors(proc)


def test_one_eligible_application_without_independent_applied_page_readback_fails(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000042", applicants=1, outcome="eligible")],
        eligible_count=1,
        applications=[application("91000042")],
    )
    proof = tmp_path / "gig-fixture-B2-91000042-submitted.png"
    proof.write_bytes(b"fresh submitted proof")
    started = proof.stat().st_mtime - 0.1
    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        ledger_rows=[{"requestId": "91000042", "status": "applied"}],
        min_mtime=started,
    )
    assert proc.returncode != 0
    assert "application_applied_page_readback_missing:91000042" in errors(proc)


def test_a_fresh_submit_proof_cannot_be_hidden_by_an_empty_model_report(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000042", applicants=1, outcome="ineligible")],
        eligible_count=0,
        applications=[],
    )
    proof = tmp_path / "gig-fixture-B2-91000042-submitted.png"
    proof.write_bytes(b"fresh submitted proof")
    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        ledger_rows=[{"requestId": "91000042", "status": "applied"}],
        min_mtime=proof.stat().st_mtime - 0.1,
    )
    assert proc.returncode != 0
    assert "unreported_submit_evidence:91000042" in errors(proc)


def test_context_binding_tamper_fails_closed(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("91000054", applicants=29, outcome="ineligible")],
        eligible_count=0,
        applications=[],
    )
    payload = json.loads(context.read_text(encoding="utf-8"))
    payload["max_applications"] = 6
    context.write_text(json.dumps(payload), encoding="utf-8")
    proc = validate(tmp_path, context, evidence, summary)
    assert proc.returncode != 0
    assert "context_sha256_mismatch" in errors(proc)


def test_pass_closes_on_single_evidence_with_zero_retainer_sources_swept(tmp_path):
    """A3 (2026-07-30): 継続 applications are refused in code, so a wake that never
    touched /job_matching/outsources must still reach its normal terminal state.

    Before A3 this exact shape failed with retainer_search_evidence_missing and the
    lane could not close until it had swept a bucket it can no longer apply into.
    """
    context = build_context(tmp_path)
    frozen = json.loads(context.read_text(encoding="utf-8"))
    assert "retainer:new" not in frozen["required_search_source_ids"]

    single_ids = ("91000048", "91000049", "91000050", "91000051")
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[
            request(request_id, applicants=1, outcome="eligible")
            for request_id in single_ids
        ],
        eligible_count=4,
        applications=[application(request_id) for request_id in single_ids],
        exhaustive_search=True,
    )
    for request_id in single_ids:
        (tmp_path / f"gig-fixture-B2-{request_id}-submitted.png").write_bytes(
            b"fresh submitted proof"
        )
    readback = evidence / "code-applied-readback.json"
    readback.write_text(json.dumps({
        "source": "code_owned_cdp_readback",
        "url": "https://coconala.com/mypage/job_matching/applied/offers",
        "observed": True,
        "not_found": False,
        "request_ids": list(single_ids),
    }) + "\n", encoding="utf-8")
    started = readback.stat().st_mtime - 1

    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        ledger_rows=[{
            "pass_id": "pass-a3",
            "requestId": request_id,
            "bucket": "single",
            "status": "applied",
            "submit_verified": True,
            "applied_page_verified": True,
        } for request_id in single_ids],
        min_mtime=started,
        pass_id="pass-a3",
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout
    swept = json.loads(
        (evidence / "attempt-01.result.json").read_text(encoding="utf-8")
    )["current_b2"]["search_sources"]
    assert [row["source_id"] for row in swept if "retainer" in row["source_id"]] == []
