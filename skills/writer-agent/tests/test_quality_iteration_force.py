import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills/writer-agent/scripts"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


QUALITY = load("quality_self_heal_force", SCRIPTS / "quality_self_heal.py")
RESUME = load("publication_resume_force", SCRIPTS / "publication_resume.py")


def _write(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _quality_fixture(tmp_path: Path):
    run = tmp_path / "run"
    gates = run / "gates"
    gates.mkdir(parents=True)
    hashes = {}
    for lang in ("ja", "en"):
        draft = run / f"article-{lang}.md"
        draft.write_text(f"# {lang}\nbody\n", encoding="utf-8")
        digest = hashlib.sha256(draft.read_bytes()).hexdigest()
        hashes[lang] = digest
        _write(gates / f"editorial-{lang}.json", {
            "verdict": "FAIL", "article_sha256": digest, "fixes": ["fix"]
        })
        _write(gates / f"reader-testing-gate-{lang}.terminal.json", {
            "status": "revision-required",
            "article_sha256": digest,
            "payload": {"unanswered_questions": ["question"]},
        })
        _write(gates / f"identity-{lang}.json", {
            "verdict": "PASS", "article_sha256": digest
        })
    _write(gates / "topic-route.json", {
        "topic_id": "topic-1", "editorial_form": "explainer"
    })
    previous = None
    for index in range(1, 5):
        snapshot_dir = gates / f"quality-attempt-{index}"
        snapshot_dir.mkdir()
        snapshot_digests = {}
        for lang in ("ja", "en"):
            snapshot_digests[lang] = {}
            for kind, filename in {
                "editorial": f"editorial-{lang}.json",
                "reader": f"reader-testing-gate-{lang}.terminal.json",
                "identity": f"identity-{lang}.json",
            }.items():
                source = gates / filename
                target = snapshot_dir / filename
                target.write_bytes(source.read_bytes())
                snapshot_digests[lang][kind] = hashlib.sha256(
                    target.read_bytes()
                ).hexdigest()
        payload = {
            "run_id": run.name,
            "attempt": index,
            "fingerprint": f"old-{index}",
            "action": "reroute",
            "forbidden_editorial_form": "explainer",
            "publication_policy": "continuous",
            "quality": {
                lang: {"article_sha256": hashes[lang]}
                for lang in ("ja", "en")
            },
            "receipt_snapshots": snapshot_digests,
            "previous_receipt_sha256": previous,
        }
        payload["receipt_sha256"] = QUALITY._receipt_hash(payload)
        _write(gates / f"quality-self-heal-attempt-{index}.json", payload)
        previous = payload["receipt_sha256"]
    return run, hashes


def test_fifth_quality_iteration_emits_force_publish_advisory(tmp_path, monkeypatch):
    run, _hashes = _quality_fixture(tmp_path)
    monkeypatch.setenv("ARTICLE_PUBLICATION_POLICY", "continuous")
    result = QUALITY.assess(
        run,
        {"ja": run / "article-ja.md", "en": run / "article-en.md"},
    )
    assert result["action"] == "force_publish_advisory"
    assert result["force_publish_after_iterations"] == 5
    assert result["quality_advisory"] is True


def test_advisory_quality_requires_force_marker_before_init(tmp_path, monkeypatch):
    run, _hashes = _quality_fixture(tmp_path)
    gates = run / "gates"
    drafts = {lang: run / f"article-{lang}.md" for lang in ("ja", "en")}
    for lang in ("ja", "en"):
        draft = drafts[lang]
        digest = hashlib.sha256(draft.read_bytes()).hexdigest()
        _write(gates / f"quality-terminal-{lang}.json", {
            "status": "terminal", "lang": lang, "article_sha256": digest,
            "editorial_gate": "ADVISORY", "reader_gate": "ADVISORY",
            "identity_gate": "PASS", "safety_gate": "ALLOW",
        })
    monkeypatch.setenv("ARTICLE_PUBLICATION_POLICY", "continuous")
    with pytest.raises(RESUME.InvariantError, match="five-iteration force receipt"):
        RESUME.require_quality_terminals(run, drafts)
    QUALITY.assess(run, drafts)
    receipts = RESUME.require_quality_terminals(run, drafts)
    assert receipts["ja"]["editorial_gate"] == "ADVISORY"


def test_force_receipt_rejects_missing_or_tampered_chain_link(tmp_path, monkeypatch):
    run, _hashes = _quality_fixture(tmp_path)
    drafts = {lang: run / f"article-{lang}.md" for lang in ("ja", "en")}
    for lang in ("ja", "en"):
        digest = hashlib.sha256(drafts[lang].read_bytes()).hexdigest()
        _write(run / "gates" / f"quality-terminal-{lang}.json", {
            "status": "terminal", "lang": lang, "article_sha256": digest,
            "editorial_gate": "ADVISORY", "reader_gate": "ADVISORY",
            "identity_gate": "PASS", "safety_gate": "ALLOW",
        })
    monkeypatch.setenv("ARTICLE_PUBLICATION_POLICY", "continuous")
    QUALITY.assess(run, drafts)
    (run / "gates" / "quality-self-heal-attempt-3.json").unlink()
    with pytest.raises(RESUME.InvariantError, match="five-iteration force receipt"):
        RESUME.require_quality_terminals(run, drafts)
