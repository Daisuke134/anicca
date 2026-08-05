import unittest

from job_search_loop.event_reporting import render_event_message, validate_event_message


class EventReportingTests(unittest.TestCase):
    def facts(self, kind):
        return {
            "version": 1,
            "event_id": "event-1",
            "kind": kind,
            "company": "Example AI",
            "title": "AI Deployment Engineer",
            "stage": "一次面接",
            "occurred_at": "2026-08-05 14:00 JST",
            "next_action": "確認メールと企業ページを照合します。",
            "links": {"求人ページ": "https://jobs.example/one"},
        }

    def test_each_event_kind_has_its_required_tone_without_fact_changes(self):
        tones = {
            "application": "💼",
            "recruiter_interest": "✨",
            "interview": "🎉",
            "offer": "🚀🎊",
            "rejection": "今回は",
            "operational_delay": "⚠️",
        }
        for kind, marker in tones.items():
            with self.subTest(kind=kind):
                facts = self.facts(kind)
                message = render_event_message(facts)
                self.assertIn(marker, message)
                receipt = validate_event_message(facts, message)
                self.assertEqual(receipt["status"], "valid")
                self.assertEqual(len(receipt["facts_sha256"]), 64)

    def test_changed_fact_link_or_tone_is_rejected(self):
        facts = self.facts("interview")
        original = render_event_message(facts)
        mutations = (
            original.replace("Example AI", "Other AI"),
            original.replace("一次面接", "オファー"),
            original.replace("https://jobs.example/one", "https://evil.example/one"),
            original.replace("🎉", "🚀🎊"),
            original + "\n採用は確実です。",
        )
        for message in mutations:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, "drift"):
                validate_event_message(facts, message)

    def test_private_paths_and_technical_copy_are_not_rendered(self):
        for kind in (
            "application", "recruiter_interest", "interview", "offer",
            "rejection", "operational_delay",
        ):
            message = render_event_message(self.facts(kind))
            lowered = message.casefold()
            for forbidden in ("/users/", "~/.local", "runner", "exit code", "sha256", "bounded"):
                self.assertNotIn(forbidden, lowered)


if __name__ == "__main__":
    unittest.main()
