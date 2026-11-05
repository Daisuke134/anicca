"""Only synthetic structural software tests. No fabricated human efficacy."""
import unittest
from heartsteps_v1_real_mrt import summarize, truth, measure


class StudyContractTests(unittest.TestCase):
    def test_boolean_parser(self):
        self.assertIs(truth("TRUE"), True)
        self.assertIs(truth("False"), False)
        self.assertIsNone(truth("NA"))

    def test_measure_missing(self):
        self.assertIsNone(measure("NA"))
        self.assertIsNone(measure("-5"))
        self.assertIsNone(measure("nan"))

    def test_eligible_and_unavailable(self):
        rows=[]
        for i in range(6):
            rows.append({"user.index":str(i//2+1),"avail":"TRUE",
                "is.randomized":"TRUE", "send":"TRUE" if i%2 else "FALSE",
                "jbsteps30":str(i+1)})
        rows.append({"user.index":"5","avail":"FALSE","is.randomized":"FALSE",
            "send":"FALSE","jbsteps30":"999"})
        s=summarize(rows,reps=120)
        self.assertEqual(s["eligible_decisions"],6)
        self.assertEqual(s["source_participants"],4)
        self.assertAlmostEqual(s["observed_difference_steps"],1.0)

    def test_missing_by_arm(self):
        rows=[{"user.index":"1","avail":"TRUE","is.randomized":"TRUE","send":"TRUE","jbsteps30":"4"},
              {"user.index":"1","avail":"TRUE","is.randomized":"FALSE","send":"FALSE","jbsteps30":"2"},
              {"user.index":"2","avail":"TRUE","is.randomized":"TRUE","send":"TRUE","jbsteps30":"6"},
              {"user.index":"2","avail":"TRUE","is.randomized":"FALSE","send":"FALSE","jbsteps30":"4"},
              {"user.index":"3","avail":"TRUE","is.randomized":"FALSE","send":"FALSE","jbsteps30":"NA"}]
        s=summarize(rows,reps=120)
        self.assertEqual(s["missing_no_suggestion"],1)
        self.assertAlmostEqual(s["observed_difference_steps"],2.0)
        self.assertTrue(s["bootstrap_95ci_cluster_participant"])
        self.assertFalse(s["quality_of_life_measured"])

    def test_reject_missing_input(self):
        with self.assertRaises(ValueError):
            summarize([{"wrong":"fields"}],reps=120)

    def test_no_false_claim(self):
        self.assertIn("not an ITT",summarize([
            {"user.index":"1","avail":"TRUE","is.randomized":"TRUE","send":"TRUE","jbsteps30":"5"},
            {"user.index":"1","avail":"TRUE","is.randomized":"FALSE","send":"FALSE","jbsteps30":"2"},
        ],reps=120)["causal_claim"])


if __name__=="__main__":
    unittest.main()
