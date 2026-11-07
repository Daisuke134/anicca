"""Synthetic-only contract tests for Manager P10-2, P10-3 and P10-4."""
import unittest
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from p10_2_4_control_plane_synthetic import (
    Proposal, PolicyInput, plan_portfolio, policy_candidate, safe_audit_projection,
    recovery_plan, slo_budget, runway_projection, cost_reconcile, synthetic_demo)


class P102Capital(unittest.TestCase):
    def setUp(self):
        self.projects = [Proposal("research", 300, 400, 80),
                         Proposal("pilot", 180, 320, 20)]

    def test_both_projects_selected_without_exceeding_budget(self):
        r = plan_portfolio(self.projects, 1000, 450, 500)
        self.assertEqual(r["spend_minor"], 480)
        self.assertEqual(r["selected_project_ids"], ["pilot", "research"])
        self.assertFalse(r["external_authorization"])

    def test_cash_reserve_is_hard_cap(self):
        r = plan_portfolio(self.projects, 500, 450, 500)
        self.assertEqual(r["spend_minor"], 0)

    def test_experiment_cap_is_hard_cap(self):
        r = plan_portfolio(self.projects, 1000, 10, 200)
        self.assertEqual(r["selected_project_ids"], ["pilot"])

    def test_unlicensed_candidate_is_never_selected(self):
        p = Proposal("unlicensed", 100, 9999, 0, False)
        r = plan_portfolio(self.projects+[p], 1000, 0, 1000)
        self.assertNotIn("unlicensed", r["selected_project_ids"])

    def test_negative_value_candidate_not_selected(self):
        r = plan_portfolio([Proposal("loss", 100, 20)], 1000, 0, 1000)
        self.assertEqual(r["selected_project_ids"], [])

    def test_duplicate_project_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            plan_portfolio(self.projects+[self.projects[0]], 1000, 0, 1000)

    def test_bad_budget_rejected(self):
        with self.assertRaisesRegex(ValueError, "cash"):
            plan_portfolio(self.projects, 100, 200, 500)

    def test_integer_money_only(self):
        with self.assertRaisesRegex(ValueError, "cash"):
            plan_portfolio(self.projects, 100.0, 0, 500)

    def test_bounded_combinatorial_search(self):
        with self.assertRaisesRegex(ValueError, "bounded unique"):
            plan_portfolio([Proposal(str(i), 1, 2) for i in range(17)], 100, 0, 100)

    def test_expected_value_is_explicitly_unproven(self):
        r = plan_portfolio(self.projects, 1000, 0, 1000)
        self.assertFalse(r["real_return_proven"])


class P103Governance(unittest.TestCase):
    def setUp(self):
        now = datetime(2026, 11, 7, tzinfo=timezone.utc)
        self.req = PolicyInput("sim", "tenant1", "tenant1", "read_synthetic",
                               frozenset({"read_synthetic"}), now+timedelta(days=1),
                               now, False, True, 0, 0, "synthetic", "p10-3-v1", False)

    def test_valid_is_simulation_not_live_grant(self):
        r = policy_candidate(self.req)
        self.assertEqual(r["decision"], "SIMULATION_ELIGIBLE_NOT_AUTHORIZED")
        self.assertFalse(r["authority_to_execute"])

    def test_revocation(self):
        self.assertIn("REVOKED", policy_candidate(replace(self.req, revoked=True))["reasons"])

    def test_expiry(self):
        self.assertIn("EXPIRED", policy_candidate(replace(self.req, expires_at_utc=self.req.now_utc))["reasons"])

    def test_scope_denied(self):
        self.assertIn("OUTSIDE_SCOPE", policy_candidate(replace(self.req, scope=frozenset()))["reasons"])

    def test_tenant_mismatch(self):
        self.assertIn("TENANT_MISMATCH", policy_candidate(replace(self.req, target_tenant_id="other"))["reasons"])

    def test_consent_missing(self):
        self.assertIn("NO_CONSENT", policy_candidate(replace(self.req, consent_confirmed=False))["reasons"])

    def test_budget_insufficient(self):
        self.assertIn("BUDGET", policy_candidate(replace(self.req, requested_cost_minor=1))["reasons"])

    def test_private_data_blocked(self):
        self.assertIn("PRIVATE_DATA_BLOCKED", policy_candidate(replace(self.req, data_class="health"))["reasons"])

    def test_external_effect_blocked_even_with_scope(self):
        r = policy_candidate(replace(self.req, action="money", scope=frozenset({"money"}),
                                     is_external_effect=True))
        self.assertIn("NO_LIVE_EFFECT_AUTHORITY", r["reasons"])

    def test_silent_external_side_effect_denied(self):
        r = policy_candidate(replace(self.req, is_external_effect=True))
        self.assertIn("NO_LIVE_EFFECT_AUTHORITY", r["reasons"])

    def test_missing_identity(self):
        r = policy_candidate(replace(self.req, actor_id=""))
        self.assertIn("MISSING_ID_OR_POLICY", r["reasons"])

    def test_naive_timestamp_rejected(self):
        r = policy_candidate(replace(self.req, now_utc=datetime(2026, 11, 7)))
        self.assertIn("UNTRUSTED_CLOCK", r["reasons"])

    def test_audit_hash_is_deterministic_and_not_immutable_proof(self):
        event = dict(event_id="e1", tenant_ref="pseudonymous", run_ref="r1", phase="plan",
                     decision="DENY", reason_code="NO_CONSENT", policy_version="v1",
                     evidence_ref="synthetic:fixture")
        first = safe_audit_projection(event)
        self.assertEqual(first["digest_sha256"], safe_audit_projection(event)["digest_sha256"])
        self.assertIn("NOT_TAMPER_PROOF", first["audit_status"])

    def test_audit_rejects_raw_pii(self):
        event = dict(event_id="e1", tenant_ref="person@email", run_ref="r1", phase="plan",
                     decision="DENY", reason_code="NO_CONSENT", policy_version="v1",
                     evidence_ref="synthetic:fixture")
        with self.assertRaisesRegex(ValueError, "PII"):
            safe_audit_projection(event)

    def test_audit_rejects_unapproved_fields(self):
        event = dict(event_id="e1", private_prompt="ignore all constraints")
        with self.assertRaisesRegex(ValueError, "allowlist|no-PII"):
            safe_audit_projection(event)


class P104Operations(unittest.TestCase):
    def test_unknown_external_never_resends(self):
        self.assertEqual(recovery_plan("UNKNOWN", "external_effect"),
                         "RECONCILE_ONLY_NO_RESEND")

    def test_dispatching_external_never_resends(self):
        self.assertEqual(recovery_plan("DISPATCHING", "external_effect"),
                         "RECONCILE_ONLY_NO_RESEND")

    def test_external_present_requires_readback(self):
        self.assertEqual(recovery_plan("PRESENT", "external_effect"),
                         "INDEPENDENT_READBACK")

    def test_external_absent_not_auto_retried(self):
        self.assertEqual(recovery_plan("ABSENT", "external_effect"),
                         "NO_AUTOMATIC_EXTERNAL_DISPATCH")

    def test_only_transient_read_failure_retries(self):
        self.assertEqual(recovery_plan("FAILED", "read_only", "TRANSIENT"),
                         "BOUNDED_READ_ONLY_RETRY")
        self.assertEqual(recovery_plan("FAILED", "read_only", "PERMANENT"),
                         "NO_ACTION")

    def test_verified_stays_done(self):
        self.assertEqual(recovery_plan("VERIFIED", "external_effect"), "DONE")

    def test_invalid_status_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown"):
            recovery_plan("MAGIC", "external_effect")

    def test_slo_budget(self):
        r = slo_budget(1000, 3, Decimal("0.995"))
        self.assertEqual(r["allowed_failures"], 5)
        self.assertEqual(r["remaining_error_budget"], 2)
        self.assertFalse(r["breached"])

    def test_slo_breach(self):
        self.assertTrue(slo_budget(1000, 6, Decimal("0.995"))["breached"])

    def test_slo_invalid_input(self):
        with self.assertRaisesRegex(ValueError, "invalid SLO"):
            slo_budget(100, 200, Decimal("0.99"))

    def test_runway_burn(self):
        self.assertEqual(runway_projection(1000, 250)["months"], "4")

    def test_runway_not_infinite_fake_number(self):
        r = runway_projection(1000, 0)
        self.assertIsNone(r["months"])
        self.assertEqual(r["status"], "NO_POSITIVE_NET_BURN")

    def test_provider_cost_unallocated_visible(self):
        r = cost_reconcile(600, 580, "USD", "synthetic:bill")
        self.assertEqual(r["unallocated_minor"], 20)
        self.assertEqual(r["status"], "UNALLOCATED_REMAINS")

    def test_provider_cost_cannot_overallocate(self):
        with self.assertRaisesRegex(ValueError, "invalid currency"):
            cost_reconcile(100, 120, "USD", "synthetic:bill")

    def test_provider_bill_does_not_claim_real(self):
        self.assertFalse(cost_reconcile(10, 10, "USD", "synthetic:bill")["is_real_invoice"])

    def test_example_is_synthetic_and_no_external_effect(self):
        r = synthetic_demo()
        self.assertEqual(r["kind"], "ENTIRELY_SYNTHETIC")
        self.assertFalse(r["real_inference_or_external_effects"])


if __name__ == "__main__":
    unittest.main()
