"""Deterministic fairness and safety tests for the four synthetic query backends."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
import json
import unittest

from p05_1_four_way_benchmark import (
    CUTOFF, FUTURE_CUTOFF, WORLD_TIME, DictIndex, FlatScan,
    GraphProjection, Question, SQLiteIndex, generate_questions, oracle,
    run_size, synthetic_events,
)
from p05_1_ontology_readonly import instant


class FourWayQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.n = 40
        cls.events = synthetic_events(cls.n)
        cls.flat = FlatScan(cls.events)
        cls.sqlite = SQLiteIndex(cls.events)
        cls.direct = DictIndex(cls.events)
        cls.graph = GraphProjection(cls.events)

    @classmethod
    def tearDownClass(cls):
        cls.sqlite.close()

    def assert_every_backend(self,q):
        exp=oracle(self.n,q)
        for method in (self.flat,self.sqlite,self.direct,self.graph):
            self.assertEqual(method.ask(q),exp,(method.__class__.__name__,q))

    def test_goal(self):
        self.assert_every_backend(Question("goal","synthetic:subject-00003"))

    def test_proposal(self):
        self.assert_every_backend(Question("proposals","synthetic:subject-00003"))

    def test_observation(self):
        self.assert_every_backend(Question("observations","synthetic:subject-00003"))

    def test_receipt(self):
        self.assert_every_backend(Question("receipts","synthetic:subject-00003"))

    def test_readback_present(self):
        self.assert_every_backend(Question("readbacks","synthetic:subject-00001"))

    def test_readback_absent(self):
        self.assert_every_backend(Question("readbacks","synthetic:subject-00000"))

    def test_multi_hop_trace(self):
        self.assert_every_backend(Question("trace","synthetic:subject-00011"))

    def test_unknown_person(self):
        self.assert_every_backend(Question("trace","synthetic:subject-99999"))

    def test_permission_never_inferred(self):
        self.assert_every_backend(Question("authority","synthetic:subject-00001"))

    def test_receipt_is_not_causal_proof(self):
        self.assert_every_backend(Question("causal_effect","synthetic:subject-00001"))

    def test_all_question_types_preverified(self):
        for q in generate_questions(self.n,how_many=80):
            self.assert_every_backend(q)

    def test_timestamps_utc(self):
        self.assertEqual(instant("2026-11-04T17:00:00+09:00"),
                         instant("2026-11-04T08:00:00Z"))

    def test_late_recording_does_not_leak(self):
        q=Question("observations","synthetic:subject-00000")
        self.assert_every_backend(q)
        self.assertEqual(self.direct.ask(q),("synthetic:observation-00000",))

    def test_future_recording_visible_after_cutoff(self):
        q=Question("observations","synthetic:subject-00000",
                   FUTURE_CUTOFF,FUTURE_CUTOFF)
        expected=oracle(self.n,q)
        self.assertEqual(self.flat.ask(q),expected)
        self.assertEqual(self.sqlite.ask(q),expected)
        self.assertEqual(DictIndex(self.events,FUTURE_CUTOFF,FUTURE_CUTOFF).ask(q),expected)
        self.assertEqual(GraphProjection(self.events,FUTURE_CUTOFF,FUTURE_CUTOFF).ask(q),expected)
        self.assertEqual(len(expected),3)

    def test_snapshot_wrong_time_rejected(self):
        q=Question("observations","synthetic:subject-00000",
                   FUTURE_CUTOFF,FUTURE_CUTOFF)
        for method in (self.direct,self.graph):
            with self.assertRaises(ValueError):
                method.ask(q)

    def test_multiple_rebuilds_idempotent(self):
        self.assertEqual(self.graph.graph,
                         GraphProjection(self.events+list(self.events)).graph)

    def test_invalid_question_rejected(self):
        q=Question("unguarded_send","synthetic:subject-00001")
        for method in (self.flat,self.sqlite,self.direct,self.graph):
            with self.assertRaises(ValueError):
                method.ask(q)

    def test_sqlite_has_indices(self):
        names={r[1] for r in self.sqlite.db.execute("PRAGMA index_list(claims)")}
        self.assertIn("source_query",names)
        self.assertIn("target_query",names)

    def test_direct_index_matches_ontology_graph_on_all_generated_data(self):
        for q in generate_questions(self.n,how_many=120):
            self.assertEqual(self.direct.ask(q),self.graph.ask(q))

    def test_deterministic_ground_truth(self):
        self.assertEqual([e.event_id for e in self.events],
                         [e.event_id for e in synthetic_events(self.n)])

    def test_size_guard(self):
        with self.assertRaises(ValueError):
            synthetic_events(2)

    def test_measurement_not_secret_or_personal(self):
        self.assertTrue(all(e.privacy_class=="synthetic_nonpersonal" for e in self.events))

    def test_end_to_end_benchmark_checks_truth(self):
        result=run_size(40,queries=48)
        self.assertTrue(result["truth_checked"])
        self.assertEqual(set(result["timings"]),
                         {"flat_scan","dict_index","sqlite_index","graph_projection"})
        self.assertTrue(all(v["errors"]==0 for v in result["correctness"].values()))
        self.assertTrue(result["time_travel_test"])


if __name__=="__main__":
    unittest.main()
