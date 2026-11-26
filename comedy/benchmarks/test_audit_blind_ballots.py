#!/usr/bin/env python3
"""Executable negative/positive controls for the ballot provenance gate."""
import copy
import unittest
from audit_blind_ballots import audit, packet_sha256


def fixture():
    def p(a, b):
        return {
            "pair_id": "p1", "category": "oogiri", "prompt": "架空の一題",
            "A": a, "B": b,
            "rating": {"preferred": "NOT_MEASURED", "allowed": ["A", "B", "TIE"],
                       "reason": "NOT_MEASURED"}
        }
    return {
        "schema": "offline_counterbalanced_review_v1",
        "task_set": "original_development_not_fixed_benchmark",
        "pairs": 1, "candidate_count": 2,
        "variants": {"v1": [p("候補一", "候補二")],
                     "v2": [p("候補二", "候補一")]},
        "review_status": "NOT_MEASURED", "human_judgments": 0,
        "publish_enabled": False, "auto_reply_enabled": False
    }


def ballot(packet, rater="r1", variant="v1", choice="A", source="synthetic"):
    return {
        "rater_id": rater, "variant": variant, "pair_id": "p1",
        "preferred": choice, "source_type": source,
        "packet_sha256": packet_sha256(packet)
    }


class BallotAuditTests(unittest.TestCase):
    def test_zero_votes_means_no_humor_measurement(self):
        r = audit(fixture(), [])
        self.assertEqual(r["human_status"], "NOT_MEASURED")
        self.assertEqual(r["total_ballots"], 0)

    def test_synthetic_ballots_never_become_human_preferences(self):
        p = fixture()
        rows = [ballot(p), ballot(p, rater="r2", variant="v2", choice="B")]
        r = audit(p, rows)
        self.assertEqual(r["synthetic_ballots"], 2)
        self.assertEqual(r["human_declared_ballots"], 0)
        self.assertEqual(r["human_tallies_by_anonymous_v1_position"]["p1"]["v1_A"], 0)
        self.assertEqual(r["human_status"], "NOT_MEASURED")

    def test_human_declared_a_b_mapping_is_position_invariant(self):
        p = fixture()
        rows = [ballot(p, source="human_declared"),
                ballot(p, rater="r2", variant="v2", choice="B", source="human_declared")]
        r = audit(p, rows)
        self.assertEqual(r["human_tallies_by_anonymous_v1_position"]["p1"]["v1_A"], 2)
        self.assertEqual(r["pairs_with_both_human_orderings"], 1)
        self.assertEqual(r["human_status"], "SELF_REPORTED_HUMAN_UNVERIFIED")

    def test_one_sided_ballots_not_position_balanced(self):
        p = fixture()
        r = audit(p, [ballot(p, source="human_declared")])
        self.assertEqual(r["position_balance_status"], "INCOMPLETE")

    def test_same_rater_cannot_view_both_orders(self):
        p = fixture()
        with self.assertRaisesRegex(ValueError, "one rater"):
            audit(p, [ballot(p), ballot(p, variant="v2")])

    def test_same_rater_cannot_duplicate_one_pair(self):
        p = fixture()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            audit(p, [ballot(p), ballot(p)])

    def test_packet_fingerprint_mismatch_rejected(self):
        p = fixture()
        b = ballot(p)
        b["packet_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            audit(p, [b])

    def test_unknown_pair_rejected(self):
        p = fixture()
        b = ballot(p)
        b["pair_id"] = "p2"
        with self.assertRaisesRegex(ValueError, "unknown"):
            audit(p, [b])

    def test_invalid_preference_rejected(self):
        p = fixture()
        b = ballot(p)
        b["preferred"] = "FUNNIEST"
        with self.assertRaisesRegex(ValueError, "invalid"):
            audit(p, [b])

    def test_source_type_is_mandatory(self):
        p = fixture()
        b = ballot(p)
        del b["source_type"]
        with self.assertRaisesRegex(ValueError, "source_type"):
            audit(p, [b])

    def test_packet_with_noninverse_variants_rejected(self):
        p = fixture()
        p["variants"]["v2"][0]["B"] = "第三の回答"
        with self.assertRaisesRegex(ValueError, "inverse"):
            audit(p, [])

    def test_unblinded_model_label_rejected(self):
        p = fixture()
        p["variants"]["v1"][0]["model"] = "model-X"
        with self.assertRaisesRegex(ValueError, "metadata"):
            audit(p, [])

    def test_prefilled_rating_rejected(self):
        p = fixture()
        p["variants"]["v1"][0]["rating"]["preferred"] = "A"
        with self.assertRaisesRegex(ValueError, "pre-filled"):
            audit(p, [])

    def test_publish_enabled_rejected(self):
        p = fixture()
        p["publish_enabled"] = True
        with self.assertRaisesRegex(ValueError, "OFF"):
            audit(p, [])


if __name__ == "__main__":
    unittest.main()
