"""Focused boundary checks for the dedicated Storefront owner."""

from __future__ import annotations

import json
import plistlib
import pytest
import sys
from pathlib import Path
from types import SimpleNamespace

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
PLIST = Path(__file__).resolve().parents[1] / "launchd" / "ai.anicca.hf-gig-storefront-direct.plist"
sys.path.insert(0, str(SCRIPTS))
import storefront_direct as direct  # noqa: E402


def _args(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        pass_id="storefront-test",
        state_dir=tmp_path / "state",
        output=None,
        operator_brake=tmp_path / "storefront.operator.brake",
        lease_script=tmp_path / "lease.py",
        runner=tmp_path / "runner.py",
        schema=tmp_path / "schema.json",
        workdir=tmp_path,
        timeout_seconds=10,
        capability_evidence=[],
        effect=False,
    )


def test_noop_observes_on_one_lease_and_commits_only_after_release(tmp_path, monkeypatch):
    events = []
    lease = {"ok": True, "ws": "ws://127.0.0.1/page/1", "token": "t", "generation": 2,
             "context_id": "c", "target_id": "p"}

    def lease_call(_script, command, task, value=None):
        events.append(command)
        if command == "release":
            return {"ok": True, "released": task}
        return lease

    def observe(*, output_path, ws_url, include_contract_sources=False):
        events.append(("observe", ws_url))
        sources = [{
            "service_id": str(i + 1), "public_url": f"https://coconala.com/services/{i + 1}",
            "title": f"service {i + 1}", "state": "公開中", "price_jpy": 1000,
            "category": "category", "public_text": f"サービス内容\nscope {i + 1}\n購入にあたってのお願い",
            "public_content_sha256": direct.hashlib.sha256(
                f"サービス内容\nscope {i + 1}\n購入にあたってのお願い".encode()
            ).hexdigest(),
        } for i in range(11)]
        return {"service_count": 11, "services": [{"service_id": str(i + 1)} for i in range(11)],
                "content_sha256": "a" * 64, "observed_at": "2026-08-15T00:00:00+00:00",
                "_contract_sources": sources if include_contract_sources else []}

    monkeypatch.setattr(direct, "_lease", lease_call)
    monkeypatch.setattr(direct, "_collect_competitors", lambda *_args: {"sources": [{}] * 7})
    monkeypatch.setattr(direct, "_observe_own_page", lambda *_args, **_kwargs: {"body": "FAQなし"})
    monkeypatch.setattr(direct, "_collect_analytics", lambda *_args, **_kwargs: {
        "snapshot_key": "storefront:analytics:v1:test",
    })
    monkeypatch.setattr(direct, "_invoke_judge", lambda **_kwargs: {})
    monkeypatch.setattr(direct, "_guard_judgement", lambda *_args, **_kwargs: {
        "decision": "no_op", "no_op_reason": "no evidence", "service_id": None,
        "changed_field": None, "experiment_key": None,
    })
    import listing_inventory
    monkeypatch.setattr(listing_inventory, "observe_storefront", observe)
    code, row = direct.run_once(_args(tmp_path))

    assert code == 0
    assert events == ["acquire", ("observe", lease["ws"]), "heartbeat", "release"]
    assert row["status"] == "completed" and row["effect"] == row["duplicate"] == 0
    assert row["official_services_read"] == 11 and row["lease"]["released"] is True
    assert row["offer_contracts_appended"] == 11
    assert row["competitor_evidence_count"] == 7
    persisted = json.loads((tmp_path / "state" / "current.json").read_text())
    assert persisted == row
    assert json.loads((tmp_path / "state" / "wakes.jsonl").read_text()) == row
    for name in direct.STATE_FILES:
        assert (tmp_path / "state" / name).exists()


@pytest.mark.parametrize("case", ("missing", "duplicate", "substituted"))
def test_invalid_official_contract_fails_before_downstream_work_and_releases_lease(
    tmp_path, monkeypatch, case,
):
    lease = {"ok": True, "ws": "ws://127.0.0.1/page/1", "token": "t", "generation": 2,
             "context_id": "c", "target_id": "p"}
    events = []
    downstream = []

    def lease_call(_script, command, task, value=None):
        events.append(command)
        if command == "release":
            return {"ok": True, "released": task}
        return lease

    def source(service_id):
        text = f"サービス内容\nscope {service_id}\n購入にあたってのお願い"
        return {
            "service_id": service_id, "public_url": f"https://coconala.com/services/{service_id}",
            "title": "OpenCV画像認識", "state": "公開中", "price_jpy": 20000,
            "category": "IT相談/プログラミング", "public_text": text,
            "public_content_sha256": direct.hashlib.sha256(text.encode()).hexdigest(),
        }

    services = [{"service_id": "91000001"}]
    if case == "missing":
        sources = []
    elif case == "duplicate":
        services = [{"service_id": "91000001"}, {"service_id": "4330369"}]
        sources = [source("91000001"), source("91000001")]
    else:
        sources = [source("9999999")]

    def observe(*, output_path, ws_url, include_contract_sources=False):
        return {"service_count": len(services), "services": services,
                "content_sha256": "a" * 64, "observed_at": "2026-08-15T00:00:00+00:00",
                "_contract_sources": sources if include_contract_sources else []}

    monkeypatch.setattr(direct, "_lease", lease_call)
    def collect(*_args):
        downstream.append("competitors")
        return {"sources": []}

    def own_page(*_args, **_kwargs):
        downstream.append("own_page")
        return {"body": "FAQなし"}

    def recovery(*_args):
        downstream.append("recovery")
        return None

    def invoke(**_kwargs):
        downstream.append("judge")
        return judgement

    judgement = {
        "decision": "change", "service_id": direct.TARGET_SERVICE_ID, "changed_field": "FAQ",
        "before_value": "FAQ_ABSENT", "proposed_value": "Q. 準備は？\nA. 対象画像をご共有ください。",
        "hypothesis": "h", "competitor_evidence_paths": [], "capability_evidence_paths": [],
        "success_metric": "inquiries", "observation_window_days": 7,
        "no_op_reason": None, "experiment_key": "storefront:test", "uncertainty": [],
    }

    monkeypatch.setattr(direct, "_collect_competitors", collect)
    monkeypatch.setattr(direct, "_observe_own_page", own_page)
    monkeypatch.setattr(direct, "_pending_recovery", recovery)
    monkeypatch.setattr(direct, "_invoke_judge", invoke)
    monkeypatch.setattr(direct, "_guard_judgement", lambda *_args, **_kwargs: judgement)
    monkeypatch.setattr(direct, "_execute_faq_effect", lambda **_kwargs: downstream.append("effect"))
    import listing_inventory
    monkeypatch.setattr(listing_inventory, "observe_storefront", observe)

    args = _args(tmp_path)
    args.effect = True
    code, row = direct.run_once(args)

    assert code == 1
    assert row["status"] == "failed"
    assert row["reason"] == "official_service_contract_invalid"
    assert events == ["acquire", "release"]
    assert downstream == []


def test_storefront_brake_prevents_lease_and_observation(tmp_path, monkeypatch):
    args = _args(tmp_path)
    args.operator_brake.write_text("held")
    monkeypatch.setattr(direct, "_lease", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError()))

    code, row = direct.run_once(args)

    assert code == 0
    assert row["status"] == "operator_brake" and row["effect"] == 0


def test_storefront_report_reuses_outbox_receipt_and_dedupes_noop(tmp_path, monkeypatch):
    args = _args(tmp_path)
    args.telegram_database = tmp_path / "telegram-outbox.sqlite3"
    args.telegram_receipt_dir = tmp_path / "telegram-delivery-receipts"
    args.telegram_target = "42"
    args.openclaw = Path("/opt/homebrew/bin/openclaw")
    calls = []

    def send(argv, **kwargs):
        calls.append((argv, kwargs))
        return direct.subprocess.CompletedProcess(argv, 0, '{"messageId":"provider-1"}', "")

    monkeypatch.setattr(direct.subprocess, "run", send)
    row = direct._receipt(
        "scheduled-1", status="completed", decision="no_op", effect=0, readback=0,
        duplicate=0, actionable=0, official_services_read=11,
        inventory_content_sha256="a" * 64,
    )
    first = direct._dispatch_report(args, row)
    second = direct._dispatch_report(args, {**row, "pass_id": "scheduled-2"})

    assert first == {"status": "sent", "message_id": "provider-1",
                     "event_key": second["event_key"]}
    assert second["status"] == "deduped" and second["message_id"] == "provider-1"
    assert len(calls) == 1
    receipts = list(args.telegram_receipt_dir.glob("*.json"))
    assert len(receipts) == 1 and receipts[0].stat().st_mode & 0o777 == 0o600
    receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
    assert receipt["event_key"] == first["event_key"]
    assert receipt["message_id"] == "provider-1"


def test_persisted_wake_contains_transport_result_without_changing_effect(tmp_path, monkeypatch):
    args = _args(tmp_path)
    args.telegram_database = tmp_path / "telegram-outbox.sqlite3"
    monkeypatch.setattr(direct, "_dispatch_report", lambda _args, _row: {
        "status": "delivery_unknown", "message_id": None, "event_key": "stable-effect",
    })
    row = direct._receipt("effect-1", status="completed", effect=1, readback=1, duplicate=0)

    persisted = direct._persist_receipt(args, args.state_dir / "current.json", row)

    assert persisted["effect"] == persisted["readback"] == 1
    assert persisted["telegram"]["status"] == "delivery_unknown"
    assert json.loads((args.state_dir / "wakes.jsonl").read_text(encoding="utf-8")) == persisted


def test_direct_source_has_no_legacy_or_cross_lane_dependency():
    source = (SCRIPTS / "storefront_direct.py").read_text(encoding="utf-8")
    for forbidden in ("ai.hermes.gateway", "gig_pass.sh", "b0_objective", "b0_result_gate",
                      "shuppin.jsonl", "/operator.brake", "application_parent"):
        assert forbidden not in source


def test_launchagent_is_immutable_dedicated_and_storefront_braked():
    data = plistlib.loads(PLIST.read_bytes())
    argv = data["ProgramArguments"]
    env = data["EnvironmentVariables"]

    assert data["Label"] == "ai.anicca.hf-gig-storefront-direct"
    assert data["StartInterval"] == 1800
    assert argv == ["/opt/homebrew/bin/python3",
                    "__LIFE_MANAGER_REPO__/skills/earn/gig/scripts/storefront_direct.py",
                    "--effect"]
    assert env["GIG_OPERATOR_BRAKE_FILE"].endswith("/storefront.operator.brake")
    assert env["ANICCA_BUDGET_DAILY_SCOPE"] == "gig-storefront-direct"
    assert env["ANICCA_BUDGET_REQUIRED"] == "1"
    assert int(env["ANICCA_PASS_TOKEN_BUDGET"]) > 0
    assert int(env["ANICCA_LOOP_DAILY_TOKEN_BUDGET"]) >= int(env["ANICCA_PASS_TOKEN_BUDGET"])
    serialized = PLIST.read_text(encoding="utf-8")
    for forbidden in ("hermes", "gig_pass.sh", "/operator.brake</string>", "worktree"):
        assert forbidden not in serialized


def test_competitor_sources_are_fresh_owned_official_and_exclude_own(tmp_path, monkeypatch):
    import listing_inventory

    monkeypatch.setattr(direct, "COMPETITOR_SOURCES", (
        ("category", "https://coconala.com/categories/230/66"),
        ("service", "https://coconala.com/services/222"),
    ))

    async def observed(_ws, url, _expression):
        return {"url": url, "title": "official", "body": f"fresh body {url}"}

    monkeypatch.setattr(listing_inventory, "_eval_json", observed)
    manifest = direct._collect_competitors("ws://leased", tmp_path, {"111"})

    assert len(manifest["sources"]) == 2
    for source in manifest["sources"]:
        row = json.loads(Path(source["path"]).read_text())
        assert row["official"] is row["observed"] is True
        assert row["content_sha256"] == source["content_sha256"]
    monkeypatch.setattr(direct, "COMPETITOR_SOURCES", (("service", "https://coconala.com/services/111"),))
    try:
        direct._collect_competitors("ws://leased", tmp_path, {"111"})
    except RuntimeError as error:
        assert str(error) == "competitor_source_is_own_service"
    else:
        raise AssertionError("own service accepted as competitor")


def test_one_variable_guard_binds_fresh_evidence_and_enforces_effect_budget(tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    competitor = evidence / "competitor.json"
    competitor.write_text(json.dumps({"official": True, "observed": True,
                                      "observed_at_epoch": 100, "content_sha256": "a" * 64}))
    capability = tmp_path / "capability.json"
    capability.write_text("{}")
    manifest = {"sources": [{"path": str(competitor), "content_sha256": "a" * 64}]}
    value = {
        "decision": "change", "service_id": direct.TARGET_SERVICE_ID, "changed_field": "FAQ",
        "before_value": "FAQ_ABSENT", "proposed_value": "Q. 何を準備しますか？\nA. 対象画像と期待結果をご共有ください。",
        "hypothesis": "事前入力を明確にすると問い合わせ摩擦が下がる",
        "competitor_evidence_paths": [str(competitor)], "capability_evidence_paths": [str(capability)],
        "success_metric": "inquiries", "observation_window_days": 7,
        "no_op_reason": None, "experiment_key": None, "uncertainty": [],
    }
    effects = tmp_path / "effects.jsonl"

    accepted = direct._guard_judgement(
        value, own_page={"body": "FAQなし"}, competitor_manifest=manifest,
        capability_paths={str(capability)}, evidence_dir=evidence, effects_path=effects,
        minimum_epoch=100, now=200,
    )
    assert accepted["decision"] == "change"
    assert accepted["experiment_key"].startswith(f"storefront:v1:{direct.TARGET_SERVICE_ID}:FAQ:")

    effects.write_text(json.dumps({"status": "accepted", "effect": 1,
                                   "accepted_at_epoch": 190, "service_id": "other",
                                   "experiment_key": "other"}) + "\n")
    blocked = direct._guard_judgement(
        value, own_page={"body": "FAQなし"}, competitor_manifest=manifest,
        capability_paths={str(capability)}, evidence_dir=evidence, effects_path=effects,
        minimum_epoch=100, now=200,
    )
    assert blocked["decision"] == "no_op"
    assert blocked["no_op_reason"] == "account_effect_budget_24h"


def test_judge_result_must_be_fresh_and_owned(tmp_path):
    runner = tmp_path / "runner.py"
    result = {"decision": "no_op", "service_id": None, "changed_field": None,
              "before_value": None, "proposed_value": None, "hypothesis": "insufficient evidence",
              "competitor_evidence_paths": [], "capability_evidence_paths": [],
              "success_metric": None, "observation_window_days": None,
              "no_op_reason": "insufficient evidence", "experiment_key": None, "uncertainty": []}
    runner.write_text(
        "import json,sys\nfrom pathlib import Path\n"
        "a=sys.argv;e=Path(a[a.index('--evidence-dir')+1]);e.mkdir(parents=True,exist_ok=True)\n"
        f"r=e/'result.json';r.write_text(json.dumps({result!r}))\n"
        "(e/'summary.json').write_text(json.dumps({'status':'success','result_path':str(r)}))\n"
    )
    evidence = tmp_path / "judge"
    value = direct._invoke_judge(
        runner=runner, schema=tmp_path / "schema.json", workdir=tmp_path, evidence_dir=evidence,
        own_page={"url": "https://coconala.com/services/91000001", "body": "own"},
        manifest={"sources": []}, capability_paths=set(), timeout_seconds=10,
    )
    assert value == result


def test_safe_noop_normalizes_non_effect_service_metadata(tmp_path):
    value = {
        "decision": "no_op", "service_id": direct.TARGET_SERVICE_ID,
        "changed_field": None, "before_value": None, "proposed_value": None,
        "hypothesis": "current FAQ already exists", "competitor_evidence_paths": [],
        "capability_evidence_paths": [], "success_metric": None,
        "observation_window_days": None, "no_op_reason": "nothing to change",
        "experiment_key": None, "uncertainty": [],
    }
    guarded = direct._guard_judgement(
        value, own_page={"body": "よくある質問"}, competitor_manifest={"sources": []},
        capability_paths=set(), evidence_dir=tmp_path, effects_path=tmp_path / "effects.jsonl",
        minimum_epoch=0, now=1,
    )
    assert guarded["decision"] == "no_op" and guarded["service_id"] is None


def test_presend_guard_rejects_a_stale_faq_absence():
    judgement = {"decision": "change", "service_id": direct.TARGET_SERVICE_ID,
                 "changed_field": "FAQ", "before_value": "FAQ_ABSENT"}
    try:
        direct._presend_guard(judgement, {"body": "現在のよくある質問"})
    except RuntimeError as error:
        assert str(error) == "presend_current_value_changed"
    else:
        raise AssertionError("stale FAQ absence accepted")


def test_service_contract_binds_official_scope_price_and_dedupes(tmp_path):
    text = "ホーム\nIT相談\n画像認識\nタイトル\nキャッチ\n評価 -\nサービス内容\nOpenCV PoC\n購入にあたってのお願い"
    source = {
        "service_id": "91000001", "public_url": "https://coconala.com/services/91000001",
        "title": "OpenCV画像認識", "state": "公開中", "price_jpy": 20000,
        "category": "IT相談/プログラミング", "public_text": text,
        "public_content_sha256": direct.hashlib.sha256(text.encode()).hexdigest(),
    }
    contract = direct._service_contract(source, "2026-08-15T00:00:00+00:00")
    changed = direct._service_contract({**source, "price_jpy": 30000}, "2026-08-15T00:01:00+00:00")
    assert contract["service_version_sha256"] != changed["service_version_sha256"]
    path = tmp_path / "offer-contracts.jsonl"
    assert direct._append_contract_once(path, contract) is True
    assert direct._append_contract_once(path, contract) is False
    assert len(path.read_text().splitlines()) == 1


def test_service_contract_requires_exact_coconala_heading_lines():
    invalid_texts = (
        "サービス内容\nOpenCV PoC",
        "購入にあたってのお願い\nOpenCV PoC",
        "サービス内容（補足）\n購入にあたってのお願い",
        "サービス内容\n購入にあたってのお願い（補足）",
        "前置きサービス内容\n購入にあたってのお願い",
        "サービス内容\n前置き購入にあたってのお願い",
    )
    for text in invalid_texts:
        source = {
            "service_id": "91000001", "public_url": "https://coconala.com/services/91000001",
            "title": "OpenCV画像認識", "state": "公開中", "price_jpy": 20000,
            "category": "IT相談/プログラミング", "public_text": text,
            "public_content_sha256": direct.hashlib.sha256(text.encode()).hexdigest(),
        }
        try:
            direct._service_contract(source, "2026-08-15T00:00:00+00:00")
        except RuntimeError as error:
            assert str(error) == "official_service_contract_invalid"
        else:
            raise AssertionError(f"near-match public text accepted: {text!r}")


def test_exact_faq_is_the_only_seller_field_and_public_delta():
    question, answer = direct._split_faq("よくある質問\n\nQ. 何を準備しますか？\nA. 対象画像をご共有ください。")
    base = [{"name": "data[Service][overview]", "value": "same", "checked": False}]
    before_form = {"url": "https://coconala.com/mypage/services/91000001", "fields": base}
    after_form = {"url": before_form["url"], "fields": base + [
        {"name": "data[Faq][0][question]", "value": question, "checked": False},
        {"name": "data[Faq][0][answer]", "value": answer, "checked": False},
    ]}
    direct._validate_form_delta(before_form, after_form, question, answer)
    direct._validate_public_acceptance(
        {"url": "https://coconala.com/services/91000001", "body": "before", "content_sha256": "a" * 64},
        {"url": "https://coconala.com/services/91000001", "body": question + answer, "content_sha256": "b" * 64},
        question, answer,
    )

    changed = {"url": before_form["url"], "fields": [
        {"name": "data[Service][overview]", "value": "different", "checked": False},
        *after_form["fields"][1:],
    ]}
    try:
        direct._validate_form_delta(before_form, changed, question, answer)
    except RuntimeError as error:
        assert str(error) == "seller_form_non_faq_changed"
    else:
        raise AssertionError("second changed field accepted")


def test_pending_effect_recovers_only_from_both_exact_public_values(tmp_path):
    intent_path = direct._effect_intent_path(tmp_path, "experiment")
    intent_path.parent.mkdir()
    intent_path.write_text(json.dumps({
        "status": "prepared", "question": "exact question", "answer": "exact answer",
        "experiment_key": "experiment",
    }))
    assert direct._pending_recovery(tmp_path, {"body": "exact question\nexact answer"})["intent_path"] == str(intent_path)
    assert direct._pending_recovery(tmp_path, {"body": "neither"}) is None
    try:
        direct._pending_recovery(tmp_path, {"body": "exact question only"})
    except RuntimeError as error:
        assert str(error) == "pending_effect_partial_public_readback"
    else:
        raise AssertionError("partial effect accepted")


def test_public_observation_expands_folded_faq_before_readback(tmp_path, monkeypatch):
    import listing_inventory

    seen = {}

    async def observed(_ws, url, expression):
        seen["expression"] = expression
        return {"url": url, "title": "official", "body": "exact question\nexact answer"}

    monkeypatch.setattr(listing_inventory, "_eval_json", observed)
    row = direct._observe_own_page("ws://leased", tmp_path)

    assert 'aria-controls^="serviceContentsFaqAnswer"' in seen["expression"]
    assert 'aria-expanded="false"' in seen["expression"]
    assert row["body"] == "exact question\nexact answer"


def test_effect_ledger_append_is_idempotent(tmp_path):
    ledger = tmp_path / "effects.jsonl"
    row = {"status": "accepted", "effect": 1, "experiment_key": "same"}
    assert direct._append_effect_once(ledger, row) is True
    assert direct._append_effect_once(ledger, row) is False
    assert len(ledger.read_text().splitlines()) == 1
    ledger.write_text("not-json\n")
    try:
        direct._append_effect_once(ledger, row)
    except RuntimeError as error:
        assert str(error) == "effect_ledger_invalid"
    else:
        raise AssertionError("corrupt effect ledger ignored")
