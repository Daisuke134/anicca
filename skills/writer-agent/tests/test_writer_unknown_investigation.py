import hashlib
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "writer_unknown_investigation.py"
SPEC = importlib.util.spec_from_file_location("writer_unknown_investigation", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_primary_research_receipt_closes_only_the_documentation_gap(tmp_path: Path) -> None:
    fingerprint = "f" * 64
    queue = {
        "schema": "writer.self-heal.incident-queue",
        "version": 1,
        "items": {
            fingerprint: {
                "state": "CLAIMED",
                "phase": "destination:zenn-article/ja",
                "reason": "zenn-stage-timeout-no-dispatch-result",
                "classification": "process",
                "occurrences": [{"execution_id": "publisher-run-bad"}],
            }
        },
    }
    evidence = {
        "schema": "writer.observability.evidence-index",
        "version": 1,
        "run_id": "run-bad",
        "incidents": [{
            "phase": "destination:zenn-article/ja",
            "reason": "zenn-stage-timeout-no-dispatch-result",
            "trace_id": "trace-bad",
            "span_id": "span-bad",
            "source_receipt": {"path": "gates/publication-state.json", "sha256": "a" * 64},
            "source_release": "release-bad",
            "safe_logs": [{"path": "gates/platform-dispatch-results.jsonl", "sha256": "b" * 64}],
            "browser_evidence": [{"kind": "network", "path": "observability/network.json", "sha256": "c" * 64}],
        }],
    }
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "articles.jsonl").write_text(
        json.dumps({
            "platform": "zenn",
            "lang": "ja",
            "run_id": "run-good",
            "published": True,
            "live_url": "https://zenn.dev/example/articles/good-article1",
            "published_at": "2026-08-01T00:00:00Z",
        }) + "\n",
        encoding="utf-8",
    )
    research_path = tmp_path / "primary-research.json"
    research = {
        "schema": "writer.self-heal.primary-research",
        "version": 1,
        "observed_at": "2026-08-06T19:30:00+09:00",
        "sources": [{
            "title": "Zenn CLIで記事・本を管理する方法",
            "url": "https://zenn.dev/zenn/articles/zenn-cli-guide",
            "quote": "publishedオプションがtrueになっていることを確認したうえで、ファイルをコミットし、連携リポジトリにプッシュします。",
        }],
        "finding": "A draft commit is not a public publication receipt.",
    }
    research_path.write_text(json.dumps(research, ensure_ascii=False), encoding="utf-8")

    result = MODULE.investigate(
        queue,
        fingerprint,
        evidence,
        state_dir,
        "2026-08-06T19:31:00+09:00",
        research_path,
    )

    assert "official_primary_document_research_required" not in result["evidence_gaps"]
    assert result["primary_research"] == {
        "path": str(research_path.resolve()),
        "sha256": hashlib.sha256(research_path.read_bytes()).hexdigest(),
        "sources": research["sources"],
        "finding": research["finding"],
    }
    assert result["cause_status"] == "UNDETERMINED"


def test_preexisting_draft_effect_becomes_a_bounded_cause_hypothesis(tmp_path: Path) -> None:
    fingerprint = "e" * 64
    queue = {
        "schema": "writer.self-heal.incident-queue",
        "version": 1,
        "items": {
            fingerprint: {
                "state": "CLAIMED",
                "phase": "destination:zenn-article/ja",
                "reason": "zenn-stage-timeout-no-dispatch-result",
                "classification": "process",
                "occurrences": [{"execution_id": "publisher-run-bad"}],
            }
        },
    }
    evidence = {
        "schema": "writer.observability.evidence-index",
        "version": 1,
        "run_id": "run-bad",
        "incidents": [{
            "phase": "destination:zenn-article/ja",
            "reason": "zenn-stage-timeout-no-dispatch-result",
            "trace_id": "trace-bad",
            "span_id": "span-bad",
            "source_receipt": {"path": "gates/publication-state.json", "sha256": "a" * 64},
            "source_release": "release-bad",
            "safe_logs": [{"path": "gates/platform-dispatch-results.jsonl", "sha256": "b" * 64}],
            "browser_evidence": [{"kind": "network", "path": "observability/network.json", "sha256": "c" * 64}],
        }],
    }
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "articles.jsonl").write_text("", encoding="utf-8")
    effect_path = tmp_path / "preexisting-effect.json"
    effect = {
        "schema": "writer.self-heal.preexisting-effect",
        "version": 1,
        "observed_at": "2026-08-06T18:07:14+09:00",
        "effect_at": "2026-08-06T18:05:11+09:00",
        "failure_at": "2026-08-06T18:07:14+09:00",
        "effect_kind": "draft",
        "target": "2026-08-06-ai4",
        "public": False,
        "effect_receipts": [
            {"kind": "git-commit", "value": "098b55e", "sha256": "d" * 64},
            {"kind": "dispatch-result", "value": "status:ok", "sha256": "e" * 64},
        ],
    }
    effect_path.write_text(json.dumps(effect), encoding="utf-8")

    result = MODULE.investigate(
        queue,
        fingerprint,
        evidence,
        state_dir,
        "2026-08-06T19:31:00+09:00",
        preexisting_effect_path=effect_path,
    )

    assert result["cause_status"] == "EVIDENCE_BACKED_HYPOTHESIS"
    assert result["cause_hypothesis"] == (
        "preexisting_draft_was_not_reconciled_before_timeout_classification"
    )
    assert result["preexisting_effect"]["sha256"] == hashlib.sha256(
        effect_path.read_bytes()
    ).hexdigest()
    assert result["next_action"] == "CHARACTERIZE_PREEXISTING_EFFECT_RECONCILIATION"
    assert result["preexisting_effect"]["public"] is False
