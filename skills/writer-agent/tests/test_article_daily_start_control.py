import importlib.util
import json
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


class ArticleStartPolicyTest(unittest.TestCase):
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
