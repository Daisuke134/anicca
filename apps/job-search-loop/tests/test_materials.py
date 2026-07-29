import tempfile
import unittest
import importlib
import shutil
from pathlib import Path

from job_search_loop.materials import (
    MaterialError,
    business_sections,
    render_business,
    render_resume_html,
    secure_material_paths,
    validate_claims,
)


class MaterialTests(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "candidate": {"name": "Daisuke Narita"},
            "facts": [
                {"id": "mufg", "claim": "Contributed to MUFG deployment", "evidence": "public"},
                {"id": "iclr", "claim": "Presented an ICLR 2026 report", "evidence": "video"},
            ],
        }

    def test_unknown_fact_id_is_rejected(self):
        with self.assertRaises(MaterialError):
            validate_claims(self.profile, [{"text": "Invented", "fact_ids": ["missing"]}])

    def test_mufg_sole_ownership_wording_is_rejected(self):
        with self.assertRaisesRegex(MaterialError, "ownership"):
            validate_claims(
                self.profile,
                [{"text": "Led the entire MUFG deployment", "fact_ids": ["mufg"]}],
            )

    def test_resume_is_single_column_and_keeps_public_link(self):
        html = render_resume_html(
            self.profile,
            [
                {
                    "heading": "Experience",
                    "items": [
                        {
                            "text": "Contributed to MUFG deployment",
                            "fact_ids": ["mufg"],
                        }
                    ],
                }
            ],
            links=[("ICLR 2026 report", "https://www.youtube.com/watch?v=biHAQ6aSQuc")],
        )
        self.assertIn("grid-template-columns: 1fr", html)
        self.assertIn("https://www.youtube.com/watch?v=biHAQ6aSQuc", html)
        self.assertIn("Daisuke Narita", html)

    def test_japan_targeted_resume_includes_verified_contact_and_birth_date(self):
        profile = {
            **self.profile,
            "candidate": {
                "name": "Daisuke Narita",
                "application_email": "candidate@example.com",
                "phone": "09000000000",
                "base": "Tokyo, Japan",
                "date_of_birth": "2002-01-30",
            },
        }
        html = render_resume_html(
            profile,
            [],
            links=[],
            include_date_of_birth=True,
        )
        self.assertIn("candidate@example.com", html)
        self.assertIn("09000000000", html)
        self.assertIn("Tokyo, Japan", html)
        self.assertIn("Date of birth: 2002-01-30", html)

    def test_generated_materials_are_private(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "resume.html"
            second = Path(directory) / "resume.pdf"
            first.write_text("html", encoding="utf-8")
            second.write_text("pdf", encoding="utf-8")
            secure_material_paths(first, second)
            self.assertEqual(first.stat().st_mode & 0o777, 0o600)
            self.assertEqual(second.stat().st_mode & 0o777, 0o600)

    def test_business_resume_prioritizes_enterprise_product_and_customer_impact(self):
        profile = {
            "candidate": {"name": "Daisuke Narita"},
            "facts": [
                {"id": "muit_agent_crm", "claim": "Deployed agents into a bank CRM."},
                {"id": "muit_rm_summary", "claim": "Built RM-facing summaries."},
                {"id": "mufg", "claim": "Contributed to MUFG production deployment."},
                {"id": "anicca_consumer", "claim": "Built and grew Anicca."},
                {"id": "life_manager", "claim": "Builds Life Manager."},
                {"id": "a10_marketing", "claim": "Managed growth campaigns."},
                {"id": "agent_club", "claim": "Founded a weekly AI agent community."},
                {"id": "iclr", "claim": "Shared ICLR research learnings."},
            ],
        }
        sections = business_sections(profile)
        self.assertEqual(
            sections[0]["heading"],
            "Regulated Enterprise AI Delivery — MUIT / MUFG (2025–Present)",
        )
        first_ids = [item["fact_ids"][0] for item in sections[0]["items"]]
        self.assertEqual(first_ids, ["muit_agent_crm", "muit_rm_summary", "mufg"])
        product_ids = {
            item["fact_ids"][0] for item in sections[1]["items"]
        }
        self.assertEqual(
            product_ids,
            {"anicca_consumer", "life_manager", "a10_marketing"},
        )

    def test_resume_supports_business_specific_headline_without_invented_ownership(self):
        html = render_resume_html(
            self.profile,
            [
                {
                    "heading": "Enterprise",
                    "items": [
                        {
                            "text": "Contributed to MUFG deployment",
                            "fact_ids": ["mufg"],
                        }
                    ],
                }
            ],
            links=[],
            headline="AI Product, Solutions & Customer Strategy",
            summary="Regulated enterprise delivery and customer adoption",
        )
        self.assertIn("AI Product, Solutions &amp; Customer Strategy", html)
        self.assertIn("customer adoption", html)
        self.assertNotIn("sales quota", html.casefold())
        self.assertNotIn("people management", html.casefold())

    @unittest.skipUnless(shutil.which("weasyprint"), "weasyprint is required")
    def test_business_resume_renders_one_private_ats_page(self):
        facts = [
            ("muit_agent_crm", "MUIT deployed AI agents into a bank CRM."),
            ("muit_genie_logs", "Analyzed agent logs with Databricks Genie Code."),
            ("muit_rm_summary", "Built relationship-manager company summaries."),
            ("mufg", "Contributed to MUFG production Agentforce deployment."),
            ("anicca_consumer", "Built and grew Anicca consumer AI products."),
            ("life_manager", "Builds the Life Manager consumer AI agent."),
            ("a10_marketing", "Managed growth campaigns and improved acquisition."),
            ("agent_club", "Founded a weekly AI agent practice community."),
            ("iclr", "Presented ICLR 2026 research learnings."),
            ("naist", "NAIST research used EEG and machine learning."),
            ("atr_research", "Conducted and presented research at ATR."),
            ("education", "M.S. studies at NAIST and B.A. from Keio."),
            ("languages", "Japanese native; professional English."),
        ]
        profile = {
            "candidate": {"name": "Daisuke Narita", "base": "Tokyo, Japan"},
            "facts": [
                {"id": fact_id, "claim": claim, "evidence": "fixture"}
                for fact_id, claim in facts
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile_path = root / "profile.json"
            profile_path.write_text(
                __import__("json").dumps(profile), encoding="utf-8"
            )
            html_path, pdf_path = render_business(profile_path, root / "output")
            self.assertEqual(html_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(pdf_path.stat().st_mode & 0o777, 0o600)
            info = __import__("subprocess").run(
                ["pdfinfo", str(pdf_path)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            extracted = __import__("subprocess").run(
                ["pdftotext", str(pdf_path), "-"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertIn("Pages:           1", info)
            self.assertIn("AI Product, Solutions & Customer Strategy", extracted)
            self.assertIn("MUIT", extracted)
            self.assertIn("Anicca", extracted)

    def test_japanese_sections_ground_at_least_ten_translated_points(self):
        materials = importlib.import_module("job_search_loop.materials")
        japanese_sections = getattr(materials, "japanese_sections", None)
        self.assertIsNotNone(japanese_sections)
        fact_ids = [
            "muit_role_2025",
            "muit_agent_crm",
            "muit_genie_logs",
            "muit_rm_summary",
            "mufg",
            "anicca_consumer",
            "life_manager",
            "naist",
            "atr_research",
            "agent_club",
            "iclr",
            "a10_marketing",
            "education",
            "languages",
        ]
        profile = {
            "candidate": {"name": "Daisuke Narita", "name_ja": "成田大輔"},
            "facts": [
                {"id": fact_id, "claim": f"Approved claim for {fact_id}"}
                for fact_id in fact_ids
            ],
        }

        sections = japanese_sections(profile)
        items = [item for section in sections for item in section["items"]]

        self.assertEqual(len(items), 14)
        self.assertEqual(
            [item["fact_ids"][0] for item in items[:5]],
            [
                "muit_role_2025",
                "muit_agent_crm",
                "muit_genie_logs",
                "muit_rm_summary",
                "mufg",
            ],
        )
        self.assertTrue(all(any("\u3040" <= c <= "\u9fff" for c in item["text"]) for item in items))
        self.assertIn("日本初", items[4]["text"])
        self.assertNotIn("主導", items[4]["text"])

    @unittest.skipUnless(shutil.which("weasyprint"), "weasyprint is required")
    def test_japanese_resume_renders_one_private_ats_page(self):
        materials = importlib.import_module("job_search_loop.materials")
        render_japanese = getattr(materials, "render_japanese", None)
        self.assertIsNotNone(render_japanese)
        fact_ids = [
            "muit_role_2025",
            "muit_agent_crm",
            "muit_genie_logs",
            "muit_rm_summary",
            "mufg",
            "anicca_consumer",
            "life_manager",
            "naist",
            "atr_research",
            "agent_club",
            "iclr",
            "a10_marketing",
            "education",
            "languages",
        ]
        profile = {
            "candidate": {
                "name": "Daisuke Narita",
                "name_ja": "成田大輔",
                "application_email": "candidate@example.com",
                "phone": "09000000000",
                "base": "Tokyo, Japan",
                "date_of_birth": "2002-01-30",
            },
            "facts": [
                {"id": fact_id, "claim": f"Approved claim for {fact_id}"}
                for fact_id in fact_ids
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile_path = root / "profile.json"
            profile_path.write_text(
                __import__("json").dumps(profile, ensure_ascii=False),
                encoding="utf-8",
            )

            html_path, pdf_path = render_japanese(profile_path, root / "output")

            info = __import__("subprocess").run(
                ["pdfinfo", str(pdf_path)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            extracted = __import__("subprocess").run(
                ["pdftotext", str(pdf_path), "-"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertIn("Pages:           1", info)
            self.assertIn("成田大輔", extracted)
            self.assertIn("職務経歴書", extracted)
            self.assertIn("AIエージェント", extracted)
            self.assertIn("生年月日：2002-01-30", extracted)
            self.assertEqual(html_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(pdf_path.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
