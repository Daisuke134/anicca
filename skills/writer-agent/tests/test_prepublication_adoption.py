import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/writer-agent/scripts"))

import article_generation_state as generation
import quality_repair_control as repair


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

    def test_quality_repair_plan_accepts_traceback_bound_adoption_and_begin_prepares_reader_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, run_id, prompt, ledger = self.fixture(Path(tmp))
            gates, traceback, quality_path = self.add_reader_traceback(run)
            generation.adopt_prepublication(run, run_id, prompt, ledger)
            adoption = json.loads(
                (gates / "prepublication-adoption.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                {
                    item["path"]: item["sha256"]
                    for item in adoption["artifact_manifest"]
                }["gates/quality-self-heal.json"],
                generation.file_sha256(quality_path),
            )

            decision = repair.plan(run, ledger)

            self.assertEqual(decision["status"], "READY")
            self.assertEqual(decision["run_id"], run_id)
            self.assertEqual(decision["source_defect"], "reader-terminal-receipt")
            self.assertEqual(
                decision["drafts"],
                {
                    "ja": generation.file_sha256(run / "article-ja.md"),
                    "en": generation.file_sha256(run / "article-en.md"),
                },
            )

            with patch.object(
                repair, "_quality_module", side_effect=AssertionError("must not assess")
            ):
                prepared = repair.begin(run, ledger)
            repair_state = json.loads(
                (gates / "quality-repair-state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                repair_state["qrr_lineage"], decision["qrr_lineage"]
            )

            self.assertEqual(prepared["status"], "prepared")
            self.assertEqual(prepared["quality_action"], "evaluate_reroute")
            prompt_text = Path(prepared["prompt_path"]).read_text(encoding="utf-8")
            self.assertIn("Run reader-testing-gate.sh for BOTH languages first", prompt_text)
            self.assertIn("editorial-gate.sh, identity-gate.sh, and reader-testing-gate.sh", prompt_text)
            self.assertIn("canonical media and CTA invariants", prompt_text)
            self.assertIn("quality_self_heal.py returns action=ready_to_freeze", prompt_text)
            archived = (
                run
                / "gates/quality-repair/epoch-1/original/quality-self-heal.json"
            )
            self.assertTrue(archived.is_file())
            self.assertEqual(archived.read_text(encoding="utf-8"), traceback)
            self.assertFalse((gates / "quality-self-heal.json").exists())
            self.assertFalse((run / "gates/publication-state.json").exists())
            self.assertFalse(generation.ledger_has_public_effect(ledger, run_id))

    def test_quality_repair_plan_refuses_missing_or_drifted_adoption_evidence(self):
        cases = {
            "missing receipt": lambda run, _prompt: (
                run / "gates/prepublication-adoption.json"
            ).unlink(),
            "traceback hash drift": lambda run, _prompt: (
                run / "gates/quality-self-heal.json"
            ).write_text(
                (run / "gates/quality-self-heal.json")
                .read_text(encoding="utf-8")
                .replace("line 132", "line 133"),
                encoding="utf-8",
            ),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                run, run_id, prompt, ledger = self.fixture(Path(tmp))
                self.add_reader_traceback(run)
                generation.adopt_prepublication(run, run_id, prompt, ledger)
                mutate(run, prompt)

                decision = repair.plan(run, ledger)

                self.assertEqual(decision["status"], "REFUSED")
                self.assertEqual(decision["run_id"] if "run_id" in decision else None, None)
                self.assertFalse((run / "gates/quality-repair-state.json").exists())

    def test_provider_failed_plan_never_creates_adoption(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, run_id, prompt, ledger = self.fixture(Path(tmp))
            self.add_reader_traceback(run)
            with patch.object(
                repair.generation_state,
                "adopt_prepublication",
                side_effect=AssertionError("provider-failed state must not adopt"),
            ):
                decision = repair.plan(run, ledger)

            self.assertEqual(decision["status"], "REFUSED")
            self.assertFalse((run / "gates/prepublication-adoption.json").exists())

    def test_reader_receipt_defect_requires_exact_trace_and_missing_terminal(self):
        cases = {
            "normal JSON": lambda gates: (gates / "quality-self-heal.json").write_text(
                '{"version":2,"action":"block_freeze"}\n', encoding="utf-8"
            ),
            "different traceback": lambda gates: (gates / "quality-self-heal.json").write_text(
                "Traceback (most recent call last):\n"
                "QualitySelfHealError: another quality error\n",
                encoding="utf-8",
            ),
            "terminal exists": lambda gates: (
                gates / "reader-testing-gate-ja.terminal.json"
            ).write_text("{}\n", encoding="utf-8"),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                run, run_id, prompt, ledger = self.fixture(Path(tmp))
                gates, _traceback, _quality_path = self.add_reader_traceback(run)
                mutate(gates)
                generation.adopt_prepublication(run, run_id, prompt, ledger)

                decision = repair.plan(run, ledger)

                self.assertEqual(decision["status"], "REFUSED")
                self.assertNotEqual(
                    decision.get("reason"),
                    "tracked-reader-terminal-receipt-source-defect",
                )

    def test_prepared_quality_repair_refuses_post_begin_evidence_drift(self):
        cases = {
            "receipt deletion": lambda run: (
                run / "gates/prepublication-adoption.json"
            ).unlink(),
            "receipt tamper": lambda run: (
                run / "gates/prepublication-adoption.json"
            ).write_text("[]\n", encoding="utf-8"),
            "generation status": self.hand_edit_generation_status,
            "original prompt drift": self.hand_edit_original_prompt,
        }
        for name, mutate in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                run, run_id, prompt, ledger = self.fixture(Path(tmp))
                self.add_reader_traceback(run)
                generation.adopt_prepublication(run, run_id, prompt, ledger)
                repair.begin(run, ledger)
                mutate(run)

                decision = repair.plan(run, ledger)

                self.assertEqual(
                    decision,
                    {"status": "REFUSED", "reason": "quality-repair-evidence-invalid"},
                )

    @staticmethod
    def hand_edit_generation_status(run: Path):
        state_path = run / "gates/generation-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["status"] = "provider-failed-ambiguous"
        state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")

    @staticmethod
    def hand_edit_original_prompt(run: Path):
        (run / "article-daily-prompt.txt").write_text(
            "changed original prompt\n", encoding="utf-8"
        )

    @staticmethod
    def add_reader_traceback(run: Path):
        gates = run / "gates"
        (gates / "topic-route.json").write_text(
            '{"topic_id":"writer-a4-reader-receipt","editorial_form":"explainer"}\n',
            encoding="utf-8",
        )
        traceback = (
            "Traceback (most recent call last):\n"
            "  File \"quality_self_heal.py\", line 132, in _snapshot_receipts\n"
            "    raise QualitySelfHealError(...)\n"
            "QualitySelfHealError: quality reader receipt is missing for ja\n"
        )
        quality_path = gates / "quality-self-heal.json"
        quality_path.write_text(traceback, encoding="utf-8")
        return gates, traceback, quality_path

    @staticmethod
    def replace_ja_with_symlink(run: Path, prompt: Path, ledger: Path):
        article = run / "article-ja.md"
        target = run.parent.parent / "outside-ja.md"
        target.write_text("outside\n", encoding="utf-8")
        article.unlink()
        article.symlink_to(target)


if __name__ == "__main__":
    unittest.main()
