"""P05-1 tests: no second ontology authority, no hidden permission, no real PII."""
from dataclasses import replace
import json
import unittest

from p05_1_ontology_readonly import (
    EvidenceEdge, as_jsonld, existing_state_machine_example, fixtures, instant,
    make_event, project, run,
)

NOW = "2026-11-04T08:00:00Z"
LATER = "2026-11-04T08:01:00Z"
BEFORE = "2026-11-04T07:59:59Z"


class OntologyProjectionTests(unittest.TestCase):
    def setUp(self):
        self.events = fixtures()

    def test_five_synthetic_events(self):
        self.assertEqual(len(self.events), 5)

    def test_all_events_provenance_hash(self):
        self.assertTrue(all(len(x.evidence_sha256) == 64 for x in self.events))
        self.assertTrue(all(x.source_fact_id.startswith("synthetic:") for x in self.events))

    def test_reproducible_fixture_hashes(self):
        self.assertEqual([x.event_id for x in self.events],
                         [x.event_id for x in fixtures()])

    def test_event_dedup_is_idempotent(self):
        p = project(self.events + self.events,
                    knowledge_cutoff=LATER, world_time=LATER)
        self.assertEqual(p["n_source_events"], 5)

    def test_deterministic_projection(self):
        a = project(self.events, knowledge_cutoff=LATER, world_time=LATER)
        b = project(list(reversed(self.events)), knowledge_cutoff=LATER, world_time=LATER)
        self.assertEqual(a, b)

    def test_recorded_time_prevents_future_leakage(self):
        early = project(self.events, knowledge_cutoff=BEFORE, world_time=LATER)
        self.assertEqual(early["n_source_events"], 0)

    def test_world_time_prevents_inaccurate_history(self):
        early = project(self.events, knowledge_cutoff=LATER, world_time=BEFORE)
        self.assertEqual(early["n_source_events"], 0)

    def test_private_identifier_rejected(self):
        with self.assertRaises(ValueError):
            replace(self.events[0], subject="real:someone")

    def test_private_class_rejected(self):
        with self.assertRaises(ValueError):
            replace(self.events[0], privacy_class="personal_sensitive")

    def test_unknown_predicate_rejected(self):
        with self.assertRaises(ValueError):
            replace(self.events[0], predicate="CAN_EXECUTE")

    def test_inferred_not_observed(self):
        p = project(self.events, knowledge_cutoff=LATER, world_time=LATER)
        self.assertEqual([x["epistemic_status"] for x in p["edges"]
                          if x["predicate"] == "PROPOSED_ACTION"],
                         ["INFERRED_NOT_VERIFIED"])

    def test_provider_receipt_not_outcome(self):
        p = project(self.events, knowledge_cutoff=LATER, world_time=LATER)
        self.assertEqual([x["epistemic_status"] for x in p["edges"]
                          if x["predicate"] == "RECEIPT_FOR"],
                         ["PROVIDER_RECEIPT_NOT_OUTCOME"])

    def test_only_independent_readback_allowed_to_claim_readback(self):
        with self.assertRaises(ValueError):
            replace(self.events[-1], verifier="synthetic:executor")

    def test_readback_without_independent_source_rejected(self):
        with self.assertRaises(ValueError):
            replace(self.events[-1], source_kind="synthetic_model_inference")

    def test_fabricated_inference_cannot_include_verifier(self):
        with self.assertRaises(ValueError):
            replace(self.events[2], verifier="synthetic:observer")

    def test_invalid_hash_rejected(self):
        with self.assertRaises(ValueError):
            replace(self.events[0], evidence_sha256="not-hashed")

    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            replace(self.events[0], source_kind="real_unverified")

    def test_conflicting_node_types_rejected(self):
        conflict = replace(
            self.events[0],
            event_id="a" * 64,
            subject_kind="Action",
        )
        with self.assertRaises(ValueError):
            project(self.events + [conflict], knowledge_cutoff=LATER, world_time=LATER)

    def test_conflicting_id_rejected(self):
        conflict = replace(self.events[0], object="synthetic:goal-02")
        with self.assertRaises(ValueError):
            project(self.events + [conflict], knowledge_cutoff=LATER, world_time=LATER)

    def test_no_permission_or_real_causal_proof_from_graph(self):
        p = project(self.events, knowledge_cutoff=LATER, world_time=LATER)
        self.assertFalse(p["can_authorize_execution"])
        self.assertFalse(p["can_prove_real_world_effect"])

    def test_existing_manager_core_state_machine_reused(self):
        result = existing_state_machine_example()
        self.assertTrue(result["manager_core_reused"])
        self.assertEqual(result["state_history"],
                         ["OBSERVED", "HYPOTHESIZED", "NO_ACTION"])
        self.assertEqual(result["causal_unsupported_choice"], "NO_ACTION")
        self.assertFalse(result["executed_real_action"])

    def test_jsonld_uses_real_w3c_prefix(self):
        obj = as_jsonld(project(self.events, knowledge_cutoff=LATER, world_time=LATER))
        self.assertEqual(obj["@context"]["prov"], "http://www.w3.org/ns/prov#")
        self.assertEqual(obj["@graph"][0]["@type"], "prov:Entity")

    def test_jsonld_refuses_to_claim_execution_authority(self):
        graph = project(self.events, knowledge_cutoff=LATER, world_time=LATER)
        graph["can_authorize_execution"] = True
        with self.assertRaises(ValueError):
            as_jsonld(graph)

    def test_offset_aware_datetime_required(self):
        with self.assertRaises(ValueError):
            instant("2026-11-04T10:00:00")

    def test_late_recording_keeps_history_invisible(self):
        late = replace(self.events[0],
                       event_id="b"*64,
                       recorded_at="2026-11-05T08:00:00Z")
        p = project([late], knowledge_cutoff="2026-11-04T23:59:59Z",
                    world_time="2026-11-06T00:00:00Z")
        self.assertEqual(p["n_source_events"], 0)

    def test_output_contains_only_synthetic(self):
        report = run()
        self.assertTrue(report["limitations"]["no_real_users"])
        self.assertFalse(report["after_recorded"]["can_authorize_execution"])
        self.assertEqual(report["before_recorded"]["n_source_events"], 0)
        self.assertEqual(report["after_recorded"]["n_source_events"], 5)


if __name__ == "__main__":
    unittest.main()
