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


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "b2_result_gate.py"


def run_gate(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        capture_output=True,
        text=True,
    )


def build_context(tmp_path: Path, *, applied_ids: tuple[str, ...] = ()) -> Path:
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
                else "https://coconala.com/job_matching/outsources"
                if source_id == "retainer:new"
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


def add_exhausted_retainer_source(evidence_dir: Path) -> None:
    shot = evidence_dir / "retainer-exhausted.png"
    shot.write_bytes(b"fresh exhausted retainer screenshot")
    dom = evidence_dir / "retainer-exhausted.json"
    url = "https://coconala.com/job_matching/outsources"
    dom.write_text(json.dumps({
        "url": url,
        "observed": True,
        "not_found": False,
    }) + "\n", encoding="utf-8")
    result_path = evidence_dir / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["current_b2"]["search_sources"].append({
        "source_id": "retainer:new",
        "url": url,
        "screenshot_path": str(shot.resolve()),
        "live_dom_path": str(dom.resolve()),
        "inspected_count": 40,
        "has_next": False,
        "exhausted": True,
    })
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")


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
    cursor_min_mtime: float | None = None,
    min_new_inspections: int = 0,
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
        args.extend((
            "--cursor-min-mtime",
            min_mtime if cursor_min_mtime is None else cursor_min_mtime,
        ))
    return run_gate(*args)


def errors(proc: subprocess.CompletedProcess[str]) -> list[str]:
    payload = json.loads((proc.stdout or proc.stderr).strip().splitlines()[-1])
    return payload["errors"]


def test_build_freezes_volume_budget_floor_sources_and_dedupe_ids(tmp_path):
    context = build_context(tmp_path, applied_ids=("5170001",))
    frozen = json.loads(context.read_text(encoding="utf-8"))
    assert frozen == {
        "version": 6,
        "target_applications": 4,
        "target_retainer_applications": 1,
        "max_applications": 7,
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
        "already_applied_request_ids": ["5170001"],
        "required_search_source_ids": [
            "single:new",
            "single:category:PPT/スライド",
            "single:keyword",
            "retainer:new",
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
                json.dumps({"requestId": "5170001"}),
                json.dumps({
                    "requestId": "5174303",
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
    assert frozen["already_applied_request_ids"] == ["5170001"]


def test_under_target_without_exhaustive_search_evidence_fails(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("5179838", applicants=29, outcome="ineligible")],
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
            request("5181687", applicants=28, outcome="ineligible"),
            request("5181669", applicants=0, outcome="ineligible"),
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
        inspected=[request("5179838", applicants=29, outcome="ineligible")],
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
        inspected=[request("5179838", applicants=29, outcome="ineligible")],
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
        inspected=[request("5174303", applicants=16, outcome="ineligible")],
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
    context = build_context(tmp_path)
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
            "5179409",
            "5178035",
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
        for request_id in ("5181422", "5179045", "5177557")
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
            "eligible_already_applied:5180735",
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
            "inspected_request_duplicate:5174747",
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
            "application_submit_evidence_missing:5179000",
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


def test_retainer_search_continues_after_four_single_applications(tmp_path):
    """The single target must not terminate an unfinished retainer sweep.

    Production pass 1785273897 submitted four verified single jobs with one
    model-call slot still available, then stopped on retainer_search_not_exhausted
    because continuation_state looked only at target_applications.
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
        for request_id in ("5179001", "5179002", "5179003", "5179004")
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
    assert payload["verified_count"] == 4
    assert payload["target"] == 4


def test_retainer_retry_stops_once_same_pass_retainer_is_verified(tmp_path):
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
        for request_id in ("5179001", "5179002", "5179003", "5179004")
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
        "next_url": "https://coconala.com/requests?sort=new",
        "reason": "inspect_missing_source",
    }


def test_parent_computes_the_exact_next_page_for_a_continuation(tmp_path):
    """The model must receive one code-owned next URL, not choose where to resume."""
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("5179838", applicants=29, outcome="ineligible")],
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
        "prior_inspected_request_ids": ["5179838"],
    }


def test_parent_rotates_to_the_least_covered_discovered_single_source(tmp_path):
    """A deep stale category must not starve shallower revenue sources.

    Production pass 1785374663-42264 spent eight B2 calls walking one source
    as deep as page 6 while other discovered categories were only on pages 1
    and 2.  Required-order-first pagination made 144 inspections yield zero
    applications before the hourly deadline.
    """
    context = build_context(tmp_path)
    frozen = json.loads(context.read_text(encoding="utf-8"))
    category_id = next(
        source_id
        for source_id in frozen["required_search_source_ids"]
        if source_id.startswith("single:category:")
    )
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("5179838", applicants=29, outcome="ineligible")],
        eligible_count=0,
        applications=[],
    )
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["current_b2"]["search_sources"] = [
        {
            "source_id": "single:new",
            "url": "https://coconala.com/requests?sort=new&page=5",
            "screenshot_path": str((evidence / "requests.png").resolve()),
            "live_dom_path": str((evidence / "requests.json").resolve()),
            "inspected_count": 80,
            "has_next": True,
            "exhausted": False,
        },
        {
            "source_id": category_id,
            "url": "https://coconala.com/requests/categories/427",
            "screenshot_path": str((evidence / "category.png").resolve()),
            "live_dom_path": str((evidence / "category.json").resolve()),
            "inspected_count": 12,
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
    assert json.loads(contract.read_text(encoding="utf-8")) == {
        "source_id": category_id,
        "previous_url": "https://coconala.com/requests/categories/427",
        "next_url": "https://coconala.com/requests/categories/427?page=2",
        "reason": "next_page",
        "prior_inspected_request_ids": ["5179838"],
    }


def test_parent_accepts_current_coconala_spot_route_for_continuation(tmp_path):
    """Production changed newest single jobs to the supplier spot route.

    Pass 1785373447-37605 submitted one verified application, then the parent
    rejected this exact live URL and could not continue toward its four-job
    target.
    """
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("5183557", applicants=0, outcome="eligible")],
        eligible_count=1,
        applications=[application("5183557")],
    )
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["current_b2"]["search_sources"] = [{
        "source_id": "single:new",
        "url": "https://coconala.com/job_matching/supplier/new?type=spot",
        "screenshot_path": str((evidence / "requests.png").resolve()),
        "live_dom_path": str((evidence / "requests.json").resolve()),
        "inspected_count": 12,
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
    assert json.loads(contract.read_text(encoding="utf-8")) == {
        "source_id": "single:new",
        "previous_url": "https://coconala.com/job_matching/supplier/new?type=spot",
        "next_url": (
            "https://coconala.com/job_matching/supplier/new?type=spot&page=2"
        ),
        "reason": "next_page",
        "prior_inspected_request_ids": ["5183557"],
    }


def test_parent_prioritizes_retainer_cursor_after_single_target_is_met(tmp_path):
    """Four singles must not trap continuation on infinite single pagination."""
    context = build_context(tmp_path)
    single_ids = ("5179001", "5179002", "5179003", "5179004")
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
    assert payload["source_id"] == "retainer:new"
    assert payload["previous_url"] == "https://coconala.com/job_matching/outsources"
    assert payload["next_url"] == "https://coconala.com/job_matching/outsources?page=2"
    assert payload["reason"] == "next_page"


def test_under_target_attempt_must_inspect_twelve_new_live_details(tmp_path):
    """Production pass 1785284583 returned after three details despite 40 live cards."""
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[
            request(str(5181000 + index), applicants=index, outcome="ineligible")
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
    prior_ids = [str(5181000 + index) for index in range(12)]
    current_ids = prior_ids + ["5182001", "5182002", "5182003"]
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
        inspected=[request("5179838", applicants=29, outcome="ineligible")],
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


def test_continuation_rejects_contracted_source_evidence_from_a_prior_invocation(tmp_path):
    """Pass-level freshness must not let call 7 reuse call 6's cursor DOM."""
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("5179838", applicants=29, outcome="ineligible")],
        eligible_count=0,
        applications=[],
    )
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    source_url = "https://coconala.com/requests?sort=new&page=2"
    source_shot = evidence / "single-new-page2.png"
    source_shot.write_bytes(b"prior invocation screenshot")
    source_dom = evidence / "single-new-page2.json"
    source_dom.write_text(json.dumps({
        "url": source_url,
        "observed": True,
        "not_found": False,
    }) + "\n", encoding="utf-8")
    result["current_b2"]["search_sources"] = [{
        "source_id": "single:new",
        "url": source_url,
        "screenshot_path": str(source_shot.resolve()),
        "live_dom_path": str(source_dom.resolve()),
        "inspected_count": 40,
        "has_next": True,
        "exhausted": False,
    }]
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    contract = tmp_path / "b2-next-cursor.json"
    contract.write_text(json.dumps({
        "source_id": "single:new",
        "previous_url": "https://coconala.com/requests?sort=new",
        "next_url": source_url,
        "reason": "next_page",
    }) + "\n", encoding="utf-8")
    prior_invocation_time = time.time() - 10
    source_shot.touch()
    source_dom.touch()
    import os
    os.utime(source_shot, (prior_invocation_time, prior_invocation_time))
    os.utime(source_dom, (prior_invocation_time, prior_invocation_time))

    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        min_mtime=prior_invocation_time - 1,
        cursor_contract=contract,
        cursor_min_mtime=prior_invocation_time + 1,
    )

    assert "unrecognized arguments" not in proc.stderr
    assert errors(proc) == [
        "continuation_cursor_screenshot_stale:single:new",
        "continuation_cursor_live_dom_stale:single:new",
        "under_target_search_not_exhausted",
    ]


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
        inspected=[request("5176013", applicants=2, outcome="ineligible")],
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


def test_competition_counts_do_not_close_an_open_application(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[
            request(
                "5179838",
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
    assert "eligible_max_applicants_exceeded:5179838" not in errors(proc)
    assert "eligible_contracted_threshold_reached:5179838" not in errors(proc)
    assert "application_count_mismatch:expected=1:actual=0" in errors(proc)


def test_open_request_with_quote_requested_budget_can_be_eligible(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[
            request(
                "5179838",
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
    assert "eligible_budget_missing:5179838" not in errors(proc)
    assert "application_count_mismatch:expected=1:actual=0" in errors(proc)


def test_closed_request_cannot_be_reported_eligible(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[
            request(
                "5179838",
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
    assert "eligible_marketplace_closed:5179838" in errors(proc)


def test_zero_eligible_with_an_explicit_ineligible_observation_passes(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("5179838", applicants=29, outcome="ineligible")],
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
        inspected=[request("5179000", applicants=1, outcome="eligible")],
        eligible_count=1,
        applications=[application("5179000")],
        exhaustive_search=True,
    )
    proof = tmp_path / "gig-fixture-B2-5179000-submitted.png"
    proof.write_bytes(b"fresh submitted proof")
    readback = evidence / "code-applied-readback.json"
    readback.write_text(json.dumps({
        "source": "code_owned_cdp_readback",
        "url": "https://coconala.com/mypage/job_matching/applied/offers",
        "observed": True,
        "not_found": False,
        "request_ids": ["5179000"],
    }) + "\n", encoding="utf-8")
    started = min(proof.stat().st_mtime, readback.stat().st_mtime) - 0.1
    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        ledger_rows=[{
            "requestId": "5179000",
            "status": "applied",
            "submit_verified": True,
            "applied_page_verified": True,
        }],
        min_mtime=started,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_canonical_readback_closes_submit_intent_when_helper_ack_is_lost(tmp_path):
    request_id = "5170842"
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


def test_hourly_target_includes_one_verified_retainer_application(tmp_path):
    context = build_context(tmp_path)
    single_ids = ("5179001", "5179002", "5179003")
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
                "5179001",
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

    assert "eligible_budget_below_minimum:5179001" in errors(proc)


def test_same_pass_verified_applications_accumulate_to_hourly_target(tmp_path):
    """A continuation attempt may report one new submit while the pass owns four."""
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("5179004", applicants=1, outcome="eligible")],
        eligible_count=1,
        applications=[application("5179004")],
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
    add_exhausted_retainer_source(evidence)
    ids = ("5179001", "5179002", "5179003", "5179004")
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
    context = build_context(tmp_path, applied_ids=("5180314",))
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("5180314", applicants=65, outcome="eligible")],
        eligible_count=0,
        applications=[application("5180314")],
    )
    proof = tmp_path / "gig-fixture-B2-5180314-submitted.png"
    proof.write_bytes(b"fresh submitted proof")
    readback = evidence / "code-applied-readback.json"
    readback.write_text(json.dumps({
        "source": "code_owned_cdp_readback",
        "url": "https://coconala.com/mypage/job_matching/applied/offers",
        "observed": True,
        "not_found": False,
        "request_ids": ["5180314"],
    }) + "\n", encoding="utf-8")
    started = min(proof.stat().st_mtime, readback.stat().st_mtime) - 0.1

    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        ledger_rows=[{
            "pass_id": "pass-1",
            "requestId": "5180314",
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
    carried_id = "5167088"
    context = build_context(tmp_path, applied_ids=(carried_id,))
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("5177557", applicants=34, outcome="ineligible")],
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
    assert observed_errors == [
        "continuation_cursor_not_advanced:single:new",
        "under_target_search_not_exhausted",
    ]


def test_continuation_accepts_two_carried_and_two_new_applications_at_target(tmp_path):
    """The final cumulative payload may contain two carried and two new submits."""
    carried_ids = ("5180746", "5177373")
    new_ids = ("5179838", "5170797")
    all_ids = carried_ids + new_ids
    context = build_context(tmp_path, applied_ids=carried_ids)
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
    add_exhausted_retainer_source(evidence)
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
    context = build_context(tmp_path, applied_ids=("5179838",))
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("5179838", applicants=1, outcome="eligible")],
        eligible_count=1,
        applications=[application("5179838")],
    )
    proc = validate(tmp_path, context, evidence, summary)
    assert proc.returncode != 0
    assert "eligible_already_applied:5179838" in errors(proc)


def test_known_application_is_removed_from_expected_new_application_count(tmp_path):
    """A model dedupe miss is observable but must not demand a duplicate submit."""
    context = build_context(tmp_path, applied_ids=("5180735",))
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("5180735", applicants=17, outcome="eligible")],
        eligible_count=1,
        applications=[],
    )

    proc = validate(tmp_path, context, evidence, summary)
    observed = errors(proc)

    assert "eligible_already_applied:5180735" in observed
    assert not any(error.startswith("application_count_mismatch:") for error in observed)
    assert "under_target_search_not_exhausted" in observed


def test_repeated_ineligible_observation_is_safe_but_conflict_is_not(tmp_path):
    context = build_context(tmp_path)
    first = request("5174747", applicants=5, outcome="ineligible")
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
    assert "inspected_request_duplicate:5174747" in safe_errors
    assert "inspected_request_conflict:5174747" not in safe_errors

    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["current_b2"]["inspected_requests"][1]["outcome"] = "eligible"
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")

    conflict_proc = validate(tmp_path, context, evidence, summary)
    assert "inspected_request_conflict:5174747" in errors(conflict_proc)


def test_reported_application_requires_fresh_submit_proof_and_ledger_row(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("5179000", applicants=1, outcome="eligible")],
        eligible_count=1,
        applications=[application("5179000")],
    )
    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        ledger_rows=[{"requestId": "5179000", "status": "applied"}],
        min_mtime=time.time() - 1,
    )
    assert proc.returncode != 0
    assert "application_submit_evidence_missing:5179000" in errors(proc)


def test_one_eligible_application_without_independent_applied_page_readback_fails(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("5179000", applicants=1, outcome="eligible")],
        eligible_count=1,
        applications=[application("5179000")],
    )
    proof = tmp_path / "gig-fixture-B2-5179000-submitted.png"
    proof.write_bytes(b"fresh submitted proof")
    started = proof.stat().st_mtime - 0.1
    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        ledger_rows=[{"requestId": "5179000", "status": "applied"}],
        min_mtime=started,
    )
    assert proc.returncode != 0
    assert "application_applied_page_readback_missing:5179000" in errors(proc)


def test_a_fresh_submit_proof_cannot_be_hidden_by_an_empty_model_report(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("5179000", applicants=1, outcome="ineligible")],
        eligible_count=0,
        applications=[],
    )
    proof = tmp_path / "gig-fixture-B2-5179000-submitted.png"
    proof.write_bytes(b"fresh submitted proof")
    proc = validate(
        tmp_path,
        context,
        evidence,
        summary,
        ledger_rows=[{"requestId": "5179000", "status": "applied"}],
        min_mtime=proof.stat().st_mtime - 0.1,
    )
    assert proc.returncode != 0
    assert "unreported_submit_evidence:5179000" in errors(proc)


def test_context_binding_tamper_fails_closed(tmp_path):
    context = build_context(tmp_path)
    evidence, summary = write_result(
        tmp_path,
        context,
        inspected=[request("5179838", applicants=29, outcome="ineligible")],
        eligible_count=0,
        applications=[],
    )
    payload = json.loads(context.read_text(encoding="utf-8"))
    payload["max_applications"] = 6
    context.write_text(json.dumps(payload), encoding="utf-8")
    proc = validate(tmp_path, context, evidence, summary)
    assert proc.returncode != 0
    assert "context_sha256_mismatch" in errors(proc)
