import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/writer-agent/scripts"))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


START = load(
    "article_daily_start_control",
    ROOT / "skills/writer-agent/scripts/article_daily_start_control.py",
)
RESUME = load(
    "publication_resume",
    ROOT / "skills/writer-agent/scripts/publication_resume.py",
)
QUARANTINE = load(
    "quarantine_invalid_run",
    ROOT / "skills/writer-agent/scripts/quarantine_invalid_run.py",
)


class ArticleStartPolicyTest(unittest.TestCase):
    def _duplicate_media_run(self, root: Path, *, live: bool = False, status: str | None = None):
        run = root / "runs" / "daily-2026-08-21"
        gates = run / "gates"
        gates.mkdir(parents=True)
        headline = run / "headline-image.png"
        body = run / "body-diagram.png"
        headline.write_bytes(b"same-media")
        body.write_bytes(b"same-media")
        state_path = gates / "publication-state.json"
        pairs = {
            f"{platform}/{lang}": {"status": "unavailable"}
            for platform, lang in START.ACTIVE_REQUIRED
        }
        pairs["note/ja"]["status"] = status or ("live" if live else "unavailable")
        state_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "publication_contract": "active-four",
                    "run_id": run.name,
                    "run_dir": str(run.resolve()),
                    "state_path": str(state_path.resolve()),
                    "ledger_path": str((root / "articles.jsonl").resolve()),
                    "media": {
                        "headline_image": {"path": str(headline)},
                        "body_assets": [{"path": str(body)}],
                    },
                    "pairs": pairs,
                }
            ),
            encoding="utf-8",
        )
        (root / "articles.jsonl").write_text("", encoding="utf-8")
        return run

    def test_duplicate_media_quarantine_releases_same_day_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = self._duplicate_media_run(root)
            receipt = QUARANTINE.quarantine(root, run.name)
            with patch.object(START, "validated_live_set", return_value=(False, None)):
                decision = START.decide(root, "2026-08-21")
        self.assertEqual(receipt["reason"], "duplicate-media")
        self.assertEqual(decision["action"], "new")
        self.assertEqual(decision["reason"], "same-jst-day-invalid-media-proof")

    def test_quarantine_refuses_live_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = self._duplicate_media_run(root, live=True)
            with self.assertRaises(QUARANTINE.QuarantineError):
                QUARANTINE.quarantine(root, run.name)

    def test_quarantine_refuses_ambiguous_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = self._duplicate_media_run(root, status="ambiguous")
            with self.assertRaises(QUARANTINE.QuarantineError):
                QUARANTINE.quarantine(root, run.name)
            with patch.object(START, "validated_live_set", return_value=(False, None)):
                self.assertEqual(START.decide(root, "2026-08-21")["action"], "block-incomplete")

    def test_terminalize_invalid_pair_under_shared_lock_then_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = self._duplicate_media_run(root)
            state_path = run / "gates" / "publication-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["pairs"]["x-article/ja"] = {
                "status": "intent",
                "target": "https://x.example/draft/1",
            }
            state_path.write_text(json.dumps(state), encoding="utf-8")
            before_ledger = (root / "articles.jsonl").read_bytes()
            entry = QUARANTINE.terminalize_pair(
                root, run.name, "x-article/ja", "duplicate-media-quarantine"
            )
            receipt = QUARANTINE.quarantine(root, run.name)
            after = json.loads(state_path.read_text(encoding="utf-8"))
            after_ledger = (root / "articles.jsonl").read_bytes()
        self.assertEqual(entry["status"], "unavailable")
        self.assertEqual(after["pairs"]["x-article/ja"]["target"], "https://x.example/draft/1")
        self.assertEqual(after_ledger, before_ledger)
        self.assertEqual(receipt["reason"], "duplicate-media")

    def test_quarantine_rejects_ambiguous_same_run_ledger_publication_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = self._duplicate_media_run(root)
            (root / "articles.jsonl").write_text(
                json.dumps({"run_id": run.name, "published": "false"}) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(QUARANTINE.QuarantineError):
                QUARANTINE.quarantine(root, run.name)

    def test_quarantine_receipt_tamper_does_not_authorize_or_block_fresh_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = self._duplicate_media_run(root)
            QUARANTINE.quarantine(root, run.name)
            receipt = run / "gates" / "run-quarantine.json"
            tampered = json.loads(receipt.read_text(encoding="utf-8"))
            tampered["created_at"] = "forged"
            receipt.write_text(json.dumps(tampered), encoding="utf-8")
            self.assertFalse(QUARANTINE.receipt_is_valid(run, run.name))
            with patch.object(START, "validated_live_set", return_value=(False, None)):
                self.assertEqual(START.decide(root, "2026-08-21")["action"], "new")

    def test_quarantine_gates_symlink_stays_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = self._duplicate_media_run(root)
            shutil.rmtree(run / "gates")
            outside = root / "outside"
            outside.mkdir()
            (run / "gates").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(QUARANTINE.QuarantineError):
                QUARANTINE.quarantine(root, run.name)

    def test_completed_active_four_releases_new_run_same_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            run = state / "runs" / "daily-2026-08-21"
            (run / "gates").mkdir(parents=True)
            state_path = run / "gates" / "publication-state.json"
            state_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "publication_contract": "active-four",
                        "run_id": run.name,
                        "state_path": str(state_path),
                        "ledger_path": str(state / "articles.jsonl"),
                    }
                ),
                encoding="utf-8",
            )

            def live_set(_rows, _run_id, required):
                return (required == START.ACTIVE_REQUIRED, "topic-1")

            with patch.object(START, "validated_live_set", side_effect=live_set):
                decision = START.decide(state, "2026-08-21")

        self.assertEqual(decision["action"], "new")
        self.assertEqual(decision["run_id"], "")
        self.assertEqual(
            decision["reason"], "new-after-complete:active-four"
        )

    def test_exhausted_prepublication_archive_releases_new_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            run = state / "runs" / "20260821-072939"
            (run / "gates" / "judge-broker").mkdir(parents=True)
            (run / "gates" / "judge-broker" / "heartbeat").write_text("x")
            archive = state / "interrupted-generation" / run.name / "attempt-4"
            (archive / "gates").mkdir(parents=True)
            for relative in (
                "article-en.md", "article-ja.md", "headline-image.png",
                "body-diagram.png", "gates/quality-terminal-en.json",
                "gates/quality-terminal-ja.json",
            ):
                path = archive / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("archived", encoding="utf-8")
            manifest = [
                {"path": relative, "sha256": hashlib.sha256(
                    (archive / relative).read_bytes()
                ).hexdigest()}
                for relative in (
                    "article-en.md", "article-ja.md", "headline-image.png",
                    "body-diagram.png", "gates/quality-terminal-en.json",
                    "gates/quality-terminal-ja.json",
                )
            ]
            state_value = {
                "version": 1,
                "run_id": run.name,
                "prompt_sha256": "a" * 64,
                "status": "interrupted-safe",
                "maximum_attempts": 3,
                "maximum_empty_interruption_recoveries": 1,
                "attempts": [
                    {"attempt": 1, "status": "interrupted-safe", "return_code": 143, "archive_manifest": []},
                    {"attempt": 2, "status": "interrupted-safe", "return_code": 143, "archive_manifest": manifest},
                    {"attempt": 3, "status": "interrupted-safe", "return_code": 143, "archive_manifest": manifest},
                    {"attempt": 4, "status": "interrupted-safe", "return_code": 124, "archive_manifest": manifest},
                ],
            }
            state_path = archive / "generation-state.json"
            state_path.write_text(json.dumps(state_value), encoding="utf-8")
            state_hash = hashlib.sha256(state_path.read_bytes()).hexdigest()
            manifest_hash = hashlib.sha256(
                json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            (archive / "generation-exhaustion-receipt.json").write_text(
                json.dumps({
                    "schema": "writer.generation-exhaustion-receipt",
                    "version": 1, "run_id": run.name, "attempt": 4,
                    "status": "interrupted-safe", "return_code": 124,
                    "charged_attempts": 3, "maximum_attempts": 3,
                    "state_sha256": state_hash,
                    "archive_manifest_sha256": manifest_hash,
                    "publication_state_absent": True, "public_ledger_rows": 0,
                }),
                encoding="utf-8",
            )
            (state / "articles.jsonl").write_text("", encoding="utf-8")

            with patch.object(START, "validated_live_set", return_value=(False, None)):
                decision = START.decide(state, "2026-08-21")

        self.assertEqual(decision["action"], "new")
        self.assertEqual(decision["run_id"], "")
        self.assertEqual(
            decision["reason"], "same-jst-day-exhausted-prepublication-archive"
        )

    def test_legacy_exact8_partial_active_subset_stays_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            run = state / "runs" / "daily-2026-08-21"
            (run / "gates").mkdir(parents=True)
            state_path = run / "gates" / "publication-state.json"
            state_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "publication_contract": "legacy-exact8",
                        "run_id": run.name,
                        "state_path": str(state_path),
                        "ledger_path": str(state / "articles.jsonl"),
                    }
                ),
                encoding="utf-8",
            )

            def live_set(_rows, _run_id, required):
                return (required == START.ACTIVE_REQUIRED, "topic-1")

            with patch.object(START, "validated_live_set", side_effect=live_set), patch.object(
                START, "publication_plan", return_value={"resumable": True}
            ):
                decision = START.decide(state, "2026-08-21")

        self.assertNotEqual(decision["action"], "new")
        self.assertEqual(decision["action"], "skip-pending-worker")

    def test_pending_active_four_remains_resume_worker_owned(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            run = state / "runs" / "daily-2026-08-21"
            (run / "gates").mkdir(parents=True)
            state_path = run / "gates" / "publication-state.json"
            state_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "publication_contract": "active-four",
                        "run_id": run.name,
                        "state_path": str(state_path),
                        "ledger_path": str(state / "articles.jsonl"),
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(START, "validated_live_set", return_value=(False, None)), patch.object(
                START, "publication_plan", return_value={"resumable": True}
            ):
                decision = START.decide(state, "2026-08-21")

        self.assertEqual(decision["action"], "skip-pending-worker")

    def test_invalid_publication_state_contract_never_releases_new_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            run = state / "runs" / "daily-2026-08-21"
            (run / "gates").mkdir(parents=True)
            (run / "gates" / "publication-state.json").write_text(
                json.dumps(
                    {
                        "version": 999,
                        "publication_contract": "active-four",
                        "run_id": "wrong-run",
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(START, "validated_live_set", return_value=(True, "topic-1")), patch.object(
                START, "publication_plan", return_value={"resumable": True}
            ):
                decision = START.decide(state, "2026-08-21")

        self.assertEqual(decision["action"], "skip-pending-worker")

    def test_published_hashes_are_identity_scoped(self):
        digest = "a" * 64
        rows = [
            {"published": True, "lang": "ja", "artifact_sha256": digest},
            {"published": False, "lang": "en", "artifact_sha256": digest},
            {"published": True, "lang": "ja", "artifact_sha256": "invalid"},
        ]
        self.assertEqual(RESUME.PublicationStore._published_artifact_hashes(rows), {("ja", digest)})

    def test_existing_state_rechecks_cross_run_hash_at_publish_boundary(self):
        digest = "b" * 64
        store = RESUME.PublicationStore.__new__(RESUME.PublicationStore)
        store._ledger_rows_locked = lambda: [
            {
                "run_id": "daily-2026-08-20",
                "published": True,
                "lang": "ja",
                "artifact_sha256": digest,
            }
        ]
        state = {
            "run_id": "daily-2026-08-21",
            "pairs": {"note/ja": {"lang": "ja"}},
            "drafts": {"ja": {"sha256": digest}},
        }
        with self.assertRaises(RESUME.InvariantError):
            store._assert_no_duplicate_published_artifact_locked(state, "note/ja")


if __name__ == "__main__":
    unittest.main()
