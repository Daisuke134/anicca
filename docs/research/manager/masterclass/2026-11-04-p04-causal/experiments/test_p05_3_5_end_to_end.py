"""P05-3/4/5 offline fixture test boundaries; NO real provider or keys."""
import json
import sqlite3
import unittest
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from p05_3_5_end_to_end import (
    NOW, ACTION, TARGET, DOMAIN, COST, FIXTURE_ISSUER,
    grant_scope, p05_3_authority_and_roles, p05_4_outbox_recovery,
    p05_5_shadow_only, p05_5_state_machine, run,
)
from manager_core.adapters.fixtures import OfflineFixtureAdapter, OfflineFixtureSensor
from manager_core.outbox import DurableOutbox
from manager_core.reconcile import Reconciler
from manager_core.verifier import ExternalReadback, verify_outcome
from manager_core.evaluator import evaluate_outcome
from manager_core.state_machine import State, StateMachine


class P05Phase5IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run()

    def test_01_authority_accepts_scoped_fixture(self):
        self.assertTrue(self.report["P05_3"]["fixture_grant_accepted"])

    def test_02_authority_denial_six_cases(self):
        self.assertEqual(self.report["P05_3"]["negative_cases_count"], 6)
        self.assertEqual(set(self.report["P05_3"]["negative_authority_cases"].values()), {"DENIED"})

    def test_03_planner_has_no_live_authority(self):
        self.assertFalse(self.report["P05_3"]["planner_can_issue_real_authority"])

    def test_04_fixture_scope_not_live(self):
        self.assertFalse(self.report["P05_3"]["live_provider_supported"])

    def test_05_invalid_scope_target_fails(self):
        a,g,s = grant_scope()
        with self.assertRaises(PermissionError):
            a.authorize(g,s,DOMAIN,ACTION,"synthetic:foreign",COST,NOW)

    def test_06_revoke_grant_fails(self):
        a,g,s = grant_scope(revoked=True)
        with self.assertRaises(PermissionError):
            a.authorize(g,s,DOMAIN,ACTION,TARGET,COST,NOW)

    def test_07_expired_grant_fails(self):
        a,g,s = grant_scope(expired=True)
        with self.assertRaises(PermissionError):
            a.authorize(g,s,DOMAIN,ACTION,TARGET,COST,NOW)

    def test_08_untrusted_issuer_fails(self):
        a,g,s = grant_scope()
        with self.assertRaises(PermissionError):
            a.authorize(g,"1"*64,DOMAIN,ACTION,TARGET,COST,NOW)

    def test_09_bounded_budget_enforced(self):
        a,g,s = grant_scope()
        with self.assertRaises(PermissionError):
            a.authorize(g,s,DOMAIN,ACTION,TARGET,1.00,NOW)

    def test_10_live_adapter_rejected(self):
        a,g,s = grant_scope()
        class FakeLiveProvider:
            domain,action,target=DOMAIN,ACTION,TARGET
            def send(self,k):
                raise AssertionError("MUST NOT CALL")
        with TemporaryDirectory() as t:
            o = DurableOutbox(Path(t)/"outbox.sqlite")
            with self.assertRaises(PermissionError):
                o.execute("bad-live",g,s,a,FakeLiveProvider(),COST,NOW)
            self.assertIsNone(o.record("bad-live"))

    def test_11_one_fixture_send_with_replay(self):
        x=self.report["P05_4"]["one_explicit_fixture_effect"]
        self.assertEqual(x["provider_send_calls"], 1)
        self.assertEqual(x["first_status"],"SUBMITTED")
        self.assertEqual(x["replayed_status"],"SUBMITTED")

    def test_12_independent_fixture_sensor_not_real(self):
        x=self.report["P05_4"]["one_explicit_fixture_effect"]
        self.assertEqual(x["result"],"VERIFIED_FIXTURE_ONLY")
        self.assertEqual(x["proof_level"],"P0")

    def test_13_no_welfare_result_imputed(self):
        r=self.report["P05_4"]
        self.assertIsNone(r["net_welfare_estimated"])
        self.assertEqual(r["net_welfare_status"],"NO_COMPARATOR")

    def test_14_timeout_after_effect_unknown(self):
        x=self.report["P05_4"]["uncertain_then_reconciled_fixture_effect"]
        self.assertEqual(x["initial_status"],"UNKNOWN")

    def test_15_unknown_lookup_prevents_retry(self):
        x=self.report["P05_4"]["uncertain_then_reconciled_fixture_effect"]
        self.assertEqual(x["provider_lookup_failed_status"],"UNKNOWN")
        self.assertEqual(x["retry_send_calls"],0)

    def test_16_reconciliation_only_after_readback(self):
        x=self.report["P05_4"]["uncertain_then_reconciled_fixture_effect"]
        self.assertEqual(x["reconciled_status"],"PRESENT")
        self.assertEqual(x["final_record_status"],"PRESENT")

    def test_17_receipt_does_not_count_as_causal_effect(self):
        self.assertFalse(self.report["external_field_RCT_completed"])
        self.assertFalse(self.report["P05_4"]["independent_field_outcome_measured"])

    def test_18_owner_self_readback_not_independent(self):
        a,g,s=grant_scope()
        with TemporaryDirectory() as t:
            outbox=DurableOutbox(Path(t)/"db.sqlite")
            adapter=OfflineFixtureAdapter(DOMAIN,ACTION,TARGET)
            effect=outbox.execute("sensor-check",g,s,a,adapter,COST,NOW)
            readback=ExternalReadback(
                effect_key=effect.key,
                source="fixture-executor",
                executor_source="fixture-executor",
                recorded_at=NOW + timedelta(minutes=1),
                observed_value=10.0,
                receipt_ref=effect.receipt_ref,
            )
            result=verify_outcome(effect,readback)
            self.assertEqual(result.status,"NOT_VERIFIED")

    def test_19_no_comparator_not_benefit(self):
        x=evaluate_outcome(1,0,2,.1,None,None,"welfare")
        self.assertIsNone(x.net_effect)
        self.assertEqual(x.proof_level,"P0")

    def test_20_actual_existing_shadow_gate_disabled(self):
        x=self.report["P05_5"]
        self.assertEqual((x["status"],x["reason"]),("SKIPPED","DISABLED"))

    def test_21_shadow_zero_external_calls(self):
        x=self.report["P05_5"]
        self.assertEqual(x["llm_or_provider_calls"],0)

    def test_22_shadow_does_not_install_product(self):
        self.assertFalse(self.report["P05_5"]["production_installation"])
        self.assertEqual(self.report["real_external_service_mutations"],0)

    def test_23_terminal_no_action_stays_terminal(self):
        self.assertEqual(self.report["terminal_no_action"]["state_history"],
                         ["OBSERVED","HYPOTHESIZED","NO_ACTION"])
        self.assertTrue(self.report["terminal_no_action"]["no_action_terminal"])

    def test_24_cannot_escalate_terminal_state(self):
        state=StateMachine()
        state.transition(State.NO_ACTION)
        with self.assertRaises(ValueError):
            state.transition(State.AUTHORIZED)

    def test_25_product_runtime_not_promoted(self):
        self.assertFalse(self.report["production_feature_gate_accepted"])
        self.assertFalse(self.report["P05_5"]["production_installation"])

    def test_26_no_weight_training_claim(self):
        self.assertFalse(self.report["actual_model_weights_trained"])

    def test_27_no_real_people_affected(self):
        self.assertEqual(self.report["real_people_affected"],0)

    def test_28_no_company_effect_delegated(self):
        self.assertEqual(self.report["real_company_decisions_delegated"],0)

    def test_29_outbox_belongs_in_temp_storage(self):
        self.assertTrue(self.report["P05_4"]["all_mutations_within_temporary_fixture_sqlite"])

    def test_30_duplicate_conflicting_action_not_reused(self):
        a,g,s=grant_scope()
        with TemporaryDirectory() as t:
            out=DurableOutbox(Path(t)/"db.sqlite")
            adapter=OfflineFixtureAdapter(DOMAIN,ACTION,TARGET)
            out.execute("same-key",g,s,a,adapter,COST,NOW)
            with self.assertRaises(ValueError):
                out.execute("same-key",g,s,a,adapter,0.02,NOW)
            self.assertEqual(adapter.send_calls,1)

    def test_31_budget_cumulative_not_per_effect(self):
        a,g,s=grant_scope(limit=.015)
        with TemporaryDirectory() as t:
            out=DurableOutbox(Path(t)/"db.sqlite")
            adapter=OfflineFixtureAdapter(DOMAIN,ACTION,TARGET)
            out.execute("one",g,s,a,adapter,.01,NOW)
            with self.assertRaises(PermissionError):
                out.execute("two",g,s,a,adapter,.01,NOW)
            self.assertEqual(adapter.send_calls,1)

    def test_32_provider_before_effect_failure_recover_unknown(self):
        a,g,s=grant_scope()
        with TemporaryDirectory() as t:
            out=DurableOutbox(Path(t)/"db.sqlite")
            adapter=OfflineFixtureAdapter(
                DOMAIN,ACTION,TARGET,timeout_before_effect=True)
            rec=out.execute("failed",g,s,a,adapter,COST,NOW)
            self.assertEqual(rec.status,"UNKNOWN")
            adapter.lookup_fails=True
            found=Reconciler(out).reconcile(rec.key,adapter)
            self.assertEqual(found.status,"UNKNOWN")
            self.assertEqual(adapter.send_calls,1)

    def test_33_reopen_outbox_preserves_idempotence(self):
        a,g,s=grant_scope()
        with TemporaryDirectory() as t:
            path=Path(t)/"db.sqlite"
            a1=DurableOutbox(path)
            adapter=OfflineFixtureAdapter(DOMAIN,ACTION,TARGET)
            rec=a1.execute("again",g,s,a,adapter,COST,NOW)
            reopened=DurableOutbox(path)
            second=reopened.execute("again",g,s,a,adapter,COST,NOW)
            self.assertEqual(second,rec)
            self.assertEqual(adapter.send_calls,1)

    def test_34_shadow_not_fabricated_gain(self):
        self.assertEqual(self.report["P05_5"]["shadow_candidate_quality"],
                         "NOT EVALUATED")

    def test_35_shadow_return_fixed_public_keys(self):
        keys=self.report["P05_5"]["public_projection_keys"]
        self.assertIn("proof_level",keys)
        self.assertIn("authorized_execution",keys)
        self.assertNotIn("api_key",keys)

    def test_36_only_offline_study_fixture_used(self):
        self.assertIn("EXISTING",self.report["P05_4"]["outbox_class"])
        self.assertIn("manager_core.owned_provider_shadow.",
                      self.report["P05_5"]["existing_shadow"])


if __name__=="__main__":
    unittest.main()
