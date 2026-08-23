import unittest

from job_search_loop.state import (
    InvalidTransition,
    canonical_job_id,
    canonical_url,
    provider_recovery_url,
    same_application_surface,
    validate_transition,
)


class StateTests(unittest.TestCase):
    def test_ashby_application_path_is_same_posting_identity(self):
        self.assertEqual(
            canonical_url("https://jobs.ashbyhq.com/acme/role/application"),
            "https://jobs.ashbyhq.com/acme/role",
        )
        self.assertEqual(
            canonical_url("https://jobs.ashbyhq.com/acme/role"),
            "https://jobs.ashbyhq.com/acme/role",
        )

    def test_non_ashby_application_path_is_unchanged(self):
        self.assertEqual(
            canonical_url("https://careers.example.com/acme/role/application"),
            "https://careers.example.com/acme/role/application",
        )

    def test_workday_apply_route_is_the_exact_posting_surface(self):
        posting = "https://rakuten.wd1.myworkdayjobs.com/en-us/rakuteninc/job/tokyo-japan/role_1036041-147"
        form = "https://rakuten.wd1.myworkdayjobs.com/en-US/rakuteninc/job/Tokyo%2C-Japan/role_1036041-147/apply/review"
        self.assertTrue(same_application_surface(form, posting))
        self.assertFalse(
            same_application_surface(
                form,
                "https://rakuten.wd1.myworkdayjobs.com/en-us/rakuteninc/job/tokyo-japan/other_999",
            )
        )

    def test_workday_recovery_review_without_location_is_same_posting(self):
        posting = (
            "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/"
            "job/Japan-Tokyo/Senior-Partner-Manager_JR2008507"
        )
        review = (
            "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/"
            "job/Senior-Partner-Manager_JR2008507/apply"
        )

        self.assertTrue(same_application_surface(review, posting))
        self.assertFalse(
            same_application_surface(
                review,
                posting.replace("JR2008507", "JR2009999"),
            )
        )
        self.assertTrue(
            same_application_surface(
                "https://workday.wd5.myworkdayjobs.com/ja-JP/Workday/job/Japan%2C-Tokyo/Account-Executive_JR-0103573-1/apply/autofillWithResume",
                "https://workday.wd5.myworkdayjobs.com/Workday/job/Japan-Tokyo/Account-Executive_JR-0103573-1",
            )
        )

    def test_workday_recovery_uses_the_provider_search_href_shape(self):
        posting = "https://rakuten.wd1.myworkdayjobs.com/en-US/RakutenInc/job/Tokyo-Japan/role_1036041-147"
        self.assertEqual(
            provider_recovery_url(posting),
            f"{posting}?q=1036041-147",
        )
        generic = "https://careers.example.com/job/role_1036041-147"
        self.assertEqual(provider_recovery_url(generic), generic)

    def test_canonical_identity_ignores_tracking_and_case(self):
        first = canonical_job_id(
            " Example, Inc. ",
            " AI Engineer ",
            "https://jobs.example.com/roles/42/?utm_source=x#apply",
        )
        second = canonical_job_id(
            "example inc",
            "ai engineer",
            "https://jobs.example.com/roles/42",
        )
        self.assertEqual(first, second)

    def test_allowed_transition(self):
        validate_transition("discovered", "qualified")

    def test_forbidden_transition(self):
        with self.assertRaises(InvalidTransition):
            validate_transition("discovered", "submitted")


if __name__ == "__main__":
    unittest.main()
