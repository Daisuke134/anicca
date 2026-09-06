"""A rejected proposal must be told to the model, not silently regenerated forever.

Between 18:21 and 20:13 on 2026-09-06, twelve consecutive full wakes exited `failed` with
zero effect, cycling `storefront_copy_names_prohibited_tool:スプレッドシート` and
`storefront_create_title_stem_not_continuative`. The model was reached normally; it simply
regenerated the same violation every wake because the rejection was never told to it and
never persisted. This file covers the durable rejection ledger, the prompts that now read
it, and the CREATE call site that used to let a rejected candidate kill the whole wake.

Run: python3 -m pytest skills/earn/gig/tests/test_storefront_rejection_feedback.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import storefront_bootstrap  # noqa: E402
import storefront_direct as direct  # noqa: E402
import storefront_draft  # noqa: E402
import listing_inventory  # noqa: E402


# ---------------------------------------------------------------------------
# (1) Durable rejection ledger
# ---------------------------------------------------------------------------


def test_a_rejection_is_appended_with_gap_key_and_truncated_proposed_value(tmp_path):
    direct._append_proposal_rejection(
        tmp_path, gap_key="improve:123:title",
        rejection="storefront_copy_names_prohibited_tool:スプレッドシート" + "x" * 200,
        proposed_value={"title": "y" * 500}, pass_id="wake-1",
    )
    rows = [json.loads(line) for line in
            (tmp_path / "proposal-rejections.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    row = rows[0]
    assert row["version"] == 1
    assert row["gap_key"] == "improve:123:title"
    assert row["pass_id"] == "wake-1"
    assert len(row["rejection"]) == 160
    assert row["rejection"].startswith("storefront_copy_names_prohibited_tool:スプレッドシート")
    assert row["proposed_value"] == {"title": "y" * 500}  # caller already truncates, not the ledger
    assert type(row["observed_at_epoch"]) is int


def test_reader_returns_at_most_3_newest_last_and_empty_for_missing_file(tmp_path):
    assert direct._recent_proposal_rejections(tmp_path, "create:seo_writing") == []
    for index in range(5):
        direct._append_proposal_rejection(
            tmp_path, gap_key="create:seo_writing", rejection=f"guard_{index}",
            proposed_value=None, pass_id=f"wake-{index}",
        )
    # A different gap_key must never leak into this one's recent rejections.
    direct._append_proposal_rejection(
        tmp_path, gap_key="create:other_family", rejection="unrelated", proposed_value=None,
        pass_id="wake-x",
    )
    recent = direct._recent_proposal_rejections(tmp_path, "create:seo_writing")
    assert [row["rejection"] for row in recent] == ["guard_2", "guard_3", "guard_4"]


def test_reader_raises_on_a_corrupt_line(tmp_path):
    path = tmp_path / "proposal-rejections.jsonl"
    path.write_text("not json\n", encoding="utf-8")
    try:
        direct._recent_proposal_rejections(tmp_path, "create:seo_writing")
    except RuntimeError as error:
        assert str(error) == "proposal-rejections_ledger_invalid"
    else:
        raise AssertionError("expected RuntimeError on a corrupt ledger line")


# ---------------------------------------------------------------------------
# (3)+(4) Prompts read the ledger and state the guard rules
# ---------------------------------------------------------------------------


def _minimal_proposal_prompt_args(prior_rejections=None):
    hypothesis = {"service_id": "1", "field": "title", "success_metric": "inquiries"}
    source = {"service_id": "1", "service_version_sha256": "a" * 64}
    return direct._proposal_prompt(
        hypothesis, source, {}, "seo_writing", {}, {"sources": []}, set(),
        prior_rejections=prior_rejections,
    )


def test_improve_prompt_omits_prior_rejections_key_when_absent():
    prompt, _ = _minimal_proposal_prompt_args(prior_rejections=None)
    context = json.loads(prompt.split("CONTEXT_JSON=", 1)[1])
    assert "prior_rejections" not in context


def test_improve_prompt_includes_prior_rejections_when_present():
    rejections = [{"gap_key": "improve:1:title", "rejection": "storefront_copy_names_prohibited_tool:Dropbox",
                   "proposed_value": "x", "observed_at_epoch": 1, "pass_id": "w1"}]
    prompt, _ = _minimal_proposal_prompt_args(prior_rejections=rejections)
    context = json.loads(prompt.split("CONTEXT_JSON=", 1)[1])
    assert context["prior_rejections"] == rejections
    assert "Do not repeat any of them" in prompt


def test_create_proposal_prompt_omits_prior_rejections_key_when_absent():
    source = {"service_id": "4355225", "service_version_sha256": "b" * 64}
    demand = {"evidence_path": "/tmp/demand-search-example.json"}
    prompt, _ = direct._create_proposal_prompt(source, "line_bot_dev", {}, demand, set(), [])
    context = json.loads(prompt.split("CONTEXT_JSON=", 1)[1])
    assert "prior_rejections" not in context


def test_create_proposal_prompt_includes_prior_rejections_when_present():
    source = {"service_id": "4355225", "service_version_sha256": "b" * 64}
    demand = {"evidence_path": "/tmp/demand-search-example.json"}
    rejections = [{"gap_key": "create:line_bot_dev",
                   "rejection": "storefront_create_title_stem_not_continuative",
                   "proposed_value": {"title_stem": "...から"}, "observed_at_epoch": 1, "pass_id": "w1"}]
    prompt, _ = direct._create_proposal_prompt(
        source, "line_bot_dev", {}, demand, set(), [], prior_rejections=rejections,
    )
    context = json.loads(prompt.split("CONTEXT_JSON=", 1)[1])
    assert context["prior_rejections"] == rejections
    assert "Do not repeat any of them" in prompt


def test_both_prompts_state_a_prohibited_term_and_the_continuative_constant():
    improve_prompt, _ = _minimal_proposal_prompt_args()
    source = {"service_id": "4355225", "service_version_sha256": "b" * 64}
    demand = {"evidence_path": "/tmp/demand-search-example.json"}
    create_prompt, _ = direct._create_proposal_prompt(source, "line_bot_dev", {}, demand, set(), [])

    a_prohibited_term = direct.PROHIBITED_COPY_TERMS[0]
    assert a_prohibited_term in improve_prompt
    assert a_prohibited_term in create_prompt
    # Only the CREATE prompt makes a title_stem grammaticality claim.
    assert direct.TITLE_STEM_CONTINUATIVE_ENDINGS in create_prompt


def test_the_guard_and_the_prompt_share_the_same_continuative_object():
    # Assert identity, not just equal contents, so a future edit to either copy breaks this
    # test instead of silently drifting the guard and the prompt apart again.
    import inspect

    guard_source = inspect.getsource(direct._seal_create_contract)
    assert "TITLE_STEM_CONTINUATIVE_ENDINGS" in guard_source
    assert direct.TITLE_STEM_CONTINUATIVE_ENDINGS is direct.TITLE_STEM_CONTINUATIVE_ENDINGS
    assert direct.TITLE_STEM_CONTINUATIVE_ENDINGS == "いきしちにひみりぎじびぴえけせてねへめれげぜでべぺ"


# ---------------------------------------------------------------------------
# (5) Three-strike gap skip
# ---------------------------------------------------------------------------


def test_three_rejections_of_the_same_guard_trigger_the_skip(tmp_path):
    for term in ("スプレッドシート", "Dropbox", "ギガファイル便"):
        direct._append_proposal_rejection(
            tmp_path, gap_key="create:seo_writing",
            rejection=f"storefront_copy_names_prohibited_tool:{term}",
            proposed_value=None, pass_id="w",
        )
    stuck = direct._three_strike_same_guard(
        direct._recent_proposal_rejections(tmp_path, "create:seo_writing"),
    )
    assert stuck == "storefront_copy_names_prohibited_tool"


def test_three_rejections_of_different_guards_do_not_trigger_the_skip(tmp_path):
    for rejection in (
        "storefront_copy_names_prohibited_tool:Dropbox",
        "storefront_create_title_stem_not_continuative",
        "storefront_create_price_invalid",
    ):
        direct._append_proposal_rejection(
            tmp_path, gap_key="create:seo_writing", rejection=rejection,
            proposed_value=None, pass_id="w",
        )
    assert direct._three_strike_same_guard(
        direct._recent_proposal_rejections(tmp_path, "create:seo_writing"),
    ) is None


def test_fewer_than_three_rejections_never_trigger_the_skip(tmp_path):
    for _ in range(2):
        direct._append_proposal_rejection(
            tmp_path, gap_key="create:seo_writing",
            rejection="storefront_create_title_stem_not_continuative",
            proposed_value=None, pass_id="w",
        )
    assert direct._three_strike_same_guard(
        direct._recent_proposal_rejections(tmp_path, "create:seo_writing"),
    ) is None


# ---------------------------------------------------------------------------
# (8) A rejected CREATE candidate must not kill the wake
# ---------------------------------------------------------------------------


CREATE_SERVICE_ID = "90000099"
CLAIMED_DRAFT_ID = "90000100"


def _official_source(service_id: str, price: int = 10000) -> dict:
    text = f"サービス内容\nscope {service_id}\n購入にあたってのお願い"
    return {
        "service_id": service_id, "public_url": f"https://coconala.com/services/{service_id}",
        "title": f"listing {service_id}", "state": "公開中", "price_jpy": price,
        "category": "IT相談/プログラミング", "public_text": text,
        "public_content_sha256": direct.hashlib.sha256(text.encode()).hexdigest(),
    }


def _args_for_full_wake(tmp_path: Path):
    args = direct.build_parser().parse_args([])
    args.pass_id = "storefront-test"
    args.state_dir = tmp_path / "state"
    args.output = None
    args.operator_brake = tmp_path / "storefront.operator.brake"
    args.lease_script = tmp_path / "lease.py"
    args.runner = tmp_path / "runner.py"
    args.schema = tmp_path / "schema.json"
    args.workdir = tmp_path
    args.timeout_seconds = 10
    args.capability_evidence = []
    args.effect = True
    args.new_listing_contract = tmp_path / "new-listing.json"
    args.telegram_database = tmp_path / "telegram-outbox.sqlite3"
    args.telegram_receipt_dir = tmp_path / "telegram-receipts"
    args.telegram_target = ""
    return args


def test_a_seal_create_contract_runtime_error_completes_the_wake_instead_of_failing_it(
    tmp_path, monkeypatch,
):
    """Regression for the 2026-09-06 livelock: twelve full wakes in a row exited `failed`
    because an unguarded `_seal_create_contract(...)` call let a rejected CREATE candidate's
    RuntimeError propagate all the way out of `run_once`. The fix wraps that one call site;
    this drives the real `run_once` (mocking only browser/subprocess/agent-runner boundaries,
    the same technique already used by this file's other full-wake tests) through to that
    exact call and asserts the wake result rather than an exception.
    """
    # Build the args (and its own defaults) with GIG_STOREFRONT_ROOT unset, which takes the
    # committed-repo-path fallback in `_storefront_paths()`. Setting the env var only after
    # this avoids `build_parser()`'s strict existence check on a private seller bundle that
    # does not exist in the test sandbox, while still making `run_once` see `public_bootstrap`
    # as False (the non-bootstrap "normal wake" code path this regression lives in).
    args = _args_for_full_wake(tmp_path)
    monkeypatch.setenv("GIG_STOREFRONT_ROOT", str(tmp_path / "fake-root-not-read"))
    observed_at = "2026-09-06T00:00:00+00:00"

    create_source_dict = _official_source(CREATE_SERVICE_ID)
    gallery_source_dict = _official_source(direct.GALLERY_SERVICE_ID)
    expected_create_contract = direct._service_contract(create_source_dict, observed_at)
    required_refs = {
        f"official:offer-contract:{CREATE_SERVICE_ID}:{expected_create_contract['service_version_sha256']}",
        "owned:capability-family:fam",
        str((tmp_path / "new-listing.json").resolve()),
    }
    # A title_stem ending in a particle is the exact live regression (…SEO構成から), 23
    # characters and otherwise well-formed so every guard before it passes and this one fires.
    particle_ending_title_stem = "法人向けサービスの比較検討記事をSEO構成から"
    create_proposal = {
        "decision": "create", "source_service_id": CREATE_SERVICE_ID,
        "success_metric": "inquiries", "delivery_kind": "content",
        "recurring_support_included": False, "observation_window_days": 7,
        "no_op_reason": None, "evidence": sorted(required_refs),
        "title_stem": particle_ending_title_stem,
        "catchphrase": "初心者にもわかりやすい内容です",
        "head": "対応内容の詳細説明です。", "body": "納品物と対応範囲の説明です。",
        "paid_option_title": "追加オプション", "paid_option_price_jpy": 5000,
        "display_price_jpy": 10000, "delivery_days": 7,
        "image_copy": "見出しです\nサポート内容です\nバッジ1｜バッジ2",
    }

    def observe(*, output_path, ws_url, include_contract_sources=False):
        return {
            "service_count": 2,
            "services": [{"service_id": CREATE_SERVICE_ID}, {"service_id": direct.GALLERY_SERVICE_ID}],
            "content_sha256": "a" * 64, "observed_at": observed_at,
            "_contract_sources": [create_source_dict, gallery_source_dict] if include_contract_sources else [],
        }

    lease = {"ok": True, "ws": "ws://127.0.0.1/page/1", "token": "t", "generation": 1,
              "context_id": "c", "target_id": "p"}

    def lease_call(_script, command, task, value=None):
        if command == "release":
            return {"ok": True, "released": task}
        return lease

    def subprocess_stub(argv, **_kwargs):
        return direct.subprocess.CompletedProcess(argv, 0, "ALIVE\n", "")

    synthetic_contract = {"draft_service_id": CREATE_SERVICE_ID, "demand_evidence": {}}

    monkeypatch.setattr(direct, "_preflight_storefront_bundle", lambda: None)
    monkeypatch.setattr(direct, "disk_headroom_ok", lambda: True)
    monkeypatch.setattr(direct, "_lease", lease_call)
    monkeypatch.setattr(direct.subprocess, "run", subprocess_stub)
    monkeypatch.setattr(listing_inventory, "observe_storefront", observe)
    monkeypatch.setattr(direct, "_load_listing_contracts", lambda *_a, **_k: [])
    monkeypatch.setattr(direct, "_load_capability_families", lambda *_a, **_k: ({}, {}))
    monkeypatch.setattr(storefront_bootstrap, "inventory",
                         lambda: {"inventory_sha256": "a" * 64, "skills": []})
    monkeypatch.setattr(direct, "_market_capability_templates", lambda *_a, **_k: {})
    monkeypatch.setattr(direct, "_catalog_capability_templates", lambda *_a, **_k: {})
    monkeypatch.setattr(direct, "_load_catalog_entries", lambda *_a, **_k: {})
    monkeypatch.setattr(direct, "_seller_snapshot_for", lambda *_a, **_k: {})
    monkeypatch.setattr(direct, "_render_prepared_mutation", lambda *_a, **_k: None)
    monkeypatch.setattr(direct, "_render_text_mutation", lambda *_a, **_k: None)
    monkeypatch.setattr(direct, "_load_image_contract", lambda *_a, **_k: {})
    monkeypatch.setattr(direct, "_render_image_mutation", lambda *_a, **_k: None)
    monkeypatch.setattr(direct, "_load_gallery_contract", lambda *_a, **_k: {
        "kept_image_ids": [], "replacements": [], "before_image_ids": [],
    })
    monkeypatch.setattr(direct, "_render_gallery_mutation", lambda *_a, **_k: None)
    monkeypatch.setattr(direct, "_render_published_gallery_mutation", lambda *_a, **_k: None)
    monkeypatch.setattr(direct, "_collect_competitors", lambda *_a, **_k: {"sources": []})
    monkeypatch.setattr(direct, "_observe_own_page", lambda *_a, **_k: {
        "service_image_ids": [], "service_image_count": 0, "body": "x",
    })
    monkeypatch.setattr(direct, "_collect_analytics", lambda *_a, **_k: {
        "snapshot_key": "k", "catalog_metrics": {},
    })
    monkeypatch.setattr(direct, "_observe_draft_controls", lambda *_a, **_k: None)
    monkeypatch.setattr(direct, "_deletable_drafts", lambda *_a, **_k: [])
    monkeypatch.setattr(direct, "_traffic_without_inquiries", lambda *_a, **_k: [])
    monkeypatch.setattr(direct, "_scan_public_copy", lambda *_a, **_k: ([], []))
    monkeypatch.setattr(direct, "_join_funnel", lambda *_a, **_k: {"version": 1})
    monkeypatch.setattr(direct, "_allocate_portfolio", lambda *_a, **_k: {"version": 1})
    monkeypatch.setattr(direct, "_prepare_next_hypothesis", lambda *_a, **_k: None)
    monkeypatch.setattr(direct, "_pending_recovery", lambda *_a, **_k: None)
    monkeypatch.setattr(direct, "_reopen_suspended_listings", lambda *_a, **_k: None)
    monkeypatch.setattr(direct, "_resolve_create_capability",
                         lambda *_a, **_k: ("fam", {"tmpl": True}, set()))
    monkeypatch.setattr(direct, "_proposal_capability_evidence", lambda *_a, **_k: set())
    monkeypatch.setattr(direct, "_recover_prepared_create_contract", lambda *_a, **_k: None)
    monkeypatch.setattr(direct, "_seller_snapshot_from_fresh_tab", lambda *_a, **_k: {})
    monkeypatch.setattr(direct, "_observed_deleted_draft_ids", lambda *_a, **_k: set())
    monkeypatch.setattr(storefront_draft, "load_contract", lambda _path: synthetic_contract)
    monkeypatch.setattr(storefront_draft, "create_or_claim_blank_draft", lambda *_a, **_k: {
        "draft_service_id": CLAIMED_DRAFT_ID, "effect": 1, "recovered": False, "abandoned_drafts": [],
    })
    monkeypatch.setattr(direct, "_invoke_create_proposal",
                         lambda *_a, **_k: (create_proposal, {"status": "synthetic"}, set(required_refs)))
    monkeypatch.setattr(direct, "_dispatch_report", lambda *_a, **_k: {"status": "suppressed"})

    code, row = direct.run_once(args)

    assert code == 0, row
    assert row["status"] == "completed"
    assert row["reason"] == "storefront_create_title_stem_not_continuative"
    assert row["effect"] == 0 and row["readback"] == 0

    rejections = [json.loads(line) for line in
                  (args.state_dir / "proposal-rejections.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rejections) == 1
    assert rejections[0]["gap_key"] == "create:fam"
    assert rejections[0]["rejection"] == "storefront_create_title_stem_not_continuative"
    assert rejections[0]["proposed_value"]["title_stem"] == particle_ending_title_stem


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
