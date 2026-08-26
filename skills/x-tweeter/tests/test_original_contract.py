from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "original_contract.py"


class OriginalContractTests(unittest.TestCase):
    def test_only_grounded_useful_novel_original_is_admitted(self) -> None:
        self.assertTrue(SCRIPT.is_file(), f"missing contract: {SCRIPT}")
        spec = importlib.util.spec_from_file_location("x_tweeter_original_contract", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = {
                "url": "https://example.com/official-ai-workflow",
                "title": "Official workflow guide",
                "text": "Validate the source before automating the next publishing handoff.",
                "source_kind": "official_documentation",
                "observed_at": "2026-08-24T00:00:00+00:00",
            }
            draft = {
                "text": "Validate the source before automating a publishing handoff. Keep the step only when recovery is clear.",
                "source_url": source["url"],
                "evidence_quote": "Validate the source before automating the next publishing handoff.",
                "reader_value": "A creator can test one handoff and its recovery path.",
                "value_types": ["procedure", "failure_condition"],
            }
            source_path, draft_path = root / "source.json", root / "draft.json"
            source_path.write_text(json.dumps(source)); draft_path.write_text(json.dumps(draft))
            source_sha = module.sha256_file(source_path)
            draft_sha = module.sha256_file(draft_path)
            critic = {
                "source_sha256": source_sha, "draft_sha256": draft_sha,
                "supported": True, "useful": True, "novel": True,
                "spam_risk": "low", "unsupported_claims": [],
                "near_duplicate_post_ids": [],
                "value_types": ["procedure", "failure_condition"],
                "reason": "The post adds a concrete test and recovery condition.",
            }
            critic_path = root / "critic.json"
            critic_path.write_text(json.dumps(critic))
            posted = root / "posted.jsonl"; posted.write_text("")

            admitted = module.admit(source_path, draft_path, critic_path, posted)

            self.assertEqual(admitted["state"], "READY_TO_PUBLISH")
            self.assertEqual(admitted["source_sha256"], source_sha)
            self.assertEqual(admitted["draft_sha256"], draft_sha)
            self.assertEqual(admitted["source_url"], source["url"])
            self.assertEqual(admitted["value_types"], ["failure_condition", "procedure"])

            posted.write_text(json.dumps({
                "post_url": "https://x.com/selawmqt/status/1",
                "text_sha256": admitted["text_sha256"],
            }) + "\n")
            with self.assertRaises(ValueError):
                module.admit(source_path, draft_path, critic_path, posted)

    def test_rejects_unbound_or_generic_model_output(self) -> None:
        spec = importlib.util.spec_from_file_location("x_tweeter_original_contract", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / "source.json"
            source_path.write_text(json.dumps({
                "url": "https://example.com/source", "title": "Source",
                "text": "One exact source fact.", "source_kind": "official_documentation",
                "observed_at": "2026-08-24T00:00:00+00:00",
            }))
            draft_path = root / "draft.json"
            draft_path.write_text(json.dumps({
                "text": "AI is changing everything.", "source_url": "https://example.com/source",
                "evidence_quote": "One exact source fact.", "reader_value": "AI matters.",
                "value_types": ["procedure"],
            }))
            critic_path = root / "critic.json"
            critic_path.write_text(json.dumps({
                "source_sha256": module.sha256_file(source_path),
                "draft_sha256": module.sha256_file(draft_path),
                "supported": True, "useful": False, "novel": False,
                "spam_risk": "high", "unsupported_claims": [],
                "near_duplicate_post_ids": ["recent-1"],
                "value_types": ["procedure"], "reason": "Generic and repetitive.",
            }))
            with self.assertRaises(ValueError):
                module.admit(source_path, draft_path, critic_path, root / "posted.jsonl")


if __name__ == "__main__":
    unittest.main()
