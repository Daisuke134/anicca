"""Contract tests for the bounded, tool-less reply semantic route."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


GIG_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = GIG_ROOT / "agent-runner" / "agent_runner.py"
RUNNER_CONFIG = GIG_ROOT / "agent-runner" / "config.json"
REQUESTED_ESTIMATE_PATH = GIG_ROOT / "scripts" / "requested_estimate.py"
QUEUE_SNAPSHOT_PATH = GIG_ROOT / "scripts" / "coconala_queue_snapshot.py"
LAUNCHD_PATH = GIG_ROOT / "config" / "launchd-jobs.json"
sys.path.insert(0, str(RUNNER_PATH.parent))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load_module("gig_agent_runner_reply_semantic_test", RUNNER_PATH)
requested_estimate = _load_module(
    "gig_requested_estimate_reply_semantic_test", REQUESTED_ESTIMATE_PATH,
)
queue_snapshot = _load_module(
    "gig_queue_snapshot_reply_semantic_test", QUEUE_SNAPSHOT_PATH,
)


def test_reply_semantic_route_prefers_luna_and_has_bounded_provider_fallback():
    config = json.loads(RUNNER_CONFIG.read_text(encoding="utf-8"))
    composition = config["task_classes"]["composition-agent"]
    route = config["task_classes"]["reply-semantic-agent"]

    assert route["route"] == "luna-medium-reply-semantic-with-provider-fallback"
    assert route["timeout_seconds"] == 120
    assert route["token_reservation"] <= composition["token_reservation"]
    assert route["candidates"][0] == {
        "provider": "codex", "model": "gpt-5.6-luna", "effort": "medium",
    }
    assert [candidate["provider"] for candidate in route["candidates"]] == [
        "codex", "claude-direct", "hermes",
    ]
    assert "reply-semantic-agent" in runner.TOOLLESS_TASK_CLASSES


def test_runner_cli_accepts_reply_semantic_task_class():
    result = subprocess.run(
        [sys.executable, str(RUNNER_PATH), "--help"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "reply-semantic-agent" in result.stdout


def test_reply_semantic_task_is_tool_starved_for_codex_and_claude(tmp_path):
    args = argparse.Namespace(
        task_class="reply-semantic-agent",
        schema=tmp_path / "schema.json",
        workdir=tmp_path,
        image=[],
        read_only=False,
    )
    args.schema.write_text("{}", encoding="utf-8")

    for task_class in runner.TOOLLESS_TASK_CLASSES:
        args.task_class = task_class
        codex_command = runner.command_for(
            "codex", "codex", {},
            {"provider": "codex", "model": "gpt-5.6-luna", "effort": "medium"},
            args, "bounded prompt", {}, tmp_path / f"result-{task_class}.json", 60, None,
            prompt_via_stdin=True,
        )
        sandbox_index = codex_command.index("--sandbox")
        assert codex_command[sandbox_index:sandbox_index + 2] == ["--sandbox", "read-only"]
        for feature in ("shell_tool", "code_mode_host", "unified_exec"):
            disable_index = codex_command.index(feature)
            assert codex_command[disable_index - 1:disable_index + 1] == ["--disable", feature]

    args.task_class = "tool-agent"
    ordinary_command = runner.command_for(
        "codex", "codex", {},
        {"provider": "codex", "model": "gpt-5.6-luna", "effort": "medium"},
        args, "bounded prompt", {}, tmp_path / "result-tool.json", 60, None,
        prompt_via_stdin=True,
    )
    assert not any(
        ordinary_command[index:index + 2] == ["--disable", feature]
        for index in range(len(ordinary_command) - 1)
        for feature in ("shell_tool", "code_mode_host", "unified_exec")
    )

    args.task_class = "reply-semantic-agent"
    claude_command = runner.command_for(
        "claude-direct", "claude", {},
        {"provider": "claude-direct", "model": "sonnet"},
        args, "bounded prompt", {}, tmp_path / "result-claude.json", 60, None,
        prompt_via_stdin=True,
    )
    tools_index = claude_command.index("--tools")
    assert claude_command[tools_index:tools_index + 2] == ["--tools", ""]


def test_semantic_judge_uses_fast_task_class_and_bounded_outer_timeout(tmp_path, monkeypatch):
    schema = GIG_ROOT / "schemas" / "reply_semantic_judgement.schema.json"
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        evidence = Path(argv[argv.index("--evidence-dir") + 1])
        result_path = evidence / "result.json"
        result_path.write_text("{}", encoding="utf-8")
        (evidence / "summary.json").write_text(json.dumps({
            "status": "success", "result_path": str(result_path),
        }), encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(requested_estimate.subprocess, "run", fake_run)
    monkeypatch.setattr(
        requested_estimate,
        "validate_semantic_judgement",
        lambda _payload, _rows: {"next_action": "reply"},
    )
    judge = requested_estimate.SemanticJudge(
        runner=RUNNER_PATH,
        schema=schema,
        workdir=tmp_path,
        evidence_root=tmp_path / "evidence",
    )
    judge({
        "url": "https://coconala.com/messages/123",
        "title": "メッセージ詳細",
        "container_present": True,
        "own_user_path": "/users/seller",
        "messages": [
            {"message_id": "seller-1", "author_path": "/users/seller",
             "body": "こんにちは", "sent_at": "2026-08-19T00:00:00Z"},
            {"message_id": "buyer-1", "author_path": "/users/buyer",
             "body": "質問です", "sent_at": "2026-08-19T00:01:00Z"},
        ],
    }, "https://coconala.com/messages/123")

    assert len(calls) == 1
    argv, kwargs = calls[0]
    assert argv[argv.index("--task-class") + 1] == "reply-semantic-agent"
    assert argv[argv.index("--timeout-seconds") + 1] == "120"
    assert kwargs["timeout"] == 150


def test_semantic_judge_accepts_compatible_receipts_and_rejects_unknown_profile(tmp_path):
    schema = GIG_ROOT / "schemas" / "reply_semantic_judgement.schema.json"
    judge = requested_estimate.SemanticJudge(
        runner=RUNNER_PATH,
        schema=schema,
        workdir=tmp_path,
        evidence_root=tmp_path / "evidence",
    )
    dom = {
        "url": "https://coconala.com/messages/123",
        "title": "メッセージ詳細",
        "container_present": True,
        "own_user_path": "/users/seller",
        "messages": [
            {"message_id": "seller-1", "author_path": "/users/seller",
             "body": "こんにちは", "sent_at": "2026-08-19T00:00:00Z"},
            {"message_id": "buyer-1", "author_path": "/users/buyer",
             "body": "質問です", "sent_at": "2026-08-19T00:01:00Z"},
        ],
    }
    current = {
        "version": requested_estimate.SEMANTIC_RECEIPT_VERSION,
        "prompt_version": requested_estimate.SEMANTIC_PROMPT_VERSION,
        "runner_profile": requested_estimate.SEMANTIC_RUNNER_PROFILE,
        "schema_sha256": judge.schema_sha256,
        "seller_facts_sha256": judge.seller_facts_sha256,
        "context_sha256": requested_estimate.semantic_context_sha256(
            requested_estimate.semantic_conversation(dom),
        ),
        "official_context_sha256": "b" * 64,
        "latest_message_identity": "buyer-1",
        "judgement": {
            "conversation_state": "question",
            "next_action": "reply",
            "cycle_start_message_id": "buyer-1",
            "evidence_message_ids": ["buyer-1"],
            "required_official_context": "none",
            "estimate_terms": None,
            "reply_body": "回答です",
            "reply_audit": {
                "answered_buyer_message_ids": ["buyer-1"],
                "unanswered_questions": [],
                "unsupported_claims": [],
                "unrequested_cta": False,
                "repeats_seller_message": False,
                "off_platform_contact": False,
            },
            "uncertainty": [],
        },
    }

    assert requested_estimate.SEMANTIC_RUNNER_PROFILE == "reply-semantic-agent"
    assert judge.receipt_current(current) is True
    legacy = {**current, "runner_profile": "composition-agent"}
    assert judge.receipt_current(legacy) is True
    assert requested_estimate.project_semantic_receipt(
        dom, "https://coconala.com/messages/123", legacy,
    )["semantic_reply_body"] == "回答です"
    assert judge.receipt_current({**current, "runner_profile": "unknown-agent"}) is False


def test_semantic_judge_uses_one_bounded_runner_attempt(tmp_path, monkeypatch):
    schema = GIG_ROOT / "schemas" / "reply_semantic_judgement.schema.json"
    calls = []

    def failed_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 1, "", "failed")

    monkeypatch.setattr(requested_estimate.subprocess, "run", failed_run)
    judge = requested_estimate.SemanticJudge(
        runner=RUNNER_PATH,
        schema=schema,
        workdir=tmp_path,
        evidence_root=tmp_path / "evidence",
    )

    with pytest.raises(requested_estimate.SemanticJudgementError, match="runner_failed"):
        judge({
            "url": "https://coconala.com/messages/123",
            "title": "メッセージ詳細",
            "container_present": True,
            "own_user_path": "/users/seller",
            "messages": [
                {"message_id": "seller-1", "author_path": "/users/seller",
                 "body": "こんにちは", "sent_at": "2026-08-19T00:00:00Z"},
                {"message_id": "buyer-1", "author_path": "/users/buyer",
                 "body": "質問です", "sent_at": "2026-08-19T00:01:00Z"},
            ],
        }, "https://coconala.com/messages/123")

    assert len(calls) == 1
    assert calls[0][1]["timeout"] == judge.timeout_seconds + 30


def test_direct_inbox_parser_defaults_semantic_timeout_to_120(tmp_path):
    args = queue_snapshot.argument_parser().parse_args([
        "--output", str(tmp_path / "out.json"),
        "--evidence-dir", str(tmp_path / "evidence"),
        "--mode", "direct-inbox-only",
    ])

    assert args.semantic_timeout_seconds == 120


def test_negotiate_runs_every_30_seconds_without_changing_other_job_intervals():
    jobs = json.loads(LAUNCHD_PATH.read_text(encoding="utf-8"))["jobs"]
    by_lane = {job["lane"]: job for job in jobs}

    assert by_lane["negotiate"]["KeepAlive"] is True
    assert "StartInterval" not in by_lane["negotiate"]
    negotiate_program = by_lane["negotiate"]["program"]
    assert negotiate_program[-5:] == ["--continuous", "--poll-seconds", "30", "--workers", "2"]
    assert by_lane["negotiate"]["ThrottleInterval"] == 30
    assert (by_lane["apply"]["StartInterval"], by_lane["apply"]["ThrottleInterval"]) == (60, 60)
    assert (by_lane["storefront"]["StartInterval"], by_lane["storefront"]["ThrottleInterval"]) == (60, 60)
    assert (by_lane["paid"]["StartInterval"], by_lane["paid"]["ThrottleInterval"]) == (300, 60)
    assert (by_lane["release"]["StartInterval"], by_lane["release"]["ThrottleInterval"]) == (300, 60)
    assert by_lane["browser"].get("StartInterval") is None
    assert by_lane["browser"]["ThrottleInterval"] == 30


def test_semantic_prompt_v15_uses_verified_application_scope_without_blanket_refusal():
    prompt = requested_estimate.semantic_prompt(
        [{"message_id": "buyer-1", "role": "buyer", "sent_at": "2026-08-19T00:00:00Z", "body": "質問です"}],
        official_context=None,
        seller_facts=[],
    )

    assert requested_estimate.SEMANTIC_PROMPT_VERSION == "reply-negotiate-v15"
    assert "saas_lp_cvr_3_to_10_20260819" in requested_estimate.SELLER_FACT_IDS
    assert "公式応募" in prompt
    assert "current capability commitment" in prompt
    assert "required_official_context=application" in prompt
    assert "対応可能です" in prompt
    assert "対応可能とはお約束できません" not in prompt
    assert (
        "required_official_context=applicationは、特定の応募proposalのexact価格・納期・本文を参照しなければ答えられない時だけです。"
        "一般的な経験・能力・稼働可否の質問には使いません。"
    ) not in prompt
    assert "current buyerのcapability・対応scope・sampleを特定の応募applicationの明示scopeと照合" in prompt
    assert "application contextと無関係な一般的な経験・能力・稼働可否の質問だけでは使いません" in prompt
    assert "この会話で確認できる事実としては断言できません" not in prompt
    assert "未確認historyの不在や経験不足を自発的に説明したり、対応不可を先頭に置いたりしません" in prompt
    assert "selection sample/roughのexplicit buyer deadlineはinterim deadline" in prompt
    assert "later official final delivery dateとは別で、applied scope内ならclarifyせず受諾" in prompt
    assert "動画編集、字幕・テロップ挿入、映像加工、完成動画書き出しは対応不能です。" not in prompt
    assert "Care Earth Mart" in prompt
    assert "選定用ラフ" in prompt
    assert "SaaS/Wix LP" in prompt
    assert "3%" in prompt and "10%" in prompt
    assert "CTA" in prompt and "first-view" in prompt
    assert "CPA" in prompt
    assert "違法・危険・プラットフォーム禁止" in prompt


def test_verified_seller_facts_only_return_allowlisted_saas_fact(tmp_path):
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({
        "facts": [
            {
                "id": "saas_lp_cvr_3_to_10_20260819",
                "claim": "visitor-to-service-start conversion was approximately 3% to 10%",
                "evidence": "verified SaaS/Wix LP application context",
            },
            {
                "id": "unknown_unverified_fact",
                "claim": "invented customer result",
                "evidence": "untrusted note",
            },
        ],
    }, ensure_ascii=False), encoding="utf-8")

    facts = requested_estimate.verified_seller_facts(profile)

    assert facts == [{
        "id": "saas_lp_cvr_3_to_10_20260819",
        "claim": "visitor-to-service-start conversion was approximately 3% to 10%",
        "evidence": "verified SaaS/Wix LP application context",
    }]
    prompt = requested_estimate.semantic_prompt([], seller_facts=facts)
    assert "approximately 3% to 10%" in prompt
    assert "invented customer result" not in prompt
