"""V2 cross-wake cache: unchanged ineligible rows do not consume planner capacity."""

from __future__ import annotations

import contextlib
import importlib.util
import inspect
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import application_snapshot as snapshot_contract  # noqa: E402
import application_direct as direct  # noqa: E402


PARENT_SCRIPT = ROOT / "scripts" / "application_parent.py"


def _load_parent():
    scripts = str(PARENT_SCRIPT.parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location("application_parent_v2_cache", PARENT_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _detail(request_id: str, brief: str) -> dict[str, object]:
    return {
        "request_id": request_id,
        "canonical_url": f"https://coconala.com/requests/{request_id}",
        "title": f"案件 {request_id}",
        "category": "コード",
        "visible_text": f"募集内容\n{brief}",
        "accepting_applications": True,
        "budget_min_jpy": 1000,
        "budget_max_jpy": 5000,
        "applicants_count": 0,
        "contracted_count": 0,
        "observed_at": "2026-08-10T00:00:00Z",
    }


def _content_hash(detail: dict[str, object]) -> str:
    return str(snapshot_contract._normalise_detail(detail)["content_sha256"])


class _TwoPageEffects:
    def __init__(self, details: dict[str, dict[str, object]]) -> None:
        self.details = details
        self.urls: list[str] = []

    def target_lock(self):
        return contextlib.nullcontext()

    def official_ids_for_snapshot(self):
        return []

    def collect_source(self, source_id, url, remaining):
        self.urls.append(url)
        page_two = "page=2" in url
        ids = ["1001", "1002"] if not page_two else ["1003"]
        ids = ids[: max(0, remaining)]
        next_url = (
            None
            if page_two
            else "https://coconala.com/requests?sort=new&recruiting=true&page=2"
        )
        return (
            {
                "source_id": source_id,
                "url": url,
                "page_index": 2 if page_two else 1,
                "card_request_ids": ids,
                "has_next": next_url is not None,
                "exhausted": next_url is None,
                "screenshot_sha256": "a" * 64,
                "dom_sha256": "b" * 64,
            },
            ids,
            {"screenshot_path": "source.png", "live_dom_path": "source.json"},
            next_url,
        )

    def reextract_detail(self, request_id):
        return self.details[request_id]


def _collect(parent, effects, cache):
    assert "ineligible_cache" in inspect.signature(parent.CdpSnapshotCollector).parameters
    return parent.CdpSnapshotCollector(
        effects,
        pass_id="v2-cache-test",
        objective={
            "target_applications": 2,
            "max_applications": 2,
            "required_search_source_ids": ["single:new"],
        },
        ineligible_cache=cache,
    ).collect({"task": "v2-cache", "token": "0" * 32, "generation": 1})


def test_unchanged_ineligible_rows_are_skipped_and_pagination_continues() -> None:
    parent = _load_parent()
    details = {
        request_id: _detail(request_id, f"内容 {request_id}")
        for request_id in ("1001", "1002", "1003")
    }
    cache = {
        request_id: {
            "content_sha256": _content_hash(details[request_id]),
            "reason_codes": ["not_feasible"],
            "judged_at_epoch": 1_000.0,
        }
        for request_id in ("1001", "1002")
    }
    effects = _TwoPageEffects(details)

    result = _collect(parent, effects, cache)

    assert effects.urls == [
        "https://coconala.com/requests?sort=new&recruiting=true",
        "https://coconala.com/requests?sort=new&recruiting=true&page=2",
    ]
    assert [row["request_id"] for row in result["request_details"]] == ["1003"]
    assert result["search_sources"][0]["card_request_ids"] == ["1003"]


def test_cached_candidates_remain_observable_with_title_and_reason() -> None:
    parent = _load_parent()
    details = {
        request_id: _detail(request_id, f"内容 {request_id}")
        for request_id in ("1001", "1002", "1003")
    }
    cache = {
        request_id: {
            "content_sha256": _content_hash(details[request_id]),
            "business_class": "hard_prohibited",
            "reason_codes": [f"reason_{request_id}"],
            "judged_at_epoch": 1_000.0,
        }
        for request_id in ("1001", "1002")
    }
    collector = parent.CdpSnapshotCollector(
        _TwoPageEffects(details),
        pass_id="observable-cache-test",
        objective={
            "target_applications": 2,
            "max_applications": 2,
            "required_search_source_ids": ["single:new"],
        },
        ineligible_cache=cache,
    )

    snapshot = collector.collect({"task": "cache", "token": "0" * 32, "generation": 1})
    observations = collector.observation_payload()

    assert [row["request_id"] for row in snapshot["request_details"]] == ["1003"]
    assert observations["raw_request_ids"] == ["1001", "1002", "1003"]
    assert observations["already_applied_ids"] == []
    assert observations["filtered_results"] == [
        {"request_id": "1001", "title": "案件 1001", "status": "cached_ineligible",
         "business_class": "hard_prohibited", "reason_codes": ["reason_1001"]},
        {"request_id": "1002", "title": "案件 1002", "status": "cached_ineligible",
         "business_class": "hard_prohibited", "reason_codes": ["reason_1002"]},
    ]


def test_direct_reports_raw_observation_and_cached_reason(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "application-snapshot.json").write_text(
        json.dumps({"request_details": []}), encoding="utf-8"
    )
    (evidence / "application-decisions.json").write_text(
        json.dumps({"decisions": []}), encoding="utf-8"
    )
    (evidence / "parent-commit.json").write_text(
        json.dumps({"results": []}), encoding="utf-8"
    )
    (evidence / "application-observations.json").write_text(json.dumps({
        "version": 1,
        "raw_request_ids": ["1001", "1002", "1003"],
        "already_applied_ids": ["1003"],
        "quarantined_ids": [],
        "filtered_results": [
            {"request_id": "1001", "title": "高単価AIシステム", "status": "cached_ineligible",
             "business_class": "hard_prohibited", "reason_codes": ["必須の対面対応"]},
            {"request_id": "1002", "title": "募集終了案件", "status": "closed",
             "reason_codes": ["募集終了"]},
        ],
    }), encoding="utf-8")

    values = direct.summarize(evidence, 0)
    report = direct._report("observation-truth", values)

    assert values["observed"] == 3
    assert values["already_applied_filtered"] == 1
    assert values["cached_ineligible_filtered"] == 1
    assert values["closed_filtered"] == 1
    assert "公式募集3件を確認" in report
    assert "既応募1件" in report and "判定cache1件" in report and "募集終了1件" in report
    assert "禁止条件1件" in report
    assert "高単価AIシステム" not in report and "必須の対面対応" not in report
    assert "募集終了案件" not in report


def test_changed_content_for_cached_id_is_rejudged() -> None:
    parent = _load_parent()
    details = {
        "1001": _detail("1001", "変更後の要件"),
        "1002": _detail("1002", "変更なし"),
        "1003": _detail("1003", "新規要件"),
    }
    cache = {
        "1001": {
            "content_sha256": _content_hash(_detail("1001", "変更前の要件")),
            "reason_codes": ["not_feasible"],
            "judged_at_epoch": 1_000.0,
        },
        "1002": {
            "content_sha256": _content_hash(details["1002"]),
            "reason_codes": ["not_feasible"],
            "judged_at_epoch": 1_000.0,
        },
    }

    result = _collect(parent, _TwoPageEffects(details), cache)

    assert {row["request_id"] for row in result["request_details"]} == {"1001", "1003"}


def test_malformed_and_expired_cache_entries_fail_open(tmp_path: Path) -> None:
    parent = _load_parent()
    loader = getattr(parent, "load_ineligible_cache", None)
    assert callable(loader)
    cache_path = tmp_path / "b2-ineligible-cache.json"
    cache_path.write_text("{not-json", encoding="utf-8")
    assert loader(cache_path, now=10_000.0) == {}

    cache_path.write_text(
        json.dumps({
            "version": 1,
            "entries": {
                "1001": {
                    "content_sha256": "a" * 64,
                    "reason_codes": ["not_feasible"],
                    "judged_at_epoch": 1.0,
                }
            },
        }),
        encoding="utf-8",
    )
    assert loader(cache_path, now=1.0 + parent.INELIGIBLE_CACHE_TTL_SECONDS + 1) == {}


def test_cache_records_only_validated_hard_prohibited_results(tmp_path: Path) -> None:
    parent = _load_parent()
    details = {
        "1001": _detail("1001", "本人の顔出し出演が必須です。"),
        "1002": _detail("1002", "内容 1002"),
        "1003": _detail("1003", "内容 1003"),
    }
    snapshot = _collect(parent, _TwoPageEffects(details), {})
    decisions = {
        "decisions": [
            {
                "request_id": "1001",
                "business_class": "hard_prohibited",
                "reason_codes": ["mandatory_human_presence", "本人の顔出し出演が必須です。"],
                "proposal_text": None,
                "price_jpy": None,
                "deliver_date": None,
            },
            {
                "request_id": "1002",
                "business_class": "submit_required",
                "reason_codes": [],
                "proposal_text": "提案文",
                "price_jpy": 1000,
                "deliver_date": "2026-08-11",
            },
            {
                "request_id": "1003",
                "business_class": "hard_prohibited",
                "reason_codes": ["mandatory_human_presence", "本人の顔出し出演が必須です。"],
                "proposal_text": None,
                "price_jpy": None,
                "deliver_date": None,
            },
        ]
    }
    cache_path = tmp_path / "b2-ineligible-cache.json"

    recorder = getattr(parent, "record_ineligible_results", None)
    assert callable(recorder)
    recorder(
        cache_path,
        snapshot,
        decisions,
        [
            {"request_id": "1001", "status": "hard_prohibited", "business_class": "hard_prohibited"},
            # A mismatched parent result must not make a submit-required decision cacheable.
            {"request_id": "1002", "status": "hard_prohibited", "business_class": "hard_prohibited"},
            {"request_id": "1003", "status": "confirmed"},
        ],
        now=20_000.0,
    )

    raw = json.loads(cache_path.read_text(encoding="utf-8"))
    assert set(raw["entries"]) == {"1001"}
    detail_by_id = {row["request_id"]: row for row in snapshot["request_details"]}
    assert raw["entries"]["1001"] == {
        "content_sha256": detail_by_id["1001"]["content_sha256"],
        "business_class": "hard_prohibited",
        "reason_codes": ["mandatory_human_presence", "本人の顔出し出演が必須です。"],
        "judged_at_epoch": 20_000.0,
    }


def test_direct_run_parent_none_does_not_resolve_home_ineligible_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = _load_parent()
    monkeypatch.setattr(
        parent,
        "default_ineligible_cache_path",
        lambda: (_ for _ in ()).throw(AssertionError("HOME cache path must not be resolved")),
    )
    context_path = tmp_path / "b2-context.json"
    context_path.write_text(json.dumps({
        "target_applications": 1,
        "max_applications": 1,
        "required_search_source_ids": ["single:new"],
    }), encoding="utf-8")

    with pytest.raises(parent.ParentContractError, match="lease_command_no_json"):
        parent.run_parent(
            lease_script=tmp_path / "missing-lease.py",
            lease_task="v2-cache-test-B2",
            context_path=context_path,
            pass_id="v2-cache-none",
            evidence_dir=tmp_path / "evidence",
            intent_root=tmp_path / "intents",
            ledger_path=tmp_path / "ledger.jsonl",
            output_path=tmp_path / "output.json",
            planner_runner=tmp_path / "runner.py",
            planner_schema=tmp_path / "schema.json",
            planner_workdir=tmp_path,
            planner_timeout_seconds=1,
            heartbeat_seconds=5.0,
            ineligible_cache_path=None,
        )


def test_empty_collected_snapshot_skips_planner_and_projects_exhaustion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = _load_parent()
    details = {
        request_id: _detail(request_id, f"内容 {request_id}")
        for request_id in ("1001", "1002", "1003")
    }
    cache = {
        request_id: {
            "content_sha256": _content_hash(details[request_id]),
            "reason_codes": ["not_feasible"],
            "judged_at_epoch": 1_000.0,
        }
        for request_id in details
    }
    snapshot = _collect(parent, _TwoPageEffects(details), cache)
    assert snapshot["request_details"] == []
    monkeypatch.setattr(
        parent,
        "_invoke_isolated_planner_once",
        lambda **_: pytest.fail("planner must not run for an exhausted snapshot"),
    )

    decisions, missing = parent.invoke_isolated_planner(
        runner=tmp_path / "runner.py",
        schema=tmp_path / "schema.json",
        snapshot=snapshot,
        evidence_dir=tmp_path / "evidence",
        workdir=tmp_path,
        timeout_seconds=1,
    )
    results = parent.commit_decisions(
        snapshot,
        decisions,
        store=parent.fence.IntentStore(tmp_path / "intents"),
        effects=_TwoPageEffects(details),
    )
    legacy = parent.project_legacy_b2(snapshot, decisions, results)

    assert decisions == {"decisions": []}
    assert missing == []
    assert results == []
    assert legacy["eligible_count"] == 0
    assert legacy["applications"] == []
    assert legacy["current_b2"]["inspected_requests"] == []
    assert legacy["current_b2"]["search_sources"][0]["exhausted"] is True
