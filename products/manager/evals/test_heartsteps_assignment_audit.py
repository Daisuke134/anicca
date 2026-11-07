"""Synthetic contract tests; these do not themselves measure human effects."""
import math
import unittest
from heartsteps_assignment_audit import make_eligible_rows, fit_assignment_model, aggregate_report, reconstruct_author_cohort, fit_average_assignment_model

def row(user, j, assigned, delivered=None, pre=10.0, outcome=5.0, available=True):
    return {
        "user.index": str(user), "decision.index.nogap": str(j),
        "avail": "True" if available else "False",
        "is.randomized": "True" if assigned else "False",
        "send": "True" if (assigned if delivered is None else delivered) else "False",
        "jbsteps30.zero": str(outcome), "jbsteps30pre.zero": str(pre),
    }

def synthetic_rows():
    result=[]
    for person in range(1,7):
        for j in range(0,45,5):
            assignment=(j//5 + person)%2==0
            pre=6.0+person*2+(j%7)
            time=j/5/42
            linear=1.1+.12*math.log(pre+.5)+.18*time+(.25-.22*time)*(int(assignment)-.6)
            result.append(row(person,j,assignment,pre=pre,outcome=math.exp(linear)-.5))
    return result

class HeartStepsAuditTests(unittest.TestCase):
    def test_author_cohort_uses_local_study_days_and_source_anomaly_rules(self):
        import datetime
        data = []
        for person in ("1", "2", "3"):
            for day in range(44):
                r = row(person, day, day % 2 == 0)
                # In UTC this timestamp falls the next day; local day comes
                # from the original per-row UTC offset, not timezone-less text.
                t = datetime.datetime(2026, 1, 1, 3) + datetime.timedelta(days=day)
                r["sugg.select.utime"] = str(t)
                r["sugg.gmtoff"] = "-18000.0"
                r["send.active"] = "False"
                r["send.sedentary"] = "False"
                data.append(r)
        travel = dict(data[0])
        travel["decision.index.nogap"] = ""
        data.append(travel)
        # Two original source-guard anomalies within 42 study days.
        data[0]["avail"]="False";data[0]["send"]="True"
        data[45]["send.active"]=""
        clean, audit = reconstruct_author_cohort(data)
        self.assertEqual(audit["travel_or_technical_unindexed"], 1)
        self.assertEqual(audit["after_study_day_42"], 6)
        self.assertEqual(audit["anomaly_rows"], 2)
        self.assertEqual(len(clean), 124)
        self.assertTrue(all(r["decision.index.nogap"] for r in clean))

    def test_author_cohort_keeps_startup_unavailable_row_with_no_timestamp(self):
        data=synthetic_rows()
        for r in data:
            r["sugg.select.utime"]="2026-01-01 05:00:00"
            r["sugg.gmtoff"]="-18000.0"
            r["send.active"]="False"
            r["send.sedentary"]="False"
        missing=row("startup",0,False,available=False)
        missing.update({"sugg.select.utime":"","sugg.gmtoff":"",
                        "send":"","is.randomized":"",
                        "send.active":"False","send.sedentary":"False"})
        cohort,audit=reconstruct_author_cohort(data+[missing])
        self.assertEqual(len(cohort),len(data)+1)
        self.assertEqual(audit["startup_undated_rows"],1)

    def test_eligibility_and_missing_indexes(self):
        rows=synthetic_rows()
        rows.extend([row("extra",210,True),row("extra2",5,True,available=False),row("extra3","",True)])
        eligible=make_eligible_rows(rows)
        self.assertEqual(len(eligible),54)
        self.assertEqual(len(set(r["uid"] for r in eligible)),6)

    def test_assignment_and_delivery_differ(self):
        rows=synthetic_rows()
        rows[0]["send"]="False" if rows[0]["is.randomized"]=="True" else "True"
        out=aggregate_report(rows,bootstrap_reps=100,seed=19)
        self.assertEqual(out["assignment_delivery_disagreement"],1)
        self.assertEqual(out["assignment_probability_used"],.6)
        self.assertEqual(out["causal_status"],"ASSIGNMENT_ANALYSIS_NOT_ORIGINAL_PAPER_REPLICATION")

    def test_recovers_constant_assignment_ratio(self):
        rows=make_eligible_rows(synthetic_rows())
        for r in rows:
            # Fixture with known constant log ratio irrespective of study day
            r["steps"]=math.exp(1.1+.12*math.log(r["steps_pre"]+.5)+
                                .18*r["day_scaled"]+.17*(r["assignment"]-.6))-.5
        est=fit_average_assignment_model(rows)
        self.assertAlmostEqual(est["average_log_ratio"], math.exp(.17),delta=1e-6)

    def test_recovers_known_log_effect(self):
        fit=fit_assignment_model(make_eligible_rows(synthetic_rows()))
        self.assertAlmostEqual(fit["beta_assignment_day0"],.25,delta=1e-6)
        self.assertAlmostEqual(fit["beta_assignment_day_interaction"],-.22,delta=1e-6)
        self.assertAlmostEqual(fit["log_pre_coefficient"],.12,delta=1e-6)

    def test_missing_outcome_fails_closed(self):
        rows=synthetic_rows();rows[0]["jbsteps30.zero"]=""
        with self.assertRaises(ValueError):make_eligible_rows(rows)

    def test_duplicate_id_fails(self):
        rows=synthetic_rows();rows.append(dict(rows[0]))
        with self.assertRaisesRegex(ValueError,"duplicate"):make_eligible_rows(rows)

    def test_unrecorded_randomization_fails(self):
        rows=synthetic_rows();rows[0]["is.randomized"]=""
        with self.assertRaises(ValueError):make_eligible_rows(rows)

    def test_not_falsely_published_cohort(self):
        result=aggregate_report(synthetic_rows(),bootstrap_reps=100,seed=7)
        self.assertFalse(result["original_6061_cohort_exactly_reproduced"])
        self.assertFalse(result["published_35_steps_causally_reproduced"])

    def test_bootstrap_deterministic(self):
        a=aggregate_report(synthetic_rows(),bootstrap_reps=100,seed=7)
        b=aggregate_report(synthetic_rows(),bootstrap_reps=100,seed=7)
        self.assertEqual(a["cluster_bootstrap_95ci_ratio_day0"],b["cluster_bootstrap_95ci_ratio_day0"])
        self.assertTrue(all(math.isfinite(x) for x in a["cluster_bootstrap_95ci_ratio_day0"]))

if __name__=="__main__":
    unittest.main()
