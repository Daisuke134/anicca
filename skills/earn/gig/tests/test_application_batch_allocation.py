"""How the apply lane spends its batch: depth, exclusion, and per-source evidence.

Every number quoted here was measured on 2026-08-07 over 36 passes of real evidence in
~/gig/evidence/gig-pass-*/agent-B2/, not chosen. The lane was applying 1.03 times a pass
against a target of 8, and the eligible pool it drew from was 5.86 -- of which 3.33 was
spent on requests the commit boundary had already decided to refuse.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import importlib.util
import json
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
PARENT_SCRIPT = SCRIPTS / "application_parent.py"
GIG_PASS_SCRIPT = ROOT / "gig_pass.sh"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _detail_with_mocked_cdp(parent, monkeypatch, *, accepting: bool, category, text: str, lifecycle=False, title="detail"):
    effects = object.__new__(parent.CdpParentEffects)
    effects.ws_url = "ws://detail-test"
    form_calls: list[tuple[str, bool]] = []

    class Connection:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *_args):
            return False

    async def fake_call(_ws, _method, _params, call_id):
        return {}

    async def fake_navigate(_ws, _url, call_id):
        return call_id + 1

    async def fake_eval(_ws, _expression, call_id):
        page = {
            "url": "https://coconala.com/requests/123450",
            "title": title,
            "text": text,
            "category": category,
            "accepting": accepting,
        }
        if lifecycle:
            page.update({"page_state": "present", "accepting_control": "present", "deadline_state": "future", "deadline_value": "2026-08-20", "recommended_deadline_value": "2026-08-14"})
        return page, call_id + 1

    monkeypatch.setattr(parent.websockets, "connect", lambda *args, **kwargs: Connection())
    monkeypatch.setattr(effects, "_call", fake_call)
    monkeypatch.setattr(effects, "_navigate", fake_navigate)
    monkeypatch.setattr(effects, "_eval_json", fake_eval)
    if lifecycle:
        async def fake_form_state(request_id: str, *, navigate: bool):
            form_calls.append((request_id, navigate))
            return {"url": f"https://coconala.com/offers/add/{request_id}", "has_content": True, "has_price": True, "has_date": True}
        monkeypatch.setattr(effects, "_form_state_async", fake_form_state)
    detail = asyncio.run(effects._detail_async("123450"))
    return (detail, form_calls) if lifecycle else detail


@pytest.mark.parametrize(
    ("accepting", "category", "text", "expected_category"),
    [
        (False, None, "募集内容\n終了した募集", "募集終了"),
        (False, "既存カテゴリ", "募集内容\n終了した募集", "既存カテゴリ"),
        (True, "既存カテゴリ", "募集内容\n募集中の募集", "既存カテゴリ"),
    ],
)
def test_detail_category_preserves_open_and_closed_or_uses_closed_fallback(
    monkeypatch, accepting, category, text, expected_category
) -> None:
    parent = _load(PARENT_SCRIPT, f"application_parent_detail_category_{accepting}_{category}")

    detail = _detail_with_mocked_cdp(
        parent,
        monkeypatch,
        accepting=accepting,
        category=category,
        text=text,
    )

    assert detail["accepting_applications"] is accepting
    assert detail["category"] == expected_category


def test_open_detail_missing_category_remains_fail_closed(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_detail_category_open_missing")

    with pytest.raises(parent.ParentContractError, match="detail_category_missing"):
        _detail_with_mocked_cdp(
            parent,
            monkeypatch,
            accepting=True,
            category=None,
            text="募集内容\nカテゴリのない募集中の募集",
        )


@pytest.mark.parametrize("title", ["403 Forbidden", "Access Denied"])
def test_source_access_denied_fails_before_observation_but_empty_source_is_valid(
    tmp_path: Path, monkeypatch, title: str,
) -> None:
    parent = _load(PARENT_SCRIPT, f"application_parent_source_access_denied_{title}")

    class Connection:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *_args):
            return False

    effects = parent.CdpParentEffects(
        ws_url="ws://source-test", evidence_dir=tmp_path,
        ledger_path=tmp_path / "ledger.jsonl", pass_id="source-pass",
    )

    monkeypatch.setattr(parent.websockets, "connect", lambda *args, **kwargs: Connection())
    async def fake_call(_ws, _method, _params, call_id):
        return {}
    async def fake_navigate(_ws, _url, call_id):
        return call_id + 1
    async def fake_eval(_ws, _expression, call_id):
        return {
            "url": "https://coconala.com/requests?sort=new",
            "title": title,
            "text": "403 Forbidden" if title == "403 Forbidden" else "Access Denied",
            "hrefs": [],
            "next_href": None,
            "access_denied": True,
            "not_found": False,
        }, call_id + 1
    async def fake_screenshot(_ws, call_id):
        return b"png", call_id + 1
    monkeypatch.setattr(effects, "_call", fake_call)
    monkeypatch.setattr(effects, "_navigate", fake_navigate)
    monkeypatch.setattr(effects, "_eval_json", fake_eval)
    monkeypatch.setattr(effects, "_screenshot", fake_screenshot)

    with pytest.raises(parent.ParentContractError, match="source_access_denied:single:new"):
        effects.collect_source(
            "single:new", "https://coconala.com/requests?sort=new", remaining=20,
        )

    async def fake_empty_eval(_ws, _expression, call_id):
        return {
            "url": "https://coconala.com/requests?sort=new",
            "title": "案件一覧",
            "text": "募集中の案件はありません",
            "hrefs": [],
            "next_href": None,
            "access_denied": False,
            "not_found": False,
        }, call_id + 1
    monkeypatch.setattr(effects, "_eval_json", fake_empty_eval)
    source, request_ids, _artifacts, next_url = effects.collect_source(
        "single:new", "https://coconala.com/requests?sort=new", remaining=20,
    )
    assert request_ids == []
    assert next_url is None
    assert source["observed"] if "observed" in source else source["exhausted"] is True


def test_numbered_pagination_retains_the_open_new_source_filters(tmp_path: Path, monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_numbered_pagination")

    class Connection:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *_args):
            return False

    effects = parent.CdpParentEffects(
        ws_url="ws://source-test", evidence_dir=tmp_path,
        ledger_path=tmp_path / "ledger.jsonl", pass_id="source-pass",
    )
    monkeypatch.setattr(parent.websockets, "connect", lambda *args, **kwargs: Connection())

    async def fake_call(_ws, _method, _params, call_id):
        return {}

    async def fake_navigate(_ws, _url, call_id):
        return call_id + 1

    async def fake_eval(_ws, _expression, call_id):
        return {
            "url": "https://coconala.com/requests?page=2&recruiting=true&sort=new",
            "title": "案件一覧 - 2ページ目",
            "text": "",
            "hrefs": [],
            "next_href": "https://coconala.com/requests?page=3",
            "access_denied": False,
            "not_found": False,
        }, call_id + 1

    async def fake_screenshot(_ws, call_id):
        return b"png", call_id + 1

    monkeypatch.setattr(effects, "_call", fake_call)
    monkeypatch.setattr(effects, "_navigate", fake_navigate)
    monkeypatch.setattr(effects, "_eval_json", fake_eval)
    monkeypatch.setattr(effects, "_screenshot", fake_screenshot)

    source, request_ids, _artifacts, next_url = effects.collect_source(
        "single:new",
        "https://coconala.com/requests?page=2&recruiting=true&sort=new",
        remaining=20,
    )

    assert request_ids == []
    assert next_url == "https://coconala.com/requests?recruiting=true&sort=new&page=3"
    assert source["has_next"] is True
    assert source["exhausted"] is False


def test_terminal_source_remains_exhausted_when_local_batch_truncates_cards(
    tmp_path: Path, monkeypatch,
) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_terminal_batch_truncation")
    effects = object.__new__(parent.CdpParentEffects)
    effects.evidence_dir = tmp_path

    async def fake_source(_source_id, _url):
        return {
            "url": "https://coconala.com/requests?page=8&recruiting=true&sort=new",
            "title": "案件一覧 - 8ページ目",
            "text": "319 件中 281 - 319 件表示",
            "hrefs": [
                "https://coconala.com/requests/5210001",
                "https://coconala.com/requests/5210002",
                "https://coconala.com/requests/5210003",
            ],
            "next_href": None,
        }, b"png"

    monkeypatch.setattr(effects, "_source_async", fake_source)
    source, request_ids, _artifacts, next_url = effects.collect_source(
        "single:new",
        "https://coconala.com/requests?page=8&recruiting=true&sort=new",
        remaining=2,
    )

    assert request_ids == ["5210001", "5210002"]
    assert next_url is None
    assert source["has_next"] is False
    assert source["exhausted"] is True


def _lifecycle_detail(
    *,
    request_id: str,
    page_state: str = "present",
    accepting_control: str = "present",
    deadline_state: str = "future",
    deadline_value: str | None = "2026-08-20",
    form_state: str = "present",
    accepting_applications: bool = True,
    title: str | None = None,
) -> dict[str, object]:
    detail = {
        "request_id": request_id,
        "canonical_url": f"https://coconala.com/requests/{request_id}",
        "title": title or f"title-{request_id}",
        "category": "コード",
        "visible_text": f"募集内容\n詳細 {request_id}",
        "accepting_applications": accepting_applications,
        "budget_min_jpy": 10000,
        "budget_max_jpy": 10000,
        "applicants_count": 0,
        "contracted_count": 0,
        "observed_at": "2026-08-13T00:00:00Z",
        "page_state": page_state,
        "accepting_control": accepting_control,
        "deadline_state": deadline_state,
        "deadline_value": deadline_value,
        "form_state": form_state,
    }
    detail["lifecycle_sha256"] = hashlib.sha256(json.dumps(
        {"request_id": request_id, "canonical_url": detail["canonical_url"], **{
            field: detail[field] for field in ("page_state", "accepting_control", "deadline_state", "deadline_value", "form_state")
        }}, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
    return detail


def test_open_detail_binds_primary_deadline_and_readonly_exact_form(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_lifecycle_open_detail")

    detail, form_calls = _detail_with_mocked_cdp(
        parent, monkeypatch, accepting=True, category="コード", text="募集内容\n詳細", lifecycle=True
    )

    assert detail["page_state"] == "present"
    assert detail["accepting_control"] == "present"
    assert detail["deadline_state"] == "future"
    assert detail["deadline_value"] == "2026-08-20"
    assert detail["form_state"] == "present"
    assert detail["accepting_applications"] is True
    assert len(detail["lifecycle_sha256"]) == 64
    assert form_calls == [("123450", True)]


def test_real_lifecycle_digest_is_validated_without_duplicate_keyword_error() -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_lifecycle_digest_real_shape")
    detail = _lifecycle_detail(request_id="1031")
    detail["lifecycle_sha256"] = parent._lifecycle_digest(
        detail["request_id"],
        detail["canonical_url"],
        **{field: detail[field] for field in parent._LIFECYCLE_FIELDS},
    )

    assert parent._lifecycle_disposition(detail)[0] == "open"


def test_not_found_title_with_official_phrase_is_not_present(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_lifecycle_not_found_title")

    detail, _ = _detail_with_mocked_cdp(
        parent,
        monkeypatch,
        accepting=True,
        category="コード",
        text="ご指定のページが見つかりませんでした",
        lifecycle=True,
        title="ご指定のページが見つかりませんでした | ココナラ",
    )

    assert detail["page_state"] == "not_found"
    assert detail["accepting_applications"] is False


def test_not_found_lifecycle_is_official_even_when_other_fields_are_unknown() -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_lifecycle_not_found_unknown_fields")
    detail = _lifecycle_detail(
        request_id="999999999",
        page_state="not_found",
        accepting_control="absent",
        deadline_state="unknown",
        deadline_value=None,
        form_state="unknown",
        accepting_applications=True,
    )
    detail["lifecycle_sha256"] = parent._lifecycle_digest(
        detail["request_id"], detail["canonical_url"],
        **{field: detail[field] for field in parent._LIFECYCLE_FIELDS},
    )

    assert parent._lifecycle_disposition(detail)[0] == "official_unavailable"


class _LifecycleEffects:
    def __init__(self, details: dict[str, dict[str, object]], *, applied=None):
        self.details = details
        self.applied = list(applied or [])

    def target_lock(self):
        return contextlib.nullcontext()

    def official_ids_for_snapshot(self):
        return self.applied

    def collect_source(self, source_id, url, remaining):
        ids = list(self.details)[: max(0, remaining)]
        return (
            {
                "source_id": source_id,
                "url": url,
                "page_index": 1,
                "card_request_ids": ids,
                "has_next": False,
                "exhausted": True,
                "screenshot_sha256": "a" * 64,
                "dom_sha256": "b" * 64,
            },
            ids,
            {"screenshot_path": "p.png", "live_dom_path": "p.json"},
            None,
        )

    def reextract_detail(self, request_id):
        return self.details[request_id]


def _collect_lifecycle(parent, monkeypatch, effects, *, ineligible_cache=None, intent_store=None):
    monkeypatch.setattr(parent.snapshot_contract, "build_envelope", lambda value: value)
    collector = parent.CdpSnapshotCollector(
        effects,
        pass_id="lifecycle",
        objective={"required_search_source_ids": ["single:new"]},
        ineligible_cache=ineligible_cache,
        intent_store=intent_store,
    )
    result = collector.collect({"lease_id": "test"})
    observations = collector.observation_payload()
    result["lifecycle_results"] = observations["lifecycle_results"]
    result["already_applied_ids"] = observations["already_applied_ids"]
    return result


def test_official_unavailable_lifecycle_never_reaches_request_details(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_lifecycle_unavailable")
    details = {
        "1001": _lifecycle_detail(
            request_id="1001", page_state="not_found", accepting_applications=True
        ),
        "1002": _lifecycle_detail(
            request_id="1002", deadline_state="expired", deadline_value="2026-08-12"
        ),
        "1003": _lifecycle_detail(
            request_id="1003", accepting_control="absent"
        ),
        "1004": _lifecycle_detail(
            request_id="1004", form_state="absent"
        ),
    }

    result = _collect_lifecycle(parent, monkeypatch, _LifecycleEffects(details))

    assert result["request_details"] == []
    assert all(
        result["lifecycle_results"][index]["status"] == "officially_unavailable"
        for index in range(len(details))
    )


def test_prepared_intent_precedes_account_page_without_application_form(
    monkeypatch, tmp_path: Path
) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_prepared_account_state")
    request_id = "1005"
    store = parent.fence.IntentStore(tmp_path / "intents")
    prepared = store.prepare(
        request_id=request_id,
        snapshot_sha256="a" * 64,
        proposal_text="verified proposal",
        price_jpy=80000,
        deliver_date="2026-08-31",
        lease_fence={"task": "apply", "token": "b" * 32, "generation": 1},
    )
    with store.locked(request_id):
        store.mark_irreversible_attempt_started_locked(
            request_id, expected_cas=prepared["intent"]["cas"]
        )
    detail = _lifecycle_detail(
        request_id=request_id,
        accepting_control="absent",
        form_state="absent",
    )

    result = _collect_lifecycle(
        parent,
        monkeypatch,
        _LifecycleEffects({request_id: detail}),
        intent_store=store,
    )

    assert result["request_details"] == []
    assert result["lifecycle_results"] == []
    assert result["already_applied_ids"] == [request_id]


def test_pre_effect_intent_does_not_override_officially_unavailable_lifecycle(
    monkeypatch, tmp_path: Path
) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_pre_effect_account_state")
    request_id = "1005"
    store = parent.fence.IntentStore(tmp_path / "intents")
    store.prepare(
        request_id=request_id, snapshot_sha256="a" * 64,
        proposal_text="verified proposal", price_jpy=80000,
        deliver_date="2026-08-31",
        lease_fence={"task": "apply", "token": "b" * 32, "generation": 1},
    )
    detail = _lifecycle_detail(
        request_id=request_id, accepting_control="absent", form_state="absent"
    )

    result = _collect_lifecycle(
        parent, monkeypatch, _LifecycleEffects({request_id: detail}), intent_store=store
    )

    assert result["already_applied_ids"] == []
    assert result["lifecycle_results"][0]["status"] == "officially_unavailable"


def test_unknown_lifecycle_is_request_local_and_does_not_starve_next_candidate(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_lifecycle_unknown_bulkhead")
    details = {
        "1010": _lifecycle_detail(
            request_id="1010",
            page_state="unknown",
            accepting_control="unknown",
            deadline_state="unknown",
            deadline_value=None,
            form_state="unknown",
            accepting_applications=True,
        ),
        "1011": _lifecycle_detail(request_id="1011"),
    }

    result = _collect_lifecycle(parent, monkeypatch, _LifecycleEffects(details))

    assert [detail["request_id"] for detail in result["request_details"]] == ["1011"]
    assert result["lifecycle_results"][0]["status"] == "unknown"


def test_official_lifecycle_precedes_unchanged_ineligible_cache(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_lifecycle_before_cache")
    detail = _lifecycle_detail(request_id="1020", form_state="absent")
    detail["content_sha256"] = "c" * 64

    result = _collect_lifecycle(
        parent,
        monkeypatch,
        _LifecycleEffects({"1020": detail}),
        ineligible_cache={"1020": {"content_sha256": "c" * 64, "reason_codes": ["old"]}},
    )

    assert result["lifecycle_results"][0]["status"] == "officially_unavailable"
    assert result["lifecycle_results"][0]["status"] != "cached_ineligible"


@pytest.mark.parametrize(
    "field_overrides",
    [
        {"page_state": "not_found"},
        {"accepting_control": "absent"},
        {"deadline_state": "expired", "deadline_value": "2026-08-12"},
        {"form_state": "absent"},
    ],
    ids=["not-found", "apply-absent", "deadline-expired", "form-absent"],
)
def test_fresh_detail_requires_full_open_lifecycle(field_overrides) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_lifecycle_fresh_gate")
    open_detail = _lifecycle_detail(request_id="1030")
    snapshot_detail = parent.snapshot_contract._normalise_detail(open_detail)
    fresh_detail = {**open_detail, **field_overrides}

    assert parent._fresh_detail(snapshot_detail, open_detail) is True
    assert parent._fresh_detail(snapshot_detail, fresh_detail) is False


@pytest.mark.parametrize("invalid", ["legacy", "missing_digest", "impossible_date", "past_future"], ids=["legacy", "missing-digest", "impossible-date", "past-future-contradiction"])
def test_pre_submit_requires_valid_open_lifecycle_and_never_prepares(invalid, tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, f"application_parent_presubmit_lifecycle_{invalid}")
    snapshot = _nine_candidate_snapshot(parent, cap=1, count=1)
    detail = snapshot["request_details"][0]
    request_id = detail["request_id"]
    fresh = dict(detail)
    if invalid != "legacy":
        fresh.update({"page_state": "present", "accepting_control": "present", "deadline_state": "future", "deadline_value": "2026-08-20", "form_state": "present"})
        if invalid == "impossible_date": fresh.update(deadline_value="2026-02-30")
        if invalid == "past_future": fresh.update(deadline_value="2026-08-12")
        fresh["lifecycle_sha256"] = parent._lifecycle_digest(request_id, fresh["canonical_url"], **{field: fresh[field] for field in parent._LIFECYCLE_FIELDS})
        if invalid == "missing_digest": fresh.pop("lifecycle_sha256")
    effects = parent.FixtureEffects(snapshot, {"fresh_details": {request_id: fresh}})
    store = parent.fence.IntentStore(tmp_path / invalid)
    result = parent.commit_decisions(snapshot, {"decisions": [_eligible_decision_for(request_id)]}, store=store, effects=effects)
    assert result[0]["status"] == "stale_snapshot"
    assert effects.open_count == effects.fill_count == effects.click_count == 0
    assert store.read(request_id) is None


def test_discovery_timeout_keeps_completed_shards_for_single_writer(monkeypatch) -> None:
    """A timed-out read-only shard must not discard candidates from completed shards."""
    parent = _load(PARENT_SCRIPT, "application_parent_shard_timeout_partial")
    required = [f"single:category:cat-{index}" for index in range(4)]
    detail_ids = {source: str(123450 + index) for index, source in enumerate(required)}
    details = {
        detail_ids[source]: {
            "request_id": detail_ids[source],
            "canonical_url": f"https://coconala.com/requests/{detail_ids[source]}",
            "title": source,
            "category": "software",
            "visible_text": source,
            "accepting_applications": True,
            "budget_min_jpy": None,
            "budget_max_jpy": None,
            "applicants_count": 0,
            "contracted_count": 0,
            "observed_at": "2026-08-11T00:00:00Z",
        }
        for source in required
    }

    class Effects:
        def __init__(self, source, *, timeout=False):
            self.source = source
            self.timeout = timeout

        def target_lock(self):
            return contextlib.nullcontext()

        def official_ids_for_snapshot(self):
            return []

        def collect_source(self, source_id, url, remaining):
            if self.timeout:
                raise TimeoutError("discovery shard deadline")
            request_id = detail_ids[source_id]
            return (
                {
                    "source_id": source_id,
                    "url": url,
                    "page_index": 1,
                    "card_request_ids": [request_id],
                    "has_next": False,
                    "exhausted": True,
                    "screenshot_sha256": "a" * 64,
                    "dom_sha256": "b" * 64,
                },
                [request_id],
                {"screenshot_path": f"{source_id}.png", "live_dom_path": f"{source_id}.json"},
                None,
            )

        def reextract_detail(self, request_id):
            return details[request_id]

    effects = [Effects(source, timeout=index == 2) for index, source in enumerate(required)]
    collector = parent.CdpSnapshotCollector(
        Effects("writer"),
        pass_id="timeout-partial",
        objective={
            "target_applications": 1,
            "max_applications": 20,
            "required_search_source_ids": required,
        },
        discovery_effect_factory=lambda index: contextlib.nullcontext(effects[index]),
        discovery_timeout_seconds=0.01,
    )

    result = collector.collect({"task": "test", "token": "0" * 32, "generation": 1})

    assert {row["source_id"] for row in result["search_sources"]} == set(required) - {required[2]}
    assert {row["request_id"] for row in result["request_details"]} == {
        detail_ids[source] for source in required if source != required[2]
    }
    assert set(result["objective"]["required_search_source_ids"]) == set(required) - {required[2]}
    assert parent.snapshot_contract.validate_snapshot(result) == []
    assert collector.discovery_failures == {2: "TimeoutError:discovery shard deadline"}


def _live_program() -> list[str]:
    """The shape b2_result_gate freezes: newest first, categories, keyword last."""
    return [
        "single:new",
        *(f"single:category:カテゴリ{index}" for index in range(85)),
        "single:keyword",
    ]


class _Effects:
    """A market that always has more listings than we are willing to take."""

    def __init__(self, applied: list[str] | None = None, per_source: int = 40) -> None:
        self.applied = applied or []
        self.per_source = per_source
        self.requests: list[tuple[str, int]] = []
        self.urls: list[tuple[str, str]] = []

    def target_lock(self):
        return contextlib.nullcontext()

    def official_ids_for_snapshot(self):
        return list(self.applied)

    def collect_source(self, source_id, url, remaining):
        self.requests.append((source_id, remaining))
        self.urls.append((source_id, url))
        offset = abs(hash(source_id)) % 900
        ids = [f"{9000 + offset * 100 + index}" for index in range(self.per_source)]
        selected = ids[: max(0, remaining)]
        return (
            {
                "source_id": source_id,
                "url": url,
                "card_request_ids": selected,
                "has_next": True,
                "exhausted": False,
                "screenshot_sha256": "a" * 64,
                "dom_sha256": "b" * 64,
            },
            selected,
            {"screenshot_path": f"{source_id}.png", "live_dom_path": f"{source_id}.json"},
            None,
        )

    def reextract_detail(self, request_id):
        return {"request_id": request_id}


def _collect(parent, monkeypatch, effects, program, excluded=None, **extra):
    monkeypatch.setattr(parent.snapshot_contract, "build_envelope", lambda value: value)
    return parent.CdpSnapshotCollector(
        effects,
        pass_id="pass-allocation",
        objective={"required_search_source_ids": program},
        excluded_request_ids=excluded,
        **extra,
    ).collect({"lease_id": "test"})


# --- read-only discovery shards ---------------------------------------------------


class _ShardEffects:
    def __init__(self, _sources, details, *, request_ids=None, barrier=None, failure=None):
        self.details = details
        self.request_ids = list(request_ids) if request_ids is not None else None
        self.barrier = barrier
        self.failure = failure
        self.urls = []

    def target_lock(self):
        return contextlib.nullcontext()

    def official_ids_for_snapshot(self):
        return []

    def collect_source(self, source_id, url, remaining):
        if self.failure is not None:
            raise self.failure
        self.urls.append((source_id, url))
        if self.barrier is not None:
            self.barrier.wait(timeout=3)
        request_ids = (
            list(self.request_ids)
            if self.request_ids is not None
            else [request_id for request_id in self.details if request_id.startswith(source_id)]
        )
        request_ids = request_ids[: max(0, remaining)]
        return (
            {
                "source_id": source_id,
                "url": url,
                "page_index": 1,
                "card_request_ids": request_ids,
                "has_next": False,
                "exhausted": True,
                "screenshot_sha256": "a" * 64,
                "dom_sha256": "b" * 64,
            },
            request_ids,
            {"screenshot_path": f"{source_id}.png", "live_dom_path": f"{source_id}.json"},
            None,
        )

    def reextract_detail(self, request_id):
        return self.details[request_id]


def _shard_factory(effects_by_index):
    return lambda index: contextlib.nullcontext(effects_by_index[index])


def _shard_detail(request_id, *, budget=None, text=None):
    return {
        "request_id": request_id,
        "canonical_url": f"https://coconala.com/requests/{request_id.split(':')[-1]}",
        "title": f"title-{request_id}",
        "category": "software",
        "visible_text": text or f"内容 {request_id}",
        "accepting_applications": True,
        "budget_min_jpy": budget,
        "budget_max_jpy": budget,
        "applicants_count": 0,
        "contracted_count": 0,
        "observed_at": "2026-08-10T00:00:00Z",
    }


def _shard_lifecycle_detail(parent, request_id, *, page_state="present", accepting_control="present", deadline_state="future", deadline_value="2026-08-20", form_state="present"):
    detail = _shard_detail(request_id)
    detail.update(page_state=page_state, accepting_control=accepting_control, deadline_state=deadline_state, deadline_value=deadline_value, form_state=form_state)
    detail["lifecycle_sha256"] = parent._lifecycle_digest(request_id, detail["canonical_url"], **{field: detail[field] for field in parent._LIFECYCLE_FIELDS})
    return detail


def _collect_shards(parent, monkeypatch, effects, required, *, pass_id="shard", objective=None, cursor=None, builder=None, lease_fence=None):
    monkeypatch.setattr(parent.snapshot_contract, "build_envelope", builder or (lambda value: value))
    return parent.CdpSnapshotCollector(
        _ShardEffects([], {}), pass_id=pass_id,
        objective=objective or {"required_search_source_ids": required},
        discovery_effect_factory=_shard_factory(effects),
    ).collect(lease_fence or {"lease_id": "test"}, cursor_contract=cursor)


def test_required_sources_are_round_robin_partitioned_exactly_once() -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_shard_partition")
    required = [f"source-{index}" for index in range(99)]

    shards = parent._partition_required_sources(required, shard_count=4)

    assert shards == [required[index::4] for index in range(4)]
    assert sorted(source for shard in shards for source in shard) == sorted(required)
    assert len({source for shard in shards for source in shard}) == len(required)


def test_cursor_selects_only_its_source_and_uses_one_discovery_shard(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_shard_cursor")
    required = ["single:new", "single:keyword", "single:category:資料", "single:category:業務"]
    selected_source = required[2]
    details = {
        selected_source: _shard_detail(f"{selected_source}:1")
    }
    effects = [_ShardEffects([selected_source], details)]
    cursor = {
        "source_id": selected_source,
        "previous_url": "https://coconala.com/requests?keyword=%E8%B3%87%E6%96%99&recruiting=true",
        "next_url": "https://coconala.com/requests?keyword=%E8%B3%87%E6%96%99&page=2&recruiting=true",
    }
    result = _collect_shards(parent, monkeypatch, effects, required, pass_id="cursor-shard", cursor=cursor)

    assert effects[0].urls == [(selected_source, cursor["next_url"])]
    assert result["objective"]["required_search_source_ids"] == [selected_source]
    assert [row["source_id"] for row in result["search_sources"]] == [selected_source]


def test_large_cursor_objective_collects_exactly_one_source(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_large_cursor")
    required = ["single:new", *(f"single:category:cat-{index}" for index in range(103))]
    selected_source = required[57]
    details = {selected_source: _shard_detail(f"{selected_source}:1")}
    effects = [_ShardEffects([selected_source], details)]
    cursor = {
        "source_id": selected_source,
        "previous_url": "https://coconala.com/requests?keyword=cat-56&recruiting=true",
        "next_url": "https://coconala.com/requests?keyword=cat-56&page=2&recruiting=true",
    }

    result = _collect_shards(
        parent, monkeypatch, effects, required, pass_id="large-cursor", cursor=cursor,
    )

    assert len(required) == 104
    assert effects[0].urls == [(selected_source, cursor["next_url"])]
    assert result["objective"]["required_search_source_ids"] == [selected_source]
    assert [row["source_id"] for row in result["search_sources"]] == [selected_source]


def test_shards_execute_concurrently_with_independent_effect_instances(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_shard_concurrency")
    required = [f"single:category:cat-{index}" for index in range(4)]
    barrier = threading.Barrier(4)
    details = {
        f"{source}:1": _shard_detail(f"{source}:1")
        for source in required
    }
    effects = [
        _ShardEffects(shard, details, barrier=barrier)
        for shard in parent._partition_required_sources(required, shard_count=4)
    ]
    result = _collect_shards(parent, monkeypatch, effects, required, pass_id="concurrent-shard")

    assert [row["source_id"] for row in result["search_sources"]] == required
    assert all(effect.urls for effect in effects)
    assert len({id(effect) for effect in effects}) == 4


def test_overlapping_request_ids_dedupe_globally_but_hash_conflict_fails_closed(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_shard_identity")
    required = ["single:category:left", "single:category:right"]
    shared = "123450"
    same = {**_shard_detail(shared, text="same"), "content_sha256": "a" * 64}
    left = _ShardEffects(required[:1], {shared: same}, request_ids=[shared])
    right = _ShardEffects(required[1:], {shared: same}, request_ids=[shared])
    empty_effects = [_ShardEffects([], {}) for _ in range(2)]
    result = _collect_shards(
        parent, monkeypatch, [left, right, *empty_effects], required, pass_id="dedupe-shard"
    )
    assert [detail["request_id"] for detail in result["request_details"]] == [shared]

    conflicting = _ShardEffects(
        required[1:],
        {shared: {**_shard_detail(shared, text="changed"), "content_sha256": "b" * 64}},
        request_ids=[shared],
    )
    with pytest.raises(parent.ParentContractError, match="shard_request_id_conflict"):
        _collect_shards(
            parent, monkeypatch, [left, conflicting, *empty_effects], required,
            pass_id="conflict-shard",
        )


def test_shard_non_open_lifecycle_removes_shared_id_but_keeps_later_request(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_shard_lifecycle_bulkhead")
    required = ["single:category:left", "single:category:right"]
    shared, later = "123480", "123481"
    left = _ShardEffects(required[:1], {shared: _shard_lifecycle_detail(parent, shared)}, request_ids=[shared])
    right = _ShardEffects(
        required[1:],
        {
            shared: _shard_lifecycle_detail(parent, shared, page_state="not_found", accepting_control="absent", deadline_state="unknown", deadline_value=None, form_state="unknown"),
            later: _shard_lifecycle_detail(parent, later),
        },
        request_ids=[shared, later],
    )
    result = _collect_shards(parent, monkeypatch, [left, right, _ShardEffects([], {}), _ShardEffects([], {})], required, pass_id="lifecycle-bulkhead")

    assert [detail["request_id"] for detail in result["request_details"]] == [later]


def test_duplicate_request_id_is_owned_by_first_source_with_real_envelope(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_shard_real_envelope")
    required = ["single:category:left", "single:category:right"]
    shared = "123456"
    detail = _shard_detail(shared, text="same")
    effects = [
        _ShardEffects(required[0:1], {shared: detail}, request_ids=[shared]),
        _ShardEffects(required[1:2], {shared: detail}, request_ids=[shared]),
        _ShardEffects([], {}), _ShardEffects([], {}),
    ]
    result = _collect_shards(
        parent, monkeypatch, effects, required, pass_id="real-envelope",
        objective={"target_applications": 1, "max_applications": 20, "required_search_source_ids": required},
        lease_fence={"task": "test", "token": "0" * 32, "generation": 1},
        builder=parent.snapshot_contract.build_envelope,
    )

    assert result["search_sources"][0]["card_request_ids"] == [shared]
    assert result["search_sources"][1]["card_request_ids"] == []


def test_duplicate_request_id_with_unparseable_detail_fails_closed(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_shard_malformed")
    required = ["single:category:left", "single:category:right"]
    shared = "123457"
    valid = _shard_detail(shared, text="same")
    malformed = {**valid, "visible_text": ""}
    effects = [
        _ShardEffects(required[0:1], {shared: valid}, request_ids=[shared]),
        _ShardEffects(required[1:2], {shared: malformed}, request_ids=[shared]),
        _ShardEffects([], {}), _ShardEffects([], {}),
    ]

    with pytest.raises(parent.ParentContractError, match="shard_request_detail_invalid"):
        _collect_shards(parent, monkeypatch, effects, required, pass_id="malformed")


def test_unique_low_rank_malformed_detail_is_rejected_before_global_trim(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_shard_low_rank_malformed")
    required = [f"single:category:cat-{index}" for index in range(4)]
    effects = []
    for source_index, source in enumerate(required):
        request_ids = [str(200000 + source_index * 100 + index) for index in range(40)]
        details = {
            request_id: _shard_detail(request_id, budget=100000)
            for request_id in request_ids
        }
        if source_index == 0:
            details[request_ids[-1]] = {
                **details[request_ids[-1]],
                "visible_text": "",
                "budget_min_jpy": None,
                "budget_max_jpy": None,
            }
        effects.append(_ShardEffects([source], details, request_ids=request_ids))

    with pytest.raises(parent.ParentContractError):
        _collect_shards(
            parent,
            monkeypatch,
            effects,
            required,
            pass_id="low-rank-malformed",
            objective={
                "target_applications": 1,
                "max_applications": 20,
                "required_search_source_ids": required,
            },
            lease_fence={
                "task": "low-rank-malformed",
                "token": "0" * 32,
                "generation": 1,
            },
            builder=parent.snapshot_contract.build_envelope,
        )


def test_shared_discovery_effect_instance_fails_closed(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_shard_shared_effect")
    required = [f"single:category:cat-{index}" for index in range(4)]
    details = {
        f"{source}:1": _shard_detail(f"{source}:1")
        for source in required
    }
    shared = _ShardEffects(required, details)
    built = []

    with pytest.raises(
        parent.ParentContractError, match="discovery_effect_instance_shared"
    ):
        _collect_shards(
            parent,
            monkeypatch,
            [shared, shared, shared, shared],
            required,
            pass_id="shared-effect",
            builder=lambda value: built.append(value) or value,
        )

    assert built and all(len(value["search_sources"]) == 1 for value in built)


def test_live_discovery_factory_isolated_and_releases_on_body_error(monkeypatch, tmp_path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_live_factory")
    leases = []
    effects = []

    class FakeLease:
        def __init__(self, *, lease_script, task, heartbeat_seconds):
            self.task, self.ws_url, self.releases, self.health_checks = task, f"ws://{task}", 0, 0
            leases.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.releases += 1

        def assert_healthy(self):
            self.health_checks += 1
            if "heartbeat-fail" in self.task:
                raise parent.ParentContractError("lease_heartbeat_failed")

    class FakeEffects:
        def __init__(self, *, ws_url, evidence_dir, ledger_path, pass_id):
            self.ws_url, self.evidence_dir, self.ledger_path, self.pass_id = (
                ws_url, evidence_dir, ledger_path, pass_id
            )
            effects.append(self)

    monkeypatch.setattr(parent, "LeaseHandle", FakeLease)
    monkeypatch.setattr(parent, "CdpParentEffects", FakeEffects)
    factory = parent._readonly_discovery_effect_factory(
        lease_script=tmp_path / "lease.py", lease_task="gig", evidence_dir=tmp_path / "evidence",
        ledger_path=tmp_path / "ledger", pass_id="pass", heartbeat_seconds=7,
    )

    with factory(0) as first, factory(1) as second:
        assert first.pass_id == "pass-discovery-0"
        assert second.pass_id == "pass-discovery-1"
        assert first.evidence_dir != second.evidence_dir
        assert [lease.task for lease in leases] == ["gig-discovery-0", "gig-discovery-1"]

    for index in (2, 3):
        with pytest.raises(RuntimeError, match="body"):
            with factory(index):
                raise RuntimeError("body")
    assert [lease.releases for lease in leases] == [1, 1, 1, 1]
    assert [lease.health_checks for lease in leases] == [1, 1, 0, 0]

    failing_factory = parent._readonly_discovery_effect_factory(
        lease_script=tmp_path / "lease.py", lease_task="gig-heartbeat-fail", evidence_dir=tmp_path / "evidence",
        ledger_path=tmp_path / "ledger", pass_id="pass", heartbeat_seconds=7,
    )
    with pytest.raises(parent.ParentContractError, match="lease_heartbeat_failed"):
        with failing_factory(0):
            pass
    assert leases[-1].releases == 1


def test_lease_enter_rolls_back_malformed_and_thread_start_failures(monkeypatch, tmp_path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_lease_enter_transaction")

    class FailingThread:
        def start(self):
            raise RuntimeError("thread start failed")

        def join(self, timeout):
            return None

    def exercise(task, acquired, thread, expected_release):
        lease = parent.LeaseHandle(
            lease_script=tmp_path / "unused.py",
            task=task,
            heartbeat_seconds=1,
        )
        calls = []

        def fake_run(*arguments):
            calls.append(arguments)
            if arguments[0] == "acquire":
                return acquired
            raise RuntimeError("rollback failed")

        monkeypatch.setattr(lease, "_run", fake_run)
        if thread is not None:
            monkeypatch.setattr(parent.threading, "Thread", lambda **_kwargs: thread)
        expected_error = RuntimeError if thread is not None else parent.ParentContractError
        with pytest.raises(expected_error):
            lease.__enter__()
        assert lease.value is None
        assert lease._thread is None
        assert lease._stop.is_set()
        assert calls == [("acquire", task), expected_release]

    exercise(
        "malformed",
        {"ok": True, "ws": "bad", "token": "bad", "generation": "bad"},
        None,
        ("release", "malformed"),
    )
    exercise(
        "start-fail",
        {"ok": True, "ws": "ws://leased", "token": "a" * 32, "generation": 9},
        FailingThread(),
        ("release", "start-fail", "--token", "a" * 32, "--generation", "9"),
    )


def test_lease_exit_checks_late_heartbeat_after_join_and_releases_once(monkeypatch, tmp_path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_late_heartbeat")
    lease = parent.LeaseHandle(
        lease_script=tmp_path / "unused-lease.py",
        task="late-heartbeat",
        heartbeat_seconds=1,
    )
    lease.value = {
        "token": "0" * 32,
        "generation": 1,
        "ws": "ws://late-heartbeat",
    }
    release_calls = []

    def run(*arguments):
        release_calls.append(arguments)
        return {"ok": True}

    class JoiningThread:
        def join(self, timeout):
            lease._heartbeat_error = "RuntimeError:late"

        def is_alive(self):
            return False

    monkeypatch.setattr(lease, "_run", run)
    lease._thread = JoiningThread()

    with pytest.raises(parent.ParentContractError, match="lease_heartbeat_failed"):
        lease.__exit__(None, None, None)
    assert [arguments[0] for arguments in release_calls] == ["release"]


def test_lease_exit_fails_closed_when_heartbeat_thread_stays_alive(monkeypatch, tmp_path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_stuck_heartbeat")
    lease = parent.LeaseHandle(
        lease_script=tmp_path / "unused-lease.py",
        task="stuck-heartbeat",
        heartbeat_seconds=1,
    )
    lease.value = {
        "token": "0" * 32,
        "generation": 1,
        "ws": "ws://stuck-heartbeat",
    }
    release_calls = []

    monkeypatch.setattr(
        lease,
        "_run",
        lambda *arguments: release_calls.append(arguments) or {"ok": True},
    )

    class StuckThread:
        def join(self, timeout):
            return None

        def is_alive(self):
            return True

    lease._thread = StuckThread()

    with pytest.raises(parent.ParentContractError, match="lease_heartbeat_thread_stuck"):
        lease.__exit__(None, None, None)
    assert [arguments[0] for arguments in release_calls] == ["release"]


def test_one_shard_failure_returns_no_partial_snapshot(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_shard_failure")
    required = [f"single:category:cat-{index}" for index in range(4)]
    details = {f"{source}:1": _shard_detail(f"{source}:1") for source in required}
    effects = [
        _ShardEffects(shard, details, failure=RuntimeError("shard failed"))
        if index == 2
        else _ShardEffects(shard, details)
        for index, shard in enumerate(parent._partition_required_sources(required, shard_count=4))
    ]
    built = []

    def fail_if_built(value):
        built.append(value)
        return value

    with pytest.raises(RuntimeError, match="shard failed"):
        _collect_shards(parent, monkeypatch, effects, required, pass_id="failed-shard", builder=fail_if_built)
    assert built and all(len(value["search_sources"]) == 1 for value in built)


def test_merged_details_are_high_ticket_first_and_trimmed_to_max_batch(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_shard_rank")
    required = [f"single:category:cat-{index}" for index in range(4)]
    detail_map = {}
    source_request_ids = []
    for source_index, source in enumerate(required):
        ids_for_source = []
        for detail_index in range(15):
            request_id = str(100_000 + source_index * 100 + detail_index)
            ids_for_source.append(request_id)
            detail_map[request_id] = _shard_detail(
                request_id,
                budget=300_000 if detail_index == 0 else 1_000 + source_index,
            )
        source_request_ids.append(ids_for_source)
    effects = [
        _ShardEffects(shard, detail_map, request_ids=source_request_ids[index])
        for index, shard in enumerate(parent._partition_required_sources(required, shard_count=4))
    ]
    result = _collect_shards(
        parent, monkeypatch, effects, required, pass_id="rank-shard",
        objective={"target_applications": 1, "max_applications": 20, "required_search_source_ids": required},
        lease_fence={"task": "test", "token": "0" * 32, "generation": 1},
        builder=parent.snapshot_contract.build_envelope,
    )

    assert len(result["request_details"]) == parent.snapshot_contract.MAX_BATCH
    assert all(parent._known_budget(detail) is not None for detail in result["request_details"][:4])
    assert result["request_details"][0]["budget_max_jpy"] == 300_000
    assert parent.snapshot_contract.validate_snapshot(result) == []


_PAGE4_CURSOR = {"source_id": "single:new", "previous_url": "https://coconala.com/requests?sort=new&recruiting=true&page=3", "next_url": "https://coconala.com/requests?sort=new&recruiting=true&page=4", "reason": "next_page"}

def test_parent_cursor_selects_one_source_and_no_cursor_keeps_page_one(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_source_cursor")
    canonical = "https://coconala.com/requests?sort=new&recruiting=true"
    cases = [(_PAGE4_CURSOR, [("single:new", f"{canonical}&page=4"), ("single:keyword", "https://coconala.com/requests?keyword=AI&recruiting=true")]), (dict(_PAGE4_CURSOR, previous_url=canonical, next_url=f"{canonical}&page=2"), [("single:new", f"{canonical}&page=2"), ("single:keyword", "https://coconala.com/requests?keyword=AI&recruiting=true")]), (None, [("single:new", canonical), ("single:keyword", "https://coconala.com/requests?keyword=AI&recruiting=true")])]
    for cursor, urls in cases:
        effects = _Effects()
        _collect(parent, monkeypatch, effects, ["single:new", "single:keyword"], cursor_contract=cursor)
        assert effects.urls == urls


def test_parent_cursor_skips_ids_already_inspected_in_the_same_wake(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_cursor_prior_ids")
    first = _collect(parent, monkeypatch, _Effects(per_source=4), ["single:new"])
    prior_ids = [row["request_id"] for row in first["request_details"][:2]]

    continued = _collect(
        parent,
        monkeypatch,
        _Effects(per_source=4),
        ["single:new"],
        cursor_contract={**_PAGE4_CURSOR, "prior_inspected_request_ids": prior_ids},
    )

    continued_ids = {row["request_id"] for row in continued["request_details"]}
    assert set(prior_ids).isdisjoint(continued_ids)
    assert len(continued_ids) == 2

@pytest.mark.parametrize(
    "cursor",
    [dict(_PAGE4_CURSOR, source_id="single:missing"), dict(_PAGE4_CURSOR, next_url="https://coconala.com/requests?sort=old&page=4")],
    ids=["absent-source", "stable-query-drift"],
)
def test_parent_cursor_rejects_invalid_scope_before_collection(monkeypatch, cursor) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_source_cursor_reject")
    effects = _Effects()

    with pytest.raises(parent.ParentContractError):
        _collect(parent, monkeypatch, effects, ["single:new", "single:keyword"], cursor_contract=cursor)
    assert effects.urls == []

def test_parent_run_cli_exposes_the_cursor_contract_file() -> None:
    assert "--cursor-contract" in PARENT_SCRIPT.read_text(encoding="utf-8")

def test_run_parent_b2_passes_cursor_to_both_attempts_and_checkpoints_before_continuation() -> None:
    source = GIG_PASS_SCRIPT.read_text(encoding="utf-8"); start = source.index("run_parent_b2()"); source = source[start : source.index("\nb2_policy_skip_reason()", start)]
    assert source.count('application_parent.py" run') == 2
    assert 'if [ -n "$B2_CURSOR_CONTRACT" ]; then' in source
    assert '--cursor-contract "$B2_CURSOR_CONTRACT"' in source
    assert "cursor_args=()" in source and source.count("cursor_args[@]") >= 2
    checkpoint_call = 'b2_search_objective.py" checkpoint'
    assert 'b2_result_gate.py" next-cursor' in source and source.count(checkpoint_call) >= 1
    checkpoint_at = source.index("b2_checkpoint_cursor || return 1")
    assert checkpoint_at < source.index("return 3", checkpoint_at)


def test_run_parent_final_readback_uses_the_shared_confirmed_statuses() -> None:
    source = PARENT_SCRIPT.read_text(encoding="utf-8")
    start = source.index("def run_parent(")
    end = source.index("\ndef runner_failure_detail", start)
    assert 'result.get("status") in CONFIRMED_STATUSES' in source[start:end]


# --- depth allocation -------------------------------------------------------------


def test_batch_depth_goes_to_the_newest_source_not_to_whoever_sorts_last() -> None:
    """List position must stop deciding who gets to read past the first listing.

    Under the old rule the final source received MAX_BATCH minus everything spent, so
    single:keyword -- last in the frozen program -- took 563 of 1785 observations across
    36 passes and produced zero applications ever, while single:new was pinned at one
    listing a pass and produced 6 of the 26 confirmations.
    """
    parent = _load(PARENT_SCRIPT, "application_parent_depth_plan")
    plan = parent._source_capacity_plan(
        _live_program(), batch=parent.snapshot_contract.MAX_BATCH
    )

    assert plan["single:new"] == 20
    assert plan["single:keyword"] == 1
    assert plan["single:category:カテゴリ0"] == 1


def test_every_required_source_keeps_a_floor_of_one_listing() -> None:
    """Depth is reallocated, never at the price of a source going unread."""
    parent = _load(PARENT_SCRIPT, "application_parent_depth_floor")
    program = _live_program()
    plan = parent._source_capacity_plan(program, batch=parent.snapshot_contract.MAX_BATCH)

    assert set(plan) == set(program)
    assert min(plan.values()) >= 1


def test_a_program_that_fits_inside_the_batch_fills_it_exactly() -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_depth_fits")
    batch = parent.snapshot_contract.MAX_BATCH
    plan = parent._source_capacity_plan(
        ["single:new", "single:category:A", "single:keyword"], batch=batch
    )

    assert sum(plan.values()) == batch
    assert plan["single:new"] == batch - 2


def test_the_batch_never_exceeds_the_contract_and_still_observes_every_source(
    monkeypatch,
) -> None:
    """A full batch is a full batch, not an unobserved source.

    Sources reached after the batch fills are still loaded and reported; they simply
    contribute no rows. Raising source_not_observed for them would fail a pass that did
    exactly what it was asked to do.
    """
    parent = _load(PARENT_SCRIPT, "application_parent_depth_clamp")
    effects = _Effects()
    program = _live_program()
    result = _collect(parent, monkeypatch, effects, program)

    assert len(result["request_details"]) == parent.snapshot_contract.MAX_BATCH
    assert [row["source_id"] for row in result["search_sources"]] == program
    assert [name for name, _ in effects.requests] == program
    assert effects.requests[0] == ("single:new", 20)
    assert effects.requests[-1][1] == 0


# --- quarantine exclusion ---------------------------------------------------------


def test_quarantined_requests_never_reach_the_batch(monkeypatch) -> None:
    """13 request_ids produced 120 quarantine events over 36 passes; one of them,
    95000014, was collected, judged eligible and refused in 29 consecutive passes."""
    parent = _load(PARENT_SCRIPT, "application_parent_quarantine_batch")
    effects = _Effects(per_source=4)
    program = ["single:new", "single:keyword"]
    open_result = _collect(parent, monkeypatch, effects, program)
    poisoned = {open_result["request_details"][0]["request_id"]}

    guarded = _collect(
        parent, monkeypatch, _Effects(per_source=4), program, excluded=poisoned
    )
    collected = {row["request_id"] for row in guarded["request_details"]}

    assert poisoned & {row["request_id"] for row in open_result["request_details"]}
    assert not (poisoned & collected)


def test_a_quarantined_request_is_not_reported_as_already_applied(monkeypatch) -> None:
    """We refused it; we did not apply to it. The envelope must not claim otherwise."""
    parent = _load(PARENT_SCRIPT, "application_parent_quarantine_envelope")
    effects = _Effects(applied=["5000"], per_source=4)
    result = _collect(
        parent, monkeypatch, effects, ["single:new"], excluded={"95000014"}
    )

    assert "95000014" not in set(result["already_applied_ids"])
    assert "5000" in set(result["already_applied_ids"])


def test_quarantined_ids_are_read_from_the_store_the_commit_boundary_writes(
    tmp_path,
) -> None:
    """One file, one meaning: the collector must refuse exactly what commit refuses.

    Live-lineage adaptation (§FK'): the store is dict-form with a 48h TTL, and the
    collector reads it through the SAME loader the commit boundary uses -- so an entry
    the TTL has ended (or a legacy bare-int with no timestamp) stops excluding the
    request from collection at the same moment it stops blocking the commit.
    """
    import time as time_module

    parent = _load(PARENT_SCRIPT, "application_parent_quarantine_store")
    threshold = parent.WEDGE_QUARANTINE_THRESHOLD
    now = time_module.time()
    (tmp_path / "wedge-quarantine.json").write_text(
        json.dumps({
            "95000014": {"count": threshold, "updated_at": now},
            "95000016": {"count": threshold - 1, "updated_at": now},
            "95000012": {
                "count": threshold,
                "updated_at": now - parent.WEDGE_QUARANTINE_TTL_SECONDS - 1,
            },
        }),
        encoding="utf-8",
    )

    # At-threshold fresh entry excluded; below-threshold and TTL-expired ones are not.
    assert parent.quarantined_request_ids(tmp_path) == {"95000014"}
    assert parent.quarantined_request_ids(tmp_path / "absent") == set()


# --- corpse skip-fast (T3, §FJ' item 1/§FH') --------------------------------------


class _CorpseAwareEffects:
    """Page one of the source is entirely closed listings; page two is entirely open.

    Whether a listing is still accepting applications is only knowable after the
    per-candidate detail reextract, so page one's load already happened by the time
    that is known -- but the planner call has not, and it is the scarcer resource.
    """

    def __init__(self) -> None:
        self.calls = 0

    def target_lock(self):
        return contextlib.nullcontext()

    def official_ids_for_snapshot(self):
        return []

    def collect_source(self, source_id, url, remaining):
        self.calls += 1
        if self.calls == 1:
            ids = [f"9500000{index}" for index in range(5)]
            return (
                {
                    "source_id": source_id,
                    "url": url,
                    "card_request_ids": ids,
                    "has_next": True,
                    "exhausted": False,
                    "screenshot_sha256": "a" * 64,
                    "dom_sha256": "b" * 64,
                },
                ids,
                {"screenshot_path": "p1.png", "live_dom_path": "p1.json"},
                "https://coconala.com/requests?sort=new&page=2",
            )
        ids = [f"9600000{index}" for index in range(5)]
        return (
            {
                "source_id": source_id,
                "url": url,
                "card_request_ids": ids,
                "has_next": False,
                "exhausted": True,
                "screenshot_sha256": "a" * 64,
                "dom_sha256": "b" * 64,
            },
            ids,
            {"screenshot_path": "p2.png", "live_dom_path": "p2.json"},
            None,
        )

    def reextract_detail(self, request_id):
        # 95xxxxxx is the closed (募集終了) fixture bucket, 96xxxxxx is open.
        return {
            "request_id": request_id,
            "accepting_applications": not request_id.startswith("95"),
        }


def test_closed_listings_do_not_consume_capacity_or_reach_the_planner(monkeypatch) -> None:
    """A page that is entirely 募集終了 must not stop the read there or spend a slot.

    Measured 2026-08-09 (§FJ'): ~45% of inspected candidates per pass were already
    closed or already-applied, eating a planner judgment slot each. Already-applied is
    filtered before the page load (`skipped`); this closes the other half -- a closed
    id is dropped after its unavoidable detail reextract instead of being handed to
    build_envelope, and the source is read one page deeper to compensate.
    """
    parent = _load(PARENT_SCRIPT, "application_parent_corpse_skip")
    effects = _CorpseAwareEffects()
    result = _collect(parent, monkeypatch, effects, ["single:new"])

    collected_ids = {row["request_id"] for row in result["request_details"]}
    assert not any(rid.startswith("95") for rid in collected_ids)
    assert collected_ids == {f"9600000{index}" for index in range(5)}
    assert effects.calls == 2, "five closed ids on page one must not have looked full"


def test_direct_cursor_returns_after_one_page_and_preserves_next_page(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_cursor_page_budget")
    effects = _CorpseAwareEffects()
    canonical = "https://coconala.com/requests?sort=new&recruiting=true"

    result = _collect(
        parent,
        monkeypatch,
        effects,
        ["single:new"],
        cursor_contract={"source_id": "single:new", "next_url": canonical},
    )

    assert effects.calls == 1
    assert result["request_details"] == []
    assert result["search_sources"][0]["has_next"] is True
    assert result["search_sources"][0]["exhausted"] is False


# --- value ranking (T3, §FJ' item 3/§FH') ------------------------------------------


class _RankedEffects:
    """One page, three candidates with distinct client_order_rate/budget."""

    _MARKET = {
        "9500001": {"client_order_rate": 20, "budget_max_jpy": 100000},
        "9500002": {"client_order_rate": None, "budget_max_jpy": 999999},
        "9500003": {"client_order_rate": 58, "budget_max_jpy": 5000},
    }

    def __init__(self, market=None):
        self.market = self._MARKET if market is None else market

    def target_lock(self):
        return contextlib.nullcontext()

    def official_ids_for_snapshot(self):
        return []

    def collect_source(self, source_id, url, remaining):
        ids = list(self.market)
        return (
            {
                "source_id": source_id,
                "url": url,
                "card_request_ids": ids,
                "has_next": False,
                "exhausted": True,
                "screenshot_sha256": "a" * 64,
                "dom_sha256": "b" * 64,
            },
            ids,
            {"screenshot_path": "p.png", "live_dom_path": "p.json"},
            None,
        )

    def reextract_detail(self, request_id):
        return {
            "request_id": request_id,
            "accepting_applications": True,
            **self.market[request_id],
        }


def test_high_value_queue_keeps_all_candidates_and_applies_contract_tie_breaks(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_high_value_queue")
    cases = [
        (_RankedEffects._MARKET, ["9500002", "9500001", "9500003"]),
        ({"9500010": {"client_order_rate": 58, "budget_min_jpy": None, "budget_max_jpy": None, "title": "一般相談", "category": "その他"}, "9500011": {"client_order_rate": 1, "budget_min_jpy": None, "budget_max_jpy": None, "title": "業務システム構築", "category": "システム開発"}}, ["9500010", "9500011"]),
        ({"9500020": {"budget_max_jpy": 200000, "client_order_rate": 1, "applicants_count": 99}, "9500021": {"budget_max_jpy": 100000, "client_order_rate": 20, "applicants_count": 1}, "9500022": {"budget_max_jpy": 100000, "client_order_rate": 58, "applicants_count": 9}, "9500023": {"budget_max_jpy": 100000, "client_order_rate": 58, "applicants_count": 2}, "9500024": {"budget_max_jpy": 100000, "client_order_rate": 58, "applicants_count": 2}}, ["9500020", "9500024", "9500023", "9500022", "9500021"]),
    ]
    for index, (market, expected) in enumerate(cases):
        result = _collect(parent, monkeypatch, _RankedEffects(market), ["single:new"])
        ids = [row["request_id"] for row in result["request_details"]]
        assert ids == expected
        if index == 1:
            assert set(ids) == set(market)
            assert all(not parent._queue_a(detail) for detail in market.values())


def test_planner_semantic_priority_order_controls_the_bounded_submit_queue(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_semantic_priority_order")
    snapshot = _nine_candidate_snapshot(parent, cap=1, count=2)
    decisions = _nine_eligible_decisions(snapshot)
    decisions["decisions"].reverse()
    priority_id = decisions["decisions"][0]["request_id"]
    effects = parent.FixtureEffects(snapshot, {"official_applied_ids": [priority_id]})

    results = parent.commit_decisions(
        snapshot,
        decisions,
        store=parent.fence.IntentStore(tmp_path / "priority-intents"),
        effects=effects,
    )

    assert results[0]["request_id"] == priority_id
    assert results[0]["status"] == "confirmed"
    assert results[1]["status"] == "cap_reached"


def test_known_budget_maximum_rejects_an_overpriced_eligible_decision() -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_budget_guard")
    snapshot = parent.snapshot_contract.build_envelope({
        "pass_id": "pricing-budget-guard", "lease_fence": {"task": "pricing-budget-guard", "token": "0123456789abcdef0123456789abcdef", "generation": 1}, "observed_at": "2026-08-10T00:00:00Z",
        "objective": {"target_applications": 1, "max_applications": 1, "required_search_source_ids": ["single:new"]},
        "search_sources": [{"source_id": "single:new", "url": "https://coconala.com/requests?sort=new", "page_index": 1, "card_request_ids": ["97000001"], "has_next": False, "exhausted": True, "screenshot_sha256": "a" * 64, "dom_sha256": "b" * 64}],
        "request_details": [{"request_id": "97000001", "canonical_url": "https://coconala.com/requests/97000001", "title": "AI調査", "category": "コード", "visible_text": "募集内容\n詳細", "accepting_applications": True, "budget_min_jpy": 10000, "budget_max_jpy": 10000, "applicants_count": 0, "contracted_count": 0, "observed_at": "2026-08-10T00:00:00Z"}], "already_applied_ids": [],
    })
    errors = parent.validate_decisions(snapshot, {"decisions": [{"request_id": "97000001", "business_class": "submit_required", "reason_codes": [], "proposal_text": "ご依頼の内容、対応可能です。" * 20, "price_jpy": 10001, "deliver_date": "2026-08-11"}]})
    assert any("budget_max" in error for error in errors), errors


def test_submit_required_rejects_an_impossible_calendar_date() -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_calendar_date_guard")
    snapshot = _planner_snapshot(
        parent,
        title="採用サイト制作",
        category="Web制作",
        visible_text="募集内容\n採用サイトを制作してください",
        budget_max=200000,
    )
    decision = _eligible_decision(price_jpy=180000)
    decision["deliver_date"] = "2108-21-21"

    errors = parent.validate_decisions(snapshot, {"decisions": [decision]})

    assert "decision[0]_submit_required_date_invalid" in errors


def test_stable_request_text_keeps_official_qa_but_drops_applicants_and_related_jobs() -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_official_qa_context")
    text = parent.snapshot_contract.stable_request_text(
        "ページ見出し\n募集内容\n依頼本文\n応募者一覧\n応募者A\n"
        "募集内容についての質問\n売り手\n音声は必要ですか\n買い手\nプレイ中はボイスチャット必須です\n"
        "応募する\n募集者情報\nこの募集内容に似ている仕事\n動画編集"
    )

    assert "依頼本文" in text
    assert "プレイ中はボイスチャット必須です" in text
    assert "応募者A" not in text
    assert "この募集内容に似ている仕事" not in text

def _planner_snapshot(
    parent, *, title, category, visible_text, budget_min=None, budget_max=None,
    already_applied_ids=(),
):
    return parent.snapshot_contract.build_envelope({
        "pass_id": "v3b-guards", "lease_fence": {"task": "v3b-guards", "token": "0123456789abcdef0123456789abcdef", "generation": 1}, "observed_at": "2026-08-10T00:00:00Z",
        "objective": {"target_applications": 1, "max_applications": 1, "required_search_source_ids": ["single:new"]},
        "search_sources": [{"source_id": "single:new", "url": "https://coconala.com/requests?sort=new", "page_index": 1, "card_request_ids": ["97000002"], "has_next": False, "exhausted": True, "screenshot_sha256": "a" * 64, "dom_sha256": "b" * 64}],
        "request_details": [{"request_id": "97000002", "canonical_url": "https://coconala.com/requests/97000002", "title": title, "category": category, "visible_text": visible_text, "accepting_applications": True, "budget_min_jpy": budget_min, "budget_max_jpy": budget_max, "applicants_count": 0, "contracted_count": 0, "observed_at": "2026-08-10T00:00:00Z"}], "already_applied_ids": list(already_applied_ids),
    })


def _eligible_decision(price_jpy=15001):
    return {"request_id": "97000002", "business_class": "submit_required", "reason_codes": [], "proposal_text": "ご依頼の内容、対応可能です。" * 20, "price_jpy": price_jpy, "deliver_date": "2026-08-11"}


def _eligible_decision_for(request_id: str, *, price_jpy: int = 10000) -> dict[str, object]:
    return {
        "request_id": request_id,
        "business_class": "submit_required",
        "reason_codes": [],
        "proposal_text": "ご依頼の内容、対応可能です。" * 20,
        "price_jpy": price_jpy,
        "deliver_date": "2026-08-11",
    }


def _nine_candidate_snapshot(parent, *, cap: int = 8, count: int = 9):
    request_ids = [str(97010000 + index) for index in range(count)]
    return parent.snapshot_contract.build_envelope({
        "pass_id": "all-eligible-batch",
        "lease_fence": {
            "task": "all-eligible-batch-B2",
            "token": "0123456789abcdef0123456789abcdef",
            "generation": 1,
        },
        "observed_at": "2026-08-11T00:00:00Z",
        "objective": {
            "target_applications": 1,
            "max_applications": cap,
            "required_search_source_ids": ["single:new"],
        },
        "search_sources": [{
            "source_id": "single:new",
            "url": "https://coconala.com/requests?sort=new",
            "page_index": 1,
            "card_request_ids": request_ids,
            "has_next": False,
            "exhausted": True,
            "screenshot_sha256": "a" * 64,
            "dom_sha256": "b" * 64,
        }],
        "request_details": [
            _shard_detail(
                request_id,
                budget=10000,
                text="募集内容\n非同期で調査結果を文章で納品する案件です。",
            )
            for request_id in request_ids
        ],
        "already_applied_ids": [],
    })


def _nine_eligible_decisions(snapshot):
    return {
        "decisions": [
            _eligible_decision_for(detail["request_id"])
            for detail in snapshot["request_details"]
        ],
    }


def test_parent_commit_default_preserves_snapshot_objective_cap(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_default_objective_cap")
    snapshot = _nine_candidate_snapshot(parent)
    decisions = _nine_eligible_decisions(snapshot)
    effects = parent.FixtureEffects(
        snapshot,
        {"official_applied_ids": [detail["request_id"] for detail in snapshot["request_details"]]},
    )

    results = parent.commit_decisions(
        snapshot,
        decisions,
        store=parent.fence.IntentStore(tmp_path / "default-intents"),
        effects=effects,
    )

    assert [row["status"] for row in results].count("confirmed") == 8
    assert [row["status"] for row in results].count("cap_reached") == 1


def test_parent_commit_all_eligible_override_processes_nine_candidates(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_all_eligible_cap")
    snapshot = _nine_candidate_snapshot(parent)
    decisions = _nine_eligible_decisions(snapshot)
    effects = parent.FixtureEffects(
        snapshot,
        {"official_applied_ids": [detail["request_id"] for detail in snapshot["request_details"]]},
    )

    results = parent.commit_decisions(
        snapshot,
        decisions,
        store=parent.fence.IntentStore(tmp_path / "all-eligible-intents"),
        effects=effects,
        cap_override=len(decisions["decisions"]),
    )

    assert len(results) == 9
    assert [row["status"] for row in results] == ["confirmed"] * 9
    assert not any(row["status"] == "cap_reached" for row in results)


def test_parent_commit_uses_the_official_form_minimum_price(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_official_form_price")
    snapshot = _planner_snapshot(
        parent,
        title="見積り希望の事務作業",
        category="事務代行",
        visible_text="募集内容\n見積りを希望します",
    )
    decision = _eligible_decision(price_jpy=1000)
    effects = parent.FixtureEffects(
        snapshot,
        {
            "official_applied_ids": ["97000002"],
            "offer_price_constraints": {
                "97000002": (
                    "このカテゴリの最低提案価格は3,000円です。"
                    "提案額は500万円まで設定できます。"
                    "提案額は3,000円以上500万円以下で入力してください"
                )
            },
        },
    )

    results = parent.commit_decisions(
        snapshot,
        {"decisions": [decision]},
        store=parent.fence.IntentStore(tmp_path / "official-price-intents"),
        effects=effects,
    )

    assert results[0]["status"] == "confirmed"
    assert effects._filled["97000002"]["price_jpy"] == 3000
    assert effects.ledger[0]["price_jpy"] == 3000
    assert parent._official_offer_price_bounds(
        "最低提案価格は3,000円。提案額は500万円まで設定できます。"
    ) == (3000, 5_000_000)


def test_parent_commit_cap_counts_submit_attempts_when_readback_never_confirms(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_submit_attempt_cap")
    snapshot = _nine_candidate_snapshot(parent, cap=2, count=3)
    decisions = _nine_eligible_decisions(snapshot)

    class SubmitCountingEffects(parent.FixtureEffects):
        def __init__(self, snapshot, fixture):
            super().__init__(snapshot, fixture)
            self.submit_ids = []

        def click_submit(self, request_id):
            self.submit_ids.append(request_id)
            super().click_submit(request_id)

    effects = SubmitCountingEffects(snapshot, {"official_applied_ids": []})
    results = parent.commit_decisions(
        snapshot,
        decisions,
        store=parent.fence.IntentStore(tmp_path / "attempt-cap-intents"),
        effects=effects,
    )

    assert len(effects.submit_ids) == 2
    assert [row["status"] for row in results].count("awaiting_exact_id_readback") == 2
    assert [row["status"] for row in results].count("cap_reached") == 1


def test_submit_attempt_budget_is_shared_across_parent_process_phases(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_shared_wake_attempt_cap")
    snapshot = _nine_candidate_snapshot(parent, cap=20, count=21)
    rows = _nine_eligible_decisions(snapshot)["decisions"]
    budget = tmp_path / "one-pass" / "submit-attempt-budget.json"
    store = parent.fence.IntentStore(tmp_path / "shared-budget-intents")
    effects = parent.FixtureEffects(
        snapshot,
        {"official_applied_ids": [detail["request_id"] for detail in snapshot["request_details"]]},
    )

    first = parent.commit_decisions(
        snapshot,
        {"decisions": rows[:1]},
        store=store,
        effects=effects,
        cap_override=20,
        attempt_budget_path=budget,
        attempt_budget_pass_id="one-pass",
    )
    second = parent.commit_decisions(
        snapshot,
        {"decisions": rows[1:]},
        store=store,
        effects=effects,
        cap_override=20,
        attempt_budget_path=budget,
        attempt_budget_pass_id="one-pass",
    )

    assert [row["status"] for row in first + second] == ["confirmed"] * 20 + [
        "cap_reached",
    ]
    assert json.loads(budget.read_text(encoding="utf-8"))["reserved_attempts"] == 20
    assert store.read(snapshot["request_details"][20]["request_id"]) is None


def test_parent_second_wake_reconciles_prepared_after_submit_without_clicking_again(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_prepared_second_wake")
    snapshot = _nine_candidate_snapshot(parent, cap=2, count=1)
    decisions = _nine_eligible_decisions(snapshot)
    store = parent.fence.IntentStore(tmp_path / "prepared-intents")

    first_effects = parent.FixtureEffects(
        snapshot,
        {"official_applied_ids": [], "crash_at": "after_submit_click"},
    )
    first = parent.commit_decisions(snapshot, decisions, store=store, effects=first_effects)
    assert first[0]["status"] == "crash_injected:after_submit_click"
    assert first_effects.click_count == 2
    assert store.read("97010000")["state"] == parent.fence.PREPARED

    second_effects = parent.FixtureEffects(snapshot, {"official_applied_ids": []})
    second = parent.commit_decisions(snapshot, decisions, store=store, effects=second_effects)
    assert second[0]["status"] == "prepared_unconfirmed"
    assert second[0]["business_class"] == "duplicate_fenced"
    assert second_effects.click_count == 0
    assert second_effects.exact_id_readback_ids == ["97010000"]


def test_null_budget_software_price_over_15000_is_allowed() -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_null_budget_software_guard")
    snapshot = _planner_snapshot(parent, title="業務システム開発", category="コード", visible_text="募集内容\n詳細")
    errors = parent.validate_decisions(snapshot, {"decisions": [_eligible_decision()]})
    assert errors == [], errors


def test_null_budget_ordinary_low_price_remains_allowed() -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_null_budget_ordinary_low_price")
    snapshot = _planner_snapshot(parent, title="データ入力", category="事務", visible_text="募集内容\n入力作業")
    errors = parent.validate_decisions(snapshot, {"decisions": [_eligible_decision(price_jpy=3000)]})
    assert errors == [], errors


def test_eligible_zoom_listing_remains_the_model_decision() -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_zoom_is_model_policy")
    snapshot = _planner_snapshot(
        parent,
        title="相談",
        category="その他",
        visible_text="募集内容\nクライアントとZoomで面談必須",
        budget_max=10000,
    )
    decisions = {"decisions": [_eligible_decision(price_jpy=10000)]}

    errors = parent.validate_decisions(snapshot, decisions)

    assert errors == []
    clean, missing = parent._degrade_id_mismatch(snapshot, decisions)
    assert clean == decisions
    assert missing == []


def test_batch_with_no_valid_planner_decision_still_errors() -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_structural_decision_guard")
    snapshot = _planner_snapshot(parent, title="相談", category="その他", visible_text="募集内容\n詳細")

    with pytest.raises(parent.ParentContractError, match="decisions_empty_after_row_sanitization"):
        parent._degrade_id_mismatch(snapshot, {"decisions": [{}]})


def test_hard_prohibited_decision_requires_hard_class_and_visible_excerpt() -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_ineligible_evidence_guard")
    short_evidence = "顔出しで出演"
    long_evidence = "根拠" * 101
    snapshot = _planner_snapshot(
        parent,
        title="出演者募集",
        category="その他",
        visible_text=f"募集内容\n{short_evidence}\n{long_evidence}",
    )

    def decision(reason_codes):
        return {
            "request_id": "97000002",
            "business_class": "hard_prohibited",
            "reason_codes": reason_codes,
            "proposal_text": None,
            "price_jpy": None,
            "deliver_date": None,
        }

    assert parent.validate_decisions(snapshot, {
        "decisions": [decision(["mandatory_human_presence", short_evidence])],
    }) == []
    for reason_codes, expected_error in (
        (["weak_portfolio", short_evidence], "hard_prohibited_reason_class_invalid"),
        (["old", short_evidence], "hard_prohibited_reason_class_invalid"),
        ([["mandatory_human_presence"], short_evidence], "hard_prohibited_reason_class_invalid"),
        (["mandatory_human_presence"], "hard_prohibited_evidence_required"),
        (["mandatory_human_presence", "listing does not say this"], "hard_prohibited_evidence_not_in_visible_text"),
        (["mandatory_human_presence", long_evidence], "hard_prohibited_evidence_length_invalid"),
    ):
        errors = parent.validate_decisions(snapshot, {"decisions": [decision(reason_codes)]})
        assert any(expected_error in error for error in errors), errors


def test_live_presence_keyword_routing_has_no_production_callsite() -> None:
    planner_source = (SCRIPTS / "application_planner.py").read_text(encoding="utf-8")
    parent_source = PARENT_SCRIPT.read_text(encoding="utf-8")

    assert "_LIVE_PRESENCE_TERMS" not in planner_source
    assert "_LIVE_NEGATION" not in planner_source
    assert "def _requires_live_presence" not in planner_source
    assert "import _requires_live_presence" not in parent_source
    assert "_requires_live_presence(" not in f"{planner_source}\n{parent_source}"


def test_mandatory_submit_contract_accepts_submit_required_and_rejects_legacy_binary() -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_mandatory_submit_contract")
    snapshot = _planner_snapshot(
        parent,
        title="業務システム開発",
        category="コード",
        visible_text="募集内容\n非同期で納品する業務システム開発",
        budget_max=10000,
    )
    proposal = "ご依頼内容を確認し、実装方針と検証結果をまとめて納品します。" * 20
    required = {
        "request_id": "97000002",
        "business_class": "submit_required",
        "reason_codes": [],
        "proposal_text": proposal,
        "price_jpy": 10000,
        "deliver_date": "2026-08-11",
    }
    assert parent.validate_decisions(snapshot, {"decisions": [required]}) == []

    legacy = dict(required)
    legacy.pop("business_class")
    legacy["eligibility"] = "eligible"
    errors = parent.validate_decisions(snapshot, {"decisions": [legacy]})
    assert any("business_class" in error for error in errors), errors


def test_hard_prohibited_is_a_zero_effect_business_class() -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_hard_prohibited_effect")
    snapshot = _planner_snapshot(
        parent,
        title="出演者募集",
        category="その他",
        visible_text="募集内容\n本人の顔出し出演が必須です。",
    )
    decisions = {
        "decisions": [{
            "request_id": "97000002",
            "business_class": "hard_prohibited",
            "reason_codes": ["mandatory_human_presence", "本人の顔出し出演が必須です。"],
            "proposal_text": None,
            "price_jpy": None,
            "deliver_date": None,
        }],
    }
    effects = parent.FixtureEffects(snapshot, {"official_applied_ids": []})
    results = parent.commit_decisions(
        snapshot,
        decisions,
        store=parent.fence.IntentStore(Path("/tmp") / "apply-mandatory-submit-hard"),
        effects=effects,
    )
    assert results == [{
        "request_id": "97000002",
        "status": "hard_prohibited",
        "business_class": "hard_prohibited",
        "reason_codes": ["mandatory_human_presence", "本人の顔出し出演が必須です。"],
    }]
    assert effects.click_count == 0


def _fresh_hard_prohibited_decision() -> dict[str, object]:
    return {
        "request_id": "97000002",
        "business_class": "hard_prohibited",
        "reason_codes": ["mandatory_human_presence", "本人の顔出し出演が必須です。"],
        "proposal_text": None,
        "price_jpy": None,
        "deliver_date": None,
    }


def test_hard_prohibited_does_not_override_already_applied_fence(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_hard_prohibited_already_applied")
    snapshot = _planner_snapshot(
        parent,
        title="出演者募集",
        category="その他",
        visible_text="募集内容\n本人の顔出し出演が必須です。",
        already_applied_ids=["97000002"],
    )
    effects = parent.FixtureEffects(snapshot, {"official_applied_ids": ["97000002"]})

    results = parent.commit_decisions(
        snapshot,
        {"decisions": [_fresh_hard_prohibited_decision()]},
        store=parent.fence.IntentStore(tmp_path / "intents"),
        effects=effects,
    )

    assert results == [{
        "request_id": "97000002",
        "status": "dedupe_already_applied",
        "business_class": "duplicate_fenced",
    }]
    assert effects.click_count == effects.open_count == effects.fill_count == 0
    assert effects.exact_id_readback_ids == []


@pytest.mark.parametrize(
    ("durable_state", "official_applied", "expected_status", "expected_class", "ledger_expected"),
    [
        ("prepared", False, "hard_prohibited", "hard_prohibited", False),
        ("prepared", True, "reconciled_confirmed", "duplicate_fenced", True),
        ("confirmed", False, "confirmed_unverified", "duplicate_fenced", False),
        ("confirmed", True, "reconciled_confirmed", "duplicate_fenced", True),
    ],
)
def test_hard_prohibited_preserves_durable_duplicate_reconcile(
    tmp_path: Path,
    durable_state: str,
    official_applied: bool,
    expected_status: str,
    expected_class: str,
    ledger_expected: bool,
) -> None:
    parent = _load(PARENT_SCRIPT, f"application_parent_hard_prohibited_durable_{durable_state}_{official_applied}")
    snapshot = _planner_snapshot(
        parent,
        title="出演者募集",
        category="その他",
        visible_text="募集内容\n本人の顔出し出演が必須です。",
    )
    prior_offer = _eligible_decision(price_jpy=10000)
    store = parent.fence.IntentStore(tmp_path / "intents")
    intent = parent.fence.intent_payload(
        request_id="97000002",
        snapshot_sha256=snapshot["snapshot_sha256"],
        proposal_text=prior_offer["proposal_text"],
        price_jpy=prior_offer["price_jpy"],
        deliver_date=prior_offer["deliver_date"],
        lease_fence=snapshot["lease_fence"],
        state=durable_state,
    )
    parent.fence._durable_replace(store.intent_path("97000002"), intent)
    effects = parent.FixtureEffects(
        snapshot, {"official_applied_ids": ["97000002"] if official_applied else []}
    )

    results = parent.commit_decisions(
        snapshot,
        {"decisions": [_fresh_hard_prohibited_decision()]},
        store=store,
        effects=effects,
    )

    assert results[0]["status"] == expected_status
    assert results[0]["business_class"] == expected_class
    assert effects.click_count == effects.open_count == effects.fill_count == 0
    assert effects.exact_id_readback_ids == ["97000002"]
    assert bool(effects.ledger) is ledger_expected
    if ledger_expected:
        assert effects.ledger[0]["price_jpy"] == prior_offer["price_jpy"]
        assert effects.ledger[0]["deliver_date"] == prior_offer["deliver_date"]
        assert store.read("97000002")["state"] == parent.fence.CONFIRMED


def test_legacy_prepared_with_official_absence_and_fresh_form_retries(
    tmp_path: Path,
) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_legacy_prepared_fence")
    snapshot = _planner_snapshot(
        parent, title="AI調査", category="IT・システム開発", visible_text="募集内容\nAI調査です。"
    )
    decision = _eligible_decision()
    store = parent.fence.IntentStore(tmp_path / "intents")
    intent = parent.fence.intent_payload(
        request_id="97000002",
        snapshot_sha256=snapshot["snapshot_sha256"],
        proposal_text=decision["proposal_text"],
        price_jpy=decision["price_jpy"],
        deliver_date=decision["deliver_date"],
        lease_fence=snapshot["lease_fence"],
    )
    legacy = {key: value for key, value in intent.items() if key != "effect_phase"}
    legacy["version"] = 1
    parent.fence._durable_replace(store.intent_path("97000002"), legacy)

    results = parent.commit_decisions(
        snapshot, {"decisions": [decision]}, store=store,
        effects=parent.FixtureEffects(snapshot, {"official_applied_ids": []}),
    )

    assert results[0]["status"] == "awaiting_exact_id_readback"
    assert results[0]["business_class"] == "duplicate_fenced"
    assert store.read("97000002")["version"] == 2
    assert store.read("97000002")["effect_phase"] == "irreversible_attempt_started"
    history = list((tmp_path / "intents" / "recovery-history" / "97000002").glob("*.json"))
    assert len(history) == 1
    assert json.loads(history[0].read_text(encoding="utf-8"))["reason"] == (
        "legacy_prepared_official_absent_and_fresh_form_present"
    )


def test_effect_started_nonlanding_with_official_absence_and_fresh_form_retries(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_effect_started_nonlanding")
    snapshot = _planner_snapshot(
        parent, title="AI調査", category="IT・システム開発", visible_text="募集内容\nAI調査です。"
    )
    decision = _eligible_decision()
    store = parent.fence.IntentStore(tmp_path / "intents")
    prepared = store.prepare(
        request_id="97000002", snapshot_sha256=snapshot["snapshot_sha256"],
        proposal_text=decision["proposal_text"],
        price_jpy=decision["price_jpy"], deliver_date=decision["deliver_date"],
        lease_fence=snapshot["lease_fence"],
    )["intent"]
    with store.locked("97000002"):
        store.mark_irreversible_attempt_started_locked(
            "97000002", expected_cas=prepared["cas"]
        )

    effects = parent.FixtureEffects(snapshot, {
        "official_applied_ids": [], "saved_nonlanding_submit_ids": ["97000002"],
    })
    results = parent.commit_decisions(
        snapshot, {"decisions": [decision]}, store=store, effects=effects,
    )

    assert results[0]["status"] == "awaiting_exact_id_readback"
    assert effects.click_count == 2
    assert effects.exact_id_readback_ids == ["97000002", "97000002"]
    history = list((tmp_path / "intents" / "recovery-history" / "97000002").glob("*.json"))
    assert len(history) == 1 and json.loads(history[0].read_text(encoding="utf-8"))["reason"] == (
        "effect_started_nonlanding_official_absent_and_fresh_form_present"
    )


def test_nonlanding_proof_is_bound_to_the_intent_origin_pass(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_nonlanding_origin")
    apply_root = tmp_path / "gig" / "apply-direct"
    current_evidence = apply_root / "gig-apply-direct-300-3" / "refresh-evidence"
    origin = apply_root / "gig-apply-direct-100-1" / "coverage-evidence"
    current_evidence.mkdir(parents=True)
    origin.mkdir(parents=True)
    proof = origin / "gig-gig-apply-direct-100-1-B2-97000002-submit-attempt.png"
    proof.write_bytes(b"post-click screenshot")
    effects = parent.CdpParentEffects(
        ws_url="ws://127.0.0.1:1", evidence_dir=current_evidence,
        ledger_path=tmp_path / "applied.jsonl",
        pass_id="gig-apply-direct-300-3",
    )

    assert effects.saved_nonlanding_submit_evidence("97000002", {
        "lease_fence": {"task": "gig-apply-direct-gig-apply-direct-100-1-coverage"},
    }) is True
    assert effects.saved_nonlanding_submit_evidence("97000002", {
        "lease_fence": {"task": "gig-apply-direct-gig-apply-direct-200-2-coverage"},
    }) is False


# --- per-source evidence ----------------------------------------------------------


def test_japanese_category_ids_get_one_evidence_file_each() -> None:
    """Measured on the live objective: 87 source ids collapsed onto 26 filenames, 48 of
    them sharing one, because sanitising stripped Japanese to nothing."""
    parent = _load(PARENT_SCRIPT, "application_parent_evidence_names")
    categories = [
        "ロゴ作成・ロゴデザイン",
        "外国語翻訳",
        "外国語翻訳/英語翻訳/EN→JP",
        *(f"カテゴリ{index}" for index in range(44)),
    ]
    assert len(categories) == 47

    names = [
        parent.CdpParentEffects._safe_name(f"single:category:{label}")
        for label in categories
    ]

    assert len(set(names)) == 47
    assert all(name and name != "source" for name in names)


def test_evidence_names_stay_stable_and_keep_their_readable_stem() -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_evidence_stable")
    label = "single:category:SEO対策・上位表示"

    first = parent.CdpParentEffects._safe_name(label)
    second = parent.CdpParentEffects._safe_name(label)

    assert first == second
    assert first.startswith("single-category-SEO")
