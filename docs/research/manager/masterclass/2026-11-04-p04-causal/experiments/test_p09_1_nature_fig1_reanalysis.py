"""Synthetic unit tests for P09-1 public Figure 1 descriptive analysis."""
import csv
import math
import tempfile
import unittest
from pathlib import Path
from p09_1_nature_fig1_reanalysis import (
    evaluate, mirror_coverage, read_contrasts, summarize, percentile, study_heldout_calibration,
)

def fixture_csv(path):
    with path.open("w", newline="") as f:
        w=csv.writer(f)
        w.writerow(("study","reference_condition","outcome","condition","human","prediction","group"))
        for study,n,m in (("S1",.2,.3),("S2",.4,.5),("S3",.6,.7)):
            w.writerow((study,"control","Y","treatment",n,m,"published"))
            w.writerow((study,"treatment","Y","control",-n,-m,"published"))

class TestReanalysis(unittest.TestCase):
    def setUp(self):
        self.d=tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        self.p=Path(self.d.name)/"source.csv"
        fixture_csv(self.p)
    def test_mirrored(self):
        self.assertEqual(mirror_coverage(read_contrasts(self.p))["share_rows_with_reverse"],1.0)
    def test_synthetic_perfect_linear_relation(self):
        s=summarize(read_contrasts(self.p))
        self.assertTrue(0.97 < s["pearson_r"] < 1.0)
        self.assertEqual(s["n"],6)
    def test_statistical_rmse(self):
        s=summarize(read_contrasts(self.p))
        self.assertAlmostEqual(s["rmse"],.1,places=12)
    def test_bootstrap_runs(self):
        out=evaluate(self.p,reps=100,seed=42)
        self.assertEqual(out["study_count"],3)
        self.assertEqual(out["bootstrap"]["repetitions_requested"],100)
    def test_study_holdout_calibration(self):
        rows=read_contrasts(self.p)
        by_study={s:[r for r in rows if r["study"]==s] for s in ("S1","S2","S3")}
        out=study_heldout_calibration(by_study)
        self.assertEqual(out["n_heldout_studies"],3)
        self.assertEqual(out["studies_improved"]+out["studies_harmed"],3)
        self.assertTrue(out["micro_rmse_raw"]>0)

    def test_bad_mirror_detected(self):
        rows=read_contrasts(self.p)
        rows[1]["human"]=-.8
        with self.assertRaisesRegex(ValueError,"Inconsistent"):
            mirror_coverage(rows)
    def test_constant_input(self):
        rows=[{"human":1,"prediction":2} for _ in range(4)]
        with self.assertRaisesRegex(ValueError,"constant"):
            summarize(rows)
    def test_percentile_endpoints(self):
        self.assertEqual(percentile([1,2,3],0),1)
        self.assertEqual(percentile([1,2,3],1),3)
        self.assertEqual(percentile([1,2,3],.5),2)
    def test_missing_header(self):
        self.p.write_text("x,y\\n1,2\\n")
        with self.assertRaisesRegex(ValueError,"columns"):
            read_contrasts(self.p)

if __name__=="__main__":
    unittest.main()
