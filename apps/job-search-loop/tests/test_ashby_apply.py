import unittest


class AshbyApplyTests(unittest.TestCase):
    def test_yes_no_buttons_win_over_internal_checkbox(self):
        from job_search_loop.ashby_apply import classify_control

        self.assertEqual(
            classify_control(
                has_file=False,
                has_checkbox=True,
                has_select=False,
                options=["Yes", "No"],
                has_editable=False,
            ),
            "select",
        )

    def test_plan_uses_current_live_field_paths_not_prior_posting_ids(self):
        from job_search_loop.ashby_apply import build_actions

        fields = [
            {
                "field_path": "new-phone-id",
                "question": "Phone number",
                "required": True,
                "control": "fill",
            },
            {
                "field_path": "new-authorization-id",
                "question": "Are you authorized to work in Japan?",
                "required": True,
                "control": "select",
                "options": ["Yes", "No"],
            },
            {
                "field_path": "new-attestation-id",
                "question": "I confirm I have read the above.",
                "required": True,
                "control": "check",
            },
            {
                "field_path": "_systemfield_resume",
                "question": "Resume/CV",
                "required": True,
                "control": "upload",
            },
        ]
        answer_map = {
            "Phone number": {
                "answer": "+81-00-0000-0000",
                "fact_ids": ["profile.phone"],
                "prior_field_path": "old-phone-id",
            },
            "Are you authorized to work in Japan?": {
                "answer": "Yes",
                "fact_ids": ["legal.japan_work_authorization"],
            },
            "I confirm I have read the above.": {
                "answer": "Confirmed",
                "fact_ids": ["candidate.attestation"],
            },
        }

        result = build_actions(
            fields,
            answer_map=answer_map,
            resume_path="/private/resume.pdf",
            resume_sha256="a" * 64,
        )

        self.assertEqual(result["status"], "ready")
        self.assertEqual(
            [action["field_path"] for action in result["actions"]],
            [
                "new-phone-id",
                "new-authorization-id",
                "new-attestation-id",
                "_systemfield_resume",
            ],
        )
        self.assertEqual(
            [action["kind"] for action in result["actions"]],
            ["fill", "select", "check", "upload"],
        )
        self.assertNotIn("old-phone-id", repr(result))


if __name__ == "__main__":
    unittest.main()
