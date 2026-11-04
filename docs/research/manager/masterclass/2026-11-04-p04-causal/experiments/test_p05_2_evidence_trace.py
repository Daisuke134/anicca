"""P05-2 contract correlation tests. All data synthetic; no API calls."""
from __future__ import annotations

from dataclasses import replace
import copy
import json
import unittest

from p05_2_evidence_trace import (
    ALLOWED, ROOT, SCHEMA, SCHEMA_SHA256, STAMP, StampedRecord,
    fixture_records, join_trace, research_decision, research_prediction, run, when,
)

TENANT = "tenant-synthetic"
RUN = "run-synthetic"
CUTOFF = "2026-11-04T09:04:00Z"
BASE = fixture_records()


def changed(items, kind, **updates):
    """Revalidate a copied record with selected synthetic mutations."""
    output = []
    for item in items:
        if item.kind == kind:
            rec=copy.deepcopy(item.record)
            rec.update(updates)
            output.append(StampedRecord(kind=kind,record=rec,
                                        known_at=item.known_at,source_ref=item.source_ref))
        else:
            output.append(item)
    return tuple(output)


class EvidenceTraceTests(unittest.TestCase):
    def query(self, records=BASE, cutoff=CUTOFF, tenant=TENANT, run_id=RUN):
        return join_trace(records, known_at=cutoff, tenant_id=tenant, run_id=run_id)

    def test_existing_contract_loaded(self):
        self.assertIn("$defs", SCHEMA)
        self.assertIn("Receipt", SCHEMA["$defs"])

    def test_contract_has_real_sha256(self):
        self.assertEqual(len(SCHEMA_SHA256), 64)

    def test_fixture_records_all_match_existing_schema(self):
        self.assertEqual(len(BASE), 4)
        self.assertEqual({x.kind for x in BASE}, ALLOWED)

    def test_source_types_preserved(self):
        self.assertEqual({r.kind for r in BASE},
                         {"job", "effect", "receipt", "runtime_event"})

    def test_times_must_be_offset_aware(self):
        with self.assertRaises(ValueError):
            when("2026-11-04T09:03:00")

    def test_early_does_not_leak_future_execution(self):
        z=self.query(cutoff="2026-11-04T09:00:00Z")
        self.assertEqual(z["n_source_records"],0)
        self.assertIsNone(z["links"]["effect_id"])

    def test_effect_visible_when_known(self):
        z=self.query(cutoff="2026-11-04T09:00:10Z")
        self.assertEqual(z["n_source_records"],2)
        self.assertTrue(z["effect_tracking"]["has_effect_intent"])
        self.assertFalse(z["effect_tracking"]["has_provider_receipt"])

    def test_receipt_appears_when_recorded(self):
        z=self.query(cutoff="2026-11-04T09:01:10Z")
        self.assertEqual(z["n_source_records"],3)
        self.assertEqual(z["links"]["receipt_id"],"receipt-synthetic")

    def test_runtime_event_last(self):
        z=self.query()
        self.assertEqual(z["n_source_records"],4)
        self.assertTrue(z["effect_tracking"]["has_runtime_event"])

    def test_effect_id_is_not_idempotency_key(self):
        z=self.query()
        self.assertNotEqual(z["links"]["effect_id"],z["links"]["idempotency_key"])
        self.assertEqual(z["links"]["idempotency_key"],"idem-synthetic")

    def test_no_false_join_between_independent_no_action_and_historic_effect(self):
        z=self.query()
        self.assertIsNone(z["producer_linkage"]["decision_id"])
        self.assertIsNone(z["producer_linkage"]["model_id"])
        self.assertEqual(z["producer_linkage"]["status"],
                         "PREDICTION_AND_DECISION_PRODUCER_NOT_LINKED")

    def test_prediction_is_existing_core_p0(self):
        z=research_prediction()
        self.assertEqual(z.proof_level,"P0")
        self.assertFalse(z.causal_support)
        self.assertEqual(z.human_outcome,"NOT_MEASURED")

    def test_manager_core_refuses_unsupported_intervention(self):
        self.assertEqual(research_decision(),("NO_ACTION","none"))

    def test_receipt_looked_up_by_effect_id_not_receipt_id(self):
        self.assertEqual(self.query()["links"]["receipt_id"],"receipt-synthetic")

    def test_provider_receipt_never_becomes_human_effect(self):
        z=self.query()
        self.assertEqual(z["effect_tracking"]["receipt_outcome"],"uncertain")
        self.assertEqual(z["effect_tracking"]["human_impact"],"NOT_MEASURED")
        self.assertFalse(z["can_prove_causal_effect"])

    def test_no_execution_grant_from_trace(self):
        z=self.query()
        self.assertFalse(z["can_execute"])
        self.assertEqual(z["action_permission"],"NEVER_ISSUED_BY_TRACE")

    def test_missing_prediction_decision_ids_are_explicit(self):
        z=self.query()
        self.assertIsNone(z["links"]["prediction_id"])
        self.assertIsNone(z["links"]["decision_id"])
        self.assertTrue(z["links"]["prediction_source_ref"].startswith("synthetic://"))
        self.assertIn("prediction_id_not_in_existing_job_effect_receipt_runtime_event",
                      z["unresolved_contract_gaps"])

    def test_exact_duplicate_idempotent(self):
        z=self.query(BASE+BASE)
        self.assertEqual(z,self.query())

    def test_conflicting_duplicate_rejected(self):
        item=BASE[0]
        mutate=copy.deepcopy(item.record)
        mutate["max_attempts"]=2
        diff=StampedRecord(kind="job",record=mutate,source_ref=item.source_ref,
                           known_at=item.known_at)
        with self.assertRaises(ValueError):
            self.query(BASE+(diff,))

    def test_external_mutation_detected(self):
        values=list(fixture_records())
        values[0].record["max_attempts"]=8
        with self.assertRaises(ValueError):
            self.query(values)

    def test_missing_effect_but_receipt_rejected(self):
        just=(BASE[0],BASE[2])
        with self.assertRaises(ValueError):
            self.query(just)

    def test_no_receipt_is_unknown_not_success(self):
        z=self.query(fixture_records(include_receipt=False,include_event=False))
        self.assertFalse(z["effect_tracking"]["has_provider_receipt"])
        self.assertEqual(z["effect_tracking"]["receipt_outcome"],"MISSING")

    def test_late_receipt_invisible_until_known(self):
        data=fixture_records(late_receipt=True)
        z=self.query(data)
        self.assertEqual(z["links"]["receipt_id"],None)
        self.assertEqual(z["n_source_records"],3)
        z2=self.query(data,cutoff="2026-11-05T13:00:00Z")
        self.assertEqual(z2["links"]["receipt_id"],"receipt-synthetic")

    def test_cross_tenant_rejected(self):
        with self.assertRaises(ValueError):
            self.query(tenant="other-tenant")

    def test_cross_run_filtered_without_spurious_join(self):
        z=self.query(run_id="run-foreign")
        self.assertIsNone(z["links"]["job_id"])
        self.assertIsNone(z["links"]["effect_id"])

    def test_wrong_effect_class_rejected(self):
        with self.assertRaises(ValueError):
            self.query(changed(BASE,"effect",effect_class="publish"))

    def test_wrong_effect_key_rejected(self):
        with self.assertRaises(ValueError):
            self.query(changed(BASE,"effect",idempotency_key="idem-wrong"))

    def test_wrong_receipt_effect_id_rejected(self):
        with self.assertRaises(ValueError):
            self.query(changed(BASE,"receipt",effect_id="effect-foreign"))

    def test_wrong_receipt_provider_rejected(self):
        with self.assertRaises(ValueError):
            self.query(changed(BASE,"receipt",provider="foreign-provider"))

    def test_wrong_receipt_run_id_rejected(self):
        with self.assertRaises(ValueError):
            self.query(changed(BASE,"receipt",run_id="run-foreign"))

    def test_wrong_runtime_owner_rejected(self):
        with self.assertRaises(ValueError):
            self.query(changed(BASE,"runtime_event",owner_id="other-tenant"))

    def test_wrong_runtime_job_id_rejected(self):
        with self.assertRaises(ValueError):
            self.query(changed(BASE,"runtime_event",job_id="foreign-job",
                               occurrence_id="foreign-job:occ-1"))

    def test_wrong_runtime_receipt_id_rejected(self):
        with self.assertRaises(ValueError):
            self.query(changed(BASE,"runtime_event",provider_receipt_id="foreign-receipt"))

    def test_broken_schema_unknown_column_rejected(self):
        item=BASE[0]
        v=copy.deepcopy(item.record)
        v["authorized_execution"]=True
        with self.assertRaises(Exception):
            StampedRecord(kind="job",record=v,source_ref=item.source_ref,known_at=item.known_at)

    def test_receipt_verified_still_is_not_causal_proof(self):
        data=changed(BASE,"receipt",outcome="verified",
                     external_ref="synthetic://provider-ack",
                     evidence_refs=["synthetic://receipt-proof"])
        z=self.query(data)
        self.assertEqual(z["effect_tracking"]["receipt_outcome"],"verified")
        self.assertFalse(z["effect_tracking"]["has_confirmed_independent_outcome"])
        self.assertFalse(z["can_prove_causal_effect"])

    def test_malformed_receipt_proof_rejected_by_existing_schema(self):
        with self.assertRaises(Exception):
            changed(BASE,"receipt",outcome="verified")

    def test_runtime_receipt_ref_without_receipt_record_is_not_verification(self):
        z=self.query(fixture_records(include_receipt=True,late_receipt=True))
        self.assertFalse(z["effect_tracking"]["has_provider_receipt"])
        self.assertFalse(z["effect_tracking"]["has_confirmed_independent_outcome"])

    def test_replay_returns_stable_source_hashes(self):
        a=self.query()
        b=self.query(fixture_records())
        self.assertEqual(a["observed_evidence"],b["observed_evidence"])

    def test_underlying_runtime_schema_not_modified(self):
        p=ROOT/"runtime/contracts/common-record.schema.json"
        import hashlib
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),SCHEMA_SHA256)

    def test_standalone_run_all_timepoints(self):
        z=run()
        self.assertEqual(z["post_receipt_and_runtime_event"]["n_source_records"],4)
        self.assertFalse(z["new_authoritative_schema_created"])
        self.assertEqual(z["standalone_core_safety_checks"]["unlinked_no_action_choice"],"NO_ACTION")
        self.assertFalse(z["standalone_core_safety_checks"]["linked_to_synthetic_job"])

if __name__=="__main__":
    unittest.main()
