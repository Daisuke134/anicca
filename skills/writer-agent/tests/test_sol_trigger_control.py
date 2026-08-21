#!/usr/bin/env python3
"""Contracts for deterministic Sol quality-sample receipt production."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "scripts" / "sol_trigger_control.py"
RUNNER = ROOT / "runtime" / "model-runner.sh"


class SolTriggerControlTests(unittest.TestCase):
    def register(
        self,
        sandbox: Path,
        ordinal: int,
        language: str,
        *,
        run_id: str | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        actual_run_id = run_id or f"run-{ordinal:02d}"
        article = sandbox / f"{actual_run_id}-{language}.md"
        article.write_text(f"article {actual_run_id} {language}\n", encoding="utf-8")
        receipt = sandbox / "receipts" / f"{actual_run_id}.json"
        result = subprocess.run(
            [
                "python3",
                str(CONTROL),
                "quality-sample",
                "--state",
                str(sandbox / "sample-state.json"),
                "--run-id",
                actual_run_id,
                "--artifact-id",
                f"article-{language}",
                "--article",
                str(article),
                "--language",
                language,
                "--receipt",
                str(receipt),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        payload = json.loads(result.stdout) if result.stdout else {}
        return result, payload

    def test_first_30_distinct_runs_emit_only_six_alternating_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            sandbox = Path(temporary)
            emitted: list[tuple[int, str]] = []
            for ordinal in range(1, 31):
                expected_language = "ja" if (ordinal // 5) % 2 == 1 else "en"
                language = expected_language if ordinal % 5 == 0 else "ja"
                result, payload = self.register(sandbox, ordinal, language)
                self.assertEqual(result.returncode, 0, result.stderr)
                if payload["status"] == "RECEIPT_READY":
                    emitted.append((ordinal, language))
                    receipt = json.loads(Path(payload["receipt_path"]).read_text())
                    self.assertEqual(receipt["schema_version"], 1)
                    self.assertEqual(receipt["trigger"], "quality_sample")
                    self.assertEqual(receipt["run_id"], f"run-{ordinal:02d}")
                    self.assertEqual(receipt["requested_reasoning_effort"], "medium")
                    self.assertRegex(receipt["article_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(
                emitted,
                [(5, "ja"), (10, "en"), (15, "ja"), (20, "en"), (25, "ja"), (30, "en")],
            )
            after, payload = self.register(sandbox, 31, "ja")
            self.assertEqual(after.returncode, 0, after.stderr)
            self.assertEqual(payload["status"], "NOT_SAMPLED")

    def test_retry_is_idempotent_and_wrong_language_keeps_same_slot_pending(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            sandbox = Path(temporary)
            for ordinal in range(1, 5):
                self.assertEqual(self.register(sandbox, ordinal, "ja")[0].returncode, 0)
            wrong, wrong_payload = self.register(sandbox, 5, "en")
            self.assertEqual(wrong.returncode, 0, wrong.stderr)
            self.assertEqual(wrong_payload["status"], "LANGUAGE_PENDING")
            self.assertFalse(Path(wrong_payload["receipt_path"]).exists())

            corrected, first = self.register(sandbox, 5, "ja", run_id="run-05")
            replay, second = self.register(sandbox, 99, "ja", run_id="run-05")
            self.assertEqual(corrected.returncode, 0, corrected.stderr)
            self.assertEqual(replay.returncode, 0, replay.stderr)
            self.assertEqual(first["status"], "RECEIPT_READY")
            self.assertEqual(second["status"], "RECEIPT_READY")
            self.assertEqual(first["ordinal"], 5)
            self.assertEqual(second["ordinal"], 5)
            state = json.loads((sandbox / "sample-state.json").read_text())
            self.assertEqual(len(state["runs"]), 5)

    def test_generated_receipt_crosses_sol_boundary_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            sandbox = Path(temporary)
            for ordinal in range(1, 5):
                self.assertEqual(self.register(sandbox, ordinal, "ja")[0].returncode, 0)
            generated, payload = self.register(sandbox, 5, "ja")
            self.assertEqual(generated.returncode, 0, generated.stderr)

            calls = sandbox / "calls.txt"
            args = sandbox / "args.txt"
            fake_codex = sandbox / "codex"
            fake_codex.write_text(
                "#!/usr/bin/env bash\nprintf '%s\\n' \"$@\" >\"$CAPTURE_ARGS\"\n"
                "printf 'CALL\\n' >>\"$CAPTURE_CALLS\"\ncat >/dev/null\nprintf 'SOLAUDIT\\n'\n",
                encoding="utf-8",
            )
            fake_codex.chmod(0o755)
            prompt = sandbox / "prompt.txt"
            prompt.write_text("Return SOLAUDIT", encoding="utf-8")
            environment = os.environ.copy()
            environment.update(
                {
                    "ARTICLE_PROVIDER": "codex",
                    "ARTICLE_CODEX_BIN": str(fake_codex),
                    "ARTICLE_MODEL_ROOT": str(sandbox / "model-root"),
                    "ARTICLE_MODEL_STATE_ROOT": str(sandbox / "model-state"),
                    "ARTICLE_PROVIDER_HEALTH": str(sandbox / "health.json"),
                    "ARTICLE_MODEL_LOG": str(sandbox / "model.log"),
                    "ARTICLE_RUN_ID": "run-05",
                    "ARTICLE_MODEL_ROLE": "sol-audit",
                    "ARTICLE_SOL_TRIGGER_RECEIPT": str(payload["receipt_path"]),
                    "CAPTURE_ARGS": str(args),
                    "CAPTURE_CALLS": str(calls),
                }
            )
            first = subprocess.run(
                [str(RUNNER), "judge", "--prompt-file", str(prompt)],
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            replay = subprocess.run(
                [str(RUNNER), "judge", "--prompt-file", str(prompt)],
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(replay.returncode, 78, replay.stderr)
            captured = args.read_text().splitlines()
            self.assertEqual(captured[captured.index("--model") + 1], "gpt-5.6-sol")
            self.assertEqual(calls.read_text(), "CALL\n")

    def test_concurrent_retry_registers_one_run_and_one_ordinal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            sandbox = Path(temporary)
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(
                    pool.map(
                        lambda _: self.register(sandbox, 1, "ja", run_id="same-run"),
                        range(16),
                    )
                )
            self.assertTrue(all(result.returncode == 0 for result, _ in results))
            self.assertTrue(all(payload["ordinal"] == 1 for _, payload in results))
            state = json.loads((sandbox / "sample-state.json").read_text())
            self.assertEqual(state["runs"], [{"ordinal": 1, "run_id": "same-run"}])


if __name__ == "__main__":
    unittest.main()
