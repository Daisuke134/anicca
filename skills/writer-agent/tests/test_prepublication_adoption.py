import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/writer-agent/scripts"))

import article_generation_state as generation


class PrepublicationAdoptionTest(unittest.TestCase):
    def fixture(self, root: Path):
        run_id = "20260829-165022"
        run = root / "runs" / run_id
        gates = run / "gates"
        gates.mkdir(parents=True)
        prompt = run / "article-daily-prompt.txt"
        prompt.write_text("immutable prompt\n", encoding="utf-8")
        ledger = root / "articles.jsonl"
        ledger.write_text(
            "\n".join(
                json.dumps(
                    {
                        "run_id": run_id,
                        "platform": platform,
                        "lang": lang,
                        "published": False,
                        "live_url": None,
                        "state": "pending:media",
                        "reality_gate": None,
                    }
                )
                for platform, lang in (
                    ("note", "ja"),
                    ("substack", "ja"),
                    ("substack", "en"),
                    ("x-article", "ja"),
                )
            )
            + "\n",
            encoding="utf-8",
        )
        state = generation.initialize(run, run_id, prompt, ledger)
        state["status"] = "provider-failed-ambiguous"
        state["attempts"] = [
            {
                "attempt": attempt,
                "status": "provider-failed-ambiguous",
                "return_code": 1,
                "boundary": "generated-or-staged-artifacts:article-ja.md",
            }
            for attempt in (1, 2, 3)
        ]
        (gates / "generation-state.json").write_text(
            json.dumps(state) + "\n", encoding="utf-8"
        )
        (run / "article-ja.md").write_text("日本語 draft\n", encoding="utf-8")
        (run / "article-en.md").write_text("English draft\n", encoding="utf-8")
        (gates / "editorial-ja.json").write_text('{"pass":false}\n', encoding="utf-8")
        (run / "headline-image.png").write_bytes(b"current image")
        return run, run_id, prompt, ledger

    def test_adopts_exact_exhausted_run_once_with_hash_bound_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, run_id, prompt, ledger = self.fixture(Path(tmp))
            state_path = run / "gates/generation-state.json"
            before = json.loads(state_path.read_text(encoding="utf-8"))

            result = generation.adopt_prepublication(run, run_id, prompt, ledger)

            state = json.loads(state_path.read_text(encoding="utf-8"))
            receipt_path = run / "gates/prepublication-adoption.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(result["action"], "adopted")
            self.assertEqual(state["status"], "quality-repair-ready")
            self.assertEqual(state["attempts"], before["attempts"])
            self.assertEqual(
                generation.resume_decision(run, run_id, prompt, ledger),
                {
                    "resumable": False,
                    "reason": "quality-repair-ready",
                    "status": "quality-repair-ready",
                },
            )
            self.assertEqual(receipt["from_status"], "provider-failed-ambiguous")
            self.assertEqual(receipt["to_status"], "quality-repair-ready")
            self.assertEqual(receipt["prompt_sha256"], generation.file_sha256(prompt))
            self.assertEqual(
                {item["path"] for item in receipt["draft_manifest"]},
                {"article-ja.md", "article-en.md"},
            )
            self.assertIn(
                "gates/editorial-ja.json",
                {item["path"] for item in receipt["artifact_manifest"]},
            )
            self.assertIn(
                "headline-image.png",
                {item["path"] for item in receipt["artifact_manifest"]},
            )
            state_bytes = state_path.read_bytes()
            receipt_bytes = receipt_path.read_bytes()

            replay = generation.adopt_prepublication(run, run_id, prompt, ledger)

            self.assertEqual(replay["action"], "unchanged")
            self.assertEqual(state_path.read_bytes(), state_bytes)
            self.assertEqual(receipt_path.read_bytes(), receipt_bytes)

            receipt["artifact_manifest_sha256"] = "0" * 64
            receipt["receipt_sha256"] = generation._adoption_receipt_hash(receipt)
            receipt_path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
            with self.assertRaises(generation.GenerationInvariant):
                generation.adopt_prepublication(run, run_id, prompt, ledger)

    def test_refuses_unsafe_evidence_before_mutation(self):
        cases = {
            "prompt hash drift": lambda run, prompt, ledger: prompt.write_text(
                "changed prompt\n", encoding="utf-8"
            ),
            "live row": lambda run, prompt, ledger: ledger.write_text(
                json.dumps({"run_id": run.name, "published": True}) + "\n",
                encoding="utf-8",
            ),
            "publication state": lambda run, prompt, ledger: (
                run / "gates/publication-state.json"
            ).write_text("{}\n", encoding="utf-8"),
            "symlink draft": self.replace_ja_with_symlink,
        }
        for name, mutate in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                run, run_id, prompt, ledger = self.fixture(Path(tmp))
                before = (run / "gates/generation-state.json").read_bytes()
                mutate(run, prompt, ledger)

                with self.assertRaises(generation.GenerationInvariant):
                    generation.adopt_prepublication(run, run_id, prompt, ledger)

                self.assertEqual(
                    (run / "gates/generation-state.json").read_bytes(), before
                )
                self.assertFalse((run / "gates/prepublication-adoption.json").exists())

    def test_cli_adopts_non_resumable_attempt_before_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, run_id, prompt, ledger = self.fixture(Path(tmp))
            state_path = run / "gates/generation-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["attempts"] = state["attempts"][:2]
            state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "skills/writer-agent/scripts/article_generation_state.py"),
                    "--run-dir",
                    str(run),
                    "--run-id",
                    run_id,
                    "--prompt-file",
                    str(prompt),
                    "--ledger",
                    str(ledger),
                    "adopt-prepublication",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["action"], "adopted")
            self.assertEqual(
                json.loads(state_path.read_text(encoding="utf-8"))["status"],
                "quality-repair-ready",
            )

    def test_recovers_receipt_written_before_state_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, run_id, prompt, ledger = self.fixture(Path(tmp))
            state_path = run / "gates/generation-state.json"
            before = state_path.read_bytes()
            generation.adopt_prepublication(run, run_id, prompt, ledger)
            receipt_path = run / "gates/prepublication-adoption.json"
            receipt = receipt_path.read_bytes()
            state_path.write_bytes(before)

            result = generation.adopt_prepublication(run, run_id, prompt, ledger)

            self.assertEqual(result["action"], "recovered")
            self.assertEqual(receipt_path.read_bytes(), receipt)
            self.assertEqual(
                json.loads(state_path.read_text(encoding="utf-8"))["status"],
                "quality-repair-ready",
            )

    @staticmethod
    def replace_ja_with_symlink(run: Path, prompt: Path, ledger: Path):
        article = run / "article-ja.md"
        target = run.parent.parent / "outside-ja.md"
        target.write_text("outside\n", encoding="utf-8")
        article.unlink()
        article.symlink_to(target)


if __name__ == "__main__":
    unittest.main()
