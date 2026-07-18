#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_landing.py"
DAILY_SCRIPT = Path(__file__).resolve().parents[1] / "capafy-ig-marketing-daily.sh"
SPEC = importlib.util.spec_from_file_location("build_landing", SCRIPT)
build_landing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_landing)


class BuildLandingTests(unittest.TestCase):
    def setUp(self):
        self.agents = [
            {
                "agentId": "2",
                "agentStatus": "online",
                "name": "Writer & Planner",
                "desc": "Turns a rough brief into a useful plan.",
            },
            {
                "agentId": "offline-id",
                "agentStatus": "offline",
                "name": "Offline Skill",
                "desc": "Must never appear.",
            },
            {
                "agentId": "1",
                "agentStatus": "online",
                "name": "<script>alert(1)</script> Analyst",
                "desc": "Checks <b>facts</b> before conclusions.",
            },
            {
                "agentStatus": "online",
                "name": "Missing ID",
                "desc": "Must never appear.",
            },
        ]

    def test_filters_online_agents_and_sorts_by_name(self):
        online = build_landing.filter_online_agents(self.agents)

        self.assertEqual([agent["agentId"] for agent in online], ["1", "2"])

    def test_render_is_safe_complete_and_dependency_free(self):
        html = build_landing.render_html(
            build_landing.filter_online_agents(self.agents)
        )

        self.assertIn("Claude Skills Daily", html)
        self.assertIn("Sharing Claude skills you can use, every day.", html)
        self.assertEqual(html.count('class="skill-card"'), 2)
        self.assertIn("2 skills available", html)
        self.assertNotIn("Offline Skill", html)
        self.assertNotIn("Missing ID", html)
        self.assertNotIn("<script>", html.lower())
        self.assertNotIn("<b>facts</b>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt; Analyst", html)
        self.assertIn("Checks &lt;b&gt;facts&lt;/b&gt; before conclusions.", html)
        self.assertIn(
            "https://capafy.ai/agent/1?utm_source=instagram_bio&amp;utm_medium=bio_link&amp;utm_campaign=capafy_marketing",
            html,
        )
        self.assertIn('content="width=device-width, initial-scale=1"', html)
        self.assertIn("prefers-color-scheme: dark", html)
        self.assertIn("prefers-reduced-motion: reduce", html)
        self.assertIn(":focus-visible", html)
        self.assertNotIn("<script", html.lower())
        self.assertNotIn(" src=", html.lower())

    def test_render_is_byte_identical_for_same_input(self):
        online = build_landing.filter_online_agents(self.agents)

        self.assertEqual(
            build_landing.render_html(online),
            build_landing.render_html(online),
        )

    def test_build_overwrites_output_and_reports_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "index.html"
            output.write_text("stale", encoding="utf-8")
            with patch.object(build_landing, "_fetch_agents", return_value=self.agents):
                count = build_landing.build(output)

            self.assertEqual(count, 2)
            self.assertIn("Claude Skills Daily", output.read_text(encoding="utf-8"))
            self.assertNotIn("stale", output.read_text(encoding="utf-8"))

    def test_build_fails_when_no_online_agents_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "index.html"
            with patch.object(
                build_landing,
                "_fetch_agents",
                return_value=[{"agentId": "1", "agentStatus": "offline"}],
            ):
                with self.assertRaisesRegex(RuntimeError, "no online listings"):
                    build_landing.build(output)
            self.assertFalse(output.exists())

    def test_daily_loop_refreshes_landing_before_cadence_and_uses_it_for_bio(self):
        script = DAILY_SCRIPT.read_text(encoding="utf-8")

        self.assertIn(
            'LANDING_URL="https://capafy-skills-daily.netlify.app"', script
        )
        self.assertIn(
            'LANDING_SITE_ID="41c8e52e-b163-442a-84ff-fd866269bf6c"', script
        )
        self.assertIn('build_landing.py" >>"$LOG"', script)
        self.assertIn('netlify deploy --prod --dir', script)
        self.assertIn('--site "$LANDING_SITE_ID"', script)
        self.assertLess(script.index("build_landing.py"), script.index("# ── CADENCE GATE"))
        self.assertIn(
            'STEP5 BIO: set the profile Website to the all-skills landing URL '\
            '\'"$LANDING_URL"\' ONLY when commercial_ok=yes AND MODE=--live.',
            script,
        )
        self.assertIn(
            "Never use an individual Capafy listing URL for the profile Website.",
            script,
        )


if __name__ == "__main__":
    unittest.main()
