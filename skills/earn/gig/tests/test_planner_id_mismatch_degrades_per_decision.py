from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


# B2 died on 2 of the last 3 passes over a single bad planner row instead of degrading:
#
#   22:27  decision_request_ids_not_one_to_one: missing=[91000119] unexpected=[91000087]
#          (a digit typo -- the planner meant 91000119, wrote 91000087)
#   23:41  decision_request_ids_not_one_to_one: missing=[91000102] unexpected=[]
#          (a plain omission)
#
# Both times validate_decisions correctly named the defect (see
# test_planner_id_mismatch_detail.py) and application_parent correctly raised -- but the
# raise was batch-fatal: one bad row killed every other well-formed decision in the same
# wake. This file pins the per-decision degradation: an id never in the snapshot is
# dropped (it was never judged against real detail data, so it can never be acted on), an
# omitted id is recorded as not-attempted-this-wake, and the rest of the batch proceeds.
# Any OTHER structural defect (duplicate id, malformed row on a real id) still fails the
# whole batch unchanged -- degradation is scoped to id identity only.

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
GATE_SCRIPT = SCRIPTS / "b2_result_gate.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PROPOSAL = (
    "募集内容と納品条件を確認しました。対象資料を案件ごとに整理し、必要な情報を原文から確認します。"
    "作業中は要件ごとの対応状況を記録し、完成後は指定形式、表示内容、文字化け、欠落の有無を検証します。"
    "成果物には実施内容と確認結果を添え、購入者が添付を開かなくても重要な結論が分かる説明を記載します。"
    "不明点は既存の会話、添付、関連URLを先に確認し、与えられた情報の範囲で作業可能な部分を完成させます。"
    "納品前に要求事項との対応表を再確認し、根拠のない完了報告や成果物のない進捗連絡は行いません。"
)


def build(tmp_path: Path):
    """A real, hash-bound 2-request envelope (ids A=91000032, B=91000033)."""
    parent = _load(SCRIPTS / "application_parent.py", "application_parent_id_mismatch_degrade")
    snapshot_module = _load(SCRIPTS / "application_snapshot.py", "application_snapshot_id_mismatch_degrade")
    collector = {
        "pass_id": "gig-pass-degrade-test",
        "lease_fence": {
            "task": "gig-pass-degrade-test-B2",
            "token": "0123456789abcdef0123456789abcdef",
            "generation": 7,
        },
        "observed_at": "2026-08-08T22:27:00Z",
        "objective": {
            "target_applications": 1,
            "max_applications": 7,
            "required_search_source_ids": ["single:new"],
        },
        "search_sources": [{
            "source_id": "single:new",
            "url": "https://coconala.com/requests?sort=new",
            "page_index": 1,
            "card_request_ids": ["91000032", "91000033"],
            "has_next": False,
            "exhausted": True,
            "screenshot_sha256": "a" * 64,
            "dom_sha256": "b" * 64,
        }],
        "request_details": [
            {
                "request_id": request_id,
                "canonical_url": f"https://coconala.com/requests/{request_id}",
                "title": f"AI 調査 {request_id}",
                "category": "リサーチ",
                "visible_text": "募集内容",
                "accepting_applications": True,
                "budget_min_jpy": 1000,
                "budget_max_jpy": 5000,
                "applicants_count": 0,
                "contracted_count": 0,
                "observed_at": "2026-08-08T22:27:00Z",
            }
            for request_id in ("91000032", "91000033")
        ],
        "already_applied_ids": [],
    }
    snapshot = snapshot_module.build_envelope(collector)
    return parent, snapshot


def _decision(request_id: str) -> dict:
    return {
        "request_id": request_id,
        "business_class": "submit_required",
        "reason_codes": [],
        "proposal_text": PROPOSAL,
        "price_jpy": 1000,
        "deliver_date": "2026-08-10",
    }


def test_typo_id_is_dropped_and_the_rest_of_the_batch_proceeds(tmp_path: Path) -> None:
    # 22:27 shape: missing=[91000033] unexpected=[9199999] (a typo on the second id).
    parent, snapshot = build(tmp_path)
    decisions = {"decisions": [_decision("91000032"), _decision("9199999")]}

    clean, missing = parent._degrade_id_mismatch(snapshot, decisions)

    assert [row["request_id"] for row in clean["decisions"]] == ["91000032"]
    assert missing == ["91000033"]


def test_omission_records_missing_and_the_rest_proceeds(tmp_path: Path) -> None:
    # 23:41 shape: missing=[91000033] unexpected=[] (a plain omission).
    parent, snapshot = build(tmp_path)
    decisions = {"decisions": [_decision("91000032")]}

    clean, missing = parent._degrade_id_mismatch(snapshot, decisions)

    assert [row["request_id"] for row in clean["decisions"]] == ["91000032"]
    assert missing == ["91000033"]


def test_omission_is_rejudged_once_without_rejudging_valid_sibling(
    tmp_path: Path, monkeypatch,
) -> None:
    parent, snapshot = build(tmp_path)
    calls = []

    def fake_planner_once(**kwargs):
        calls.append(kwargs["snapshot"])
        if len(calls) == 1:
            return {"decisions": [_decision("91000032")]}, ["91000033"]
        return {"decisions": [_decision("91000033")]}, []

    monkeypatch.setattr(parent, "_invoke_isolated_planner_once", fake_planner_once)

    decisions, missing = parent.invoke_isolated_planner(
        runner=tmp_path / "runner.py",
        schema=tmp_path / "schema.json",
        snapshot=snapshot,
        evidence_dir=tmp_path / "evidence",
        workdir=tmp_path,
        timeout_seconds=30,
    )

    assert [row["request_id"] for row in decisions["decisions"]] == ["91000032", "91000033"]
    assert missing == []
    assert [row["request_id"] for row in calls[1]["request_details"]] == ["91000033"]


def test_failed_omission_retry_keeps_valid_sibling_and_missing_truth(
    tmp_path: Path, monkeypatch,
) -> None:
    parent, snapshot = build(tmp_path)
    call_count = 0

    def fake_planner_once(**_kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"decisions": [_decision("91000032")]}, ["91000033"]
        raise parent.ParentContractError("invalid_retry")

    monkeypatch.setattr(parent, "_invoke_isolated_planner_once", fake_planner_once)

    decisions, missing = parent.invoke_isolated_planner(
        runner=tmp_path / "runner.py", schema=tmp_path / "schema.json",
        snapshot=snapshot, evidence_dir=tmp_path / "evidence",
        workdir=tmp_path, timeout_seconds=30,
    )

    assert [row["request_id"] for row in decisions["decisions"]] == ["91000032"]
    assert missing == ["91000033"]
    assert call_count == 2


def test_all_invalid_still_hard_fails(tmp_path: Path) -> None:
    parent, snapshot = build(tmp_path)
    decisions = {"decisions": [_decision("9199999"), _decision("8188888")]}

    try:
        parent._degrade_id_mismatch(snapshot, decisions)
        assert False, "expected ParentContractError when nothing in the batch survives"
    except parent.ParentContractError as error:
        assert "application_intent_planner_contract" in str(error)


def test_structural_defect_on_a_real_id_drops_only_that_row(tmp_path: Path) -> None:
    parent, snapshot = build(tmp_path)
    broken = _decision("91000033")
    broken["business_class"] = "maybe"
    decisions = {"decisions": [_decision("91000032"), broken]}

    clean, missing = parent._degrade_id_mismatch(snapshot, decisions)

    assert [row["request_id"] for row in clean["decisions"]] == ["91000032"]
    assert missing == ["91000033"]


def test_missing_decision_does_not_crash_commit_and_the_rest_of_the_batch_applies(tmp_path: Path) -> None:
    parent, snapshot = build(tmp_path)
    # This is exactly what _degrade_id_mismatch hands to commit_decisions: only the
    # well-formed intersection, 91000033 already recorded elsewhere as missing.
    decisions = {"decisions": [_decision("91000032")]}
    store = parent.fence.IntentStore(tmp_path / "intents")
    effects = parent.FixtureEffects(snapshot, {"official_applied_ids": ["91000032"]})

    results = parent.commit_decisions(snapshot, decisions, store=store, effects=effects)

    assert [row["request_id"] for row in results] == ["91000032"]
    assert results[0]["status"] == "confirmed"


def test_project_legacy_b2_omits_missing_ids_and_records_them(tmp_path: Path) -> None:
    parent, snapshot = build(tmp_path)
    decisions = {"decisions": [_decision("91000032")]}
    store = parent.fence.IntentStore(tmp_path / "intents")
    effects = parent.FixtureEffects(snapshot, {"official_applied_ids": ["91000032"]})
    results = parent.commit_decisions(snapshot, decisions, store=store, effects=effects)

    legacy_b2 = parent.project_legacy_b2(
        snapshot, decisions, results, planner_missing_request_ids=["91000033"]
    )

    assert legacy_b2["planner_missing_request_ids"] == ["91000033"]
    inspected_ids = [row["request_id"] for row in legacy_b2["current_b2"]["inspected_requests"]]
    assert inspected_ids == ["91000032"]
    assert legacy_b2["eligible_count"] == 1
    assert legacy_b2["current_b2"]["inspected_requests"][0]["outcome"] == "eligible"
    assert [app["request_id"] for app in legacy_b2["applications"]] == ["91000032"]


# -- Gate side: a planner-missing id must not turn into a phantom application_count
# mismatch. b2_result_gate.py computes expected_applications from len(new_eligible_ids),
# which it derives from current_b2.inspected_requests -- so a dropped/missing id that
# never appears there is already excluded from the count, not a defect to special-case.


def _run_gate(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GATE_SCRIPT), *map(str, args)],
        capture_output=True,
        text=True,
    )


def _gate_errors(proc: subprocess.CompletedProcess[str]) -> list[str]:
    payload = json.loads((proc.stdout or proc.stderr).strip().splitlines()[-1])
    return payload["errors"]


def test_gate_does_not_flag_application_count_mismatch_for_a_planner_missing_id(tmp_path: Path) -> None:
    prep = {
        "max_apply_per_pass": 7,
        "target_apply_per_pass": 1,
        "category_order": ["PPT/スライド"],
        "apply_skip_thresholds": {
            "max_applicants": 12,
            "min_contracted_to_skip": 1,
            "min_budget_jpy": 3000,
        },
    }
    applied = tmp_path / "applied.jsonl"
    applied.write_text("", encoding="utf-8")
    context = tmp_path / "b2-context.json"
    build_proc = _run_gate(
        "build", "--prep-json", json.dumps(prep), "--applied", applied, "--output", context
    )
    assert build_proc.returncode == 0, build_proc.stderr or build_proc.stdout

    evidence_dir = tmp_path / "agent-B2"
    evidence_dir.mkdir()
    marketplace_shot = evidence_dir / "requests.png"
    marketplace_shot.write_bytes(b"fresh marketplace screenshot")
    marketplace_dom = evidence_dir / "requests.json"
    marketplace_dom.write_text(
        json.dumps({"url": "https://coconala.com/requests?sort=new", "not_found": False, "observed": True}),
        encoding="utf-8",
    )
    import hashlib

    result_path = evidence_dir / "attempt-01.result.json"
    result_path.write_text(
        json.dumps({
            "status": "ok",
            "summary": "fixture",
            "evidence": ["fixture evidence"],
            # Only the id the planner actually decided on this wake -- 91000033 was
            # recorded as planner_missing and simply never appears here.
            "planner_missing_request_ids": ["91000033"],
            "eligible_count": 1,
            "applications": [{
                "request_id": "91000032",
                "bucket": "single",
                "category": "システム開発・制作",
                "title": "fixture",
                "price_jpy": 8000,
                "deliver_date": "2026-07-29",
                "url": "https://coconala.com/requests/91000032",
                "compensation_type": None,
                "weekly_days": None,
                "weekly_hours_min": None,
                "weekly_hours_max": None,
            }],
            "current_b2": {
                "context_path": str(context.resolve()),
                "context_sha256": hashlib.sha256(context.read_bytes()).hexdigest(),
                "marketplace_url": "https://coconala.com/requests?sort=new",
                "marketplace_screenshot_path": str(marketplace_shot.resolve()),
                "marketplace_live_dom_path": str(marketplace_dom.resolve()),
                "inspected_requests": [{
                    "request_id": "91000032",
                    "bucket": "single",
                    "url": "https://coconala.com/requests/91000032",
                    "applicants": 0,
                    "contracted": 0,
                    "budget_max_jpy": 10000,
                    "compensation_type": None,
                    "compensation_min_jpy": None,
                    "compensation_max_jpy": None,
                    "weekly_days": None,
                    "weekly_hours_min": None,
                    "weekly_hours_max": None,
                    "remote": None,
                    "synchronous_interview_required": None,
                    "human_identity_required": None,
                    "accepting_applications": True,
                    "outcome": "eligible",
                    "reason": None,
                }],
                "search_sources": [],
            },
        }) + "\n",
        encoding="utf-8",
    )
    summary = evidence_dir / "summary.json"
    summary.write_text(
        json.dumps({
            "status": "success",
            "task_label": "gig-B2",
            "result_path": str(result_path.resolve()),
        }) + "\n",
        encoding="utf-8",
    )
    ledger = tmp_path / "applied-ledger.jsonl"
    ledger.write_text("", encoding="utf-8")

    proc = _run_gate(
        "validate",
        "--context", context,
        "--runner-summary", summary,
        "--evidence-dir", evidence_dir,
        "--evidence-root", tmp_path,
        "--ledger", ledger,
        "--min-mtime", 0,
        "--min-new-inspections", 0,
    )

    found = _gate_errors(proc)
    assert not any(error.startswith("application_count_mismatch") for error in found), found
    assert not any(error.startswith("eligible_count_mismatch") for error in found), found
