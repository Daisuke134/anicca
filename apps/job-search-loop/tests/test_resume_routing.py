import importlib
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ResumeRoutingTests(unittest.TestCase):
    def _resume_tree(self, root: Path) -> None:
        files = [
            root / "japan" / "Daisuke_Narita_Japan_AI_Resume.pdf",
            root / "master" / "Daisuke_Narita_AI_Resume.pdf",
            root / "business" / "Daisuke_Narita_AI_Business_Resume.pdf",
        ]
        for index, path in enumerate(files):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"%PDF-1.4 resume-{index}".encode())

    def test_japanese_posting_selects_japanese_resume_regardless_of_role_family(self):
        self.assertIsNotNone(
            importlib.util.find_spec("job_search_loop.resume_routing")
        )
        routing = importlib.import_module("job_search_loop.resume_routing")
        select_resume = getattr(routing, "select_resume", None)
        self.assertIsNotNone(select_resume)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._resume_tree(root)

            result = select_resume(
                posting_text=(
                    "生成AIエンジニアを募集します。金融機関向けAIエージェントの"
                    "設計・開発・評価を担当し、プロダクトチームと連携します。"
                ),
                role_family="customer_success",
                materials_root=root,
            )

            self.assertEqual(result["posting_language"], "ja")
            self.assertEqual(result["resume_variant"], "japanese")
            self.assertEqual(
                Path(result["resume_path"]).name,
                "Daisuke_Narita_Japan_AI_Resume.pdf",
            )

    def test_english_posting_keeps_english_role_variant(self):
        self.assertIsNotNone(
            importlib.util.find_spec("job_search_loop.resume_routing")
        )
        routing = importlib.import_module("job_search_loop.resume_routing")
        select_resume = getattr(routing, "select_resume", None)
        self.assertIsNotNone(select_resume)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._resume_tree(root)

            engineering = select_resume(
                posting_text="Build and evaluate production AI agents for banking workflows.",
                role_family="engineering",
                materials_root=root,
            )
            business = select_resume(
                posting_text="Help enterprise customers adopt reliable AI products.",
                role_family="customer_success",
                materials_root=root,
            )

            self.assertEqual(engineering["posting_language"], "en")
            self.assertEqual(engineering["resume_variant"], "engineering")
            self.assertEqual(
                Path(engineering["resume_path"]).name,
                "Daisuke_Narita_AI_Resume.pdf",
            )
            self.assertEqual(business["posting_language"], "en")
            self.assertEqual(business["resume_variant"], "technical_business")
            self.assertEqual(
                Path(business["resume_path"]).name,
                "Daisuke_Narita_AI_Business_Resume.pdf",
            )

    def test_existing_assignment_variant_is_reused_without_role_rerouting(self):
        routing = importlib.import_module("job_search_loop.resume_routing")
        select_resume_variant = getattr(routing, "select_resume_variant", None)
        self.assertIsNotNone(select_resume_variant)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._resume_tree(root)

            result = select_resume_variant(
                resume_variant="japanese",
                materials_root=root,
            )

            self.assertEqual(result["resume_variant"], "japanese")
            self.assertEqual(result["posting_language"], "ja")
            self.assertEqual(
                Path(result["resume_path"]).name,
                "Daisuke_Narita_Japan_AI_Resume.pdf",
            )
            expected = hashlib.sha256(
                (root / "japan" / "Daisuke_Narita_Japan_AI_Resume.pdf").read_bytes()
            ).hexdigest()
            self.assertEqual(result["resume_sha256"], expected)
            self.assertEqual(
                select_resume_variant(
                    resume_variant="japanese",
                    materials_root=root,
                    expected_sha256=expected,
                )["resume_sha256"],
                expected,
            )
            with self.assertRaises(ValueError):
                select_resume_variant(
                    resume_variant="japanese",
                    materials_root=root,
                    expected_sha256="0" * 64,
                )

            main = getattr(routing, "main")
            with patch.object(
                sys,
                "argv",
                [
                    "resume_routing",
                    "--resume-variant",
                    "japanese",
                    "--materials-root",
                    str(root),
                ],
            ), self.assertRaises(SystemExit) as missing_hash:
                main()
            self.assertEqual(missing_hash.exception.code, 2)

            with patch.object(
                sys,
                "argv",
                [
                    "resume_routing",
                    "--role-family",
                    "engineering",
                    "--expected-sha256",
                    expected,
                    "--materials-root",
                    str(root),
                ],
            ), self.assertRaises(SystemExit) as unexpected_hash:
                main()
            self.assertEqual(unexpected_hash.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
