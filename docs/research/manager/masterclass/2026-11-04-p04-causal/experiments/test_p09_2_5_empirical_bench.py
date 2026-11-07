"""No-network synthetic software regression tests for P09-2 through P09-5.

These tests confirm split/estimator behavior. They are NOT human-performance tests.
"""
import tempfile
import unittest
import csv
import numpy as np
from pathlib import Path
from p09_2_5_empirical_bench import (
    fit_line, predict_line, rmse, mae, fewshot, split_studies,
    ood_calibration, text_features, feature_matrix, ridge_fit,
    transfer_experiment
)


class TestP09(unittest.TestCase):
    @staticmethod
    def synthetic_studies(n=70, each=10):
        out={}
        groups={}
        for i in range(n):
            name=f"testStudy{i:03}"
            x=np.linspace(-.2,.25,each)
            y=.03 + .5*x + (i%5)*.003
            out[name]=np.column_stack((x,y))
            groups[name]="published" if i<40 else "unpublished"
        return out,groups

    def test_study_balanced_fit(self):
        data,_=self.synthetic_studies(4,10)
        beta=fit_line(data,sorted(data))
        self.assertTrue(.4<beta[1]<.6)
        self.assertTrue(.02<beta[0]<.05)

    def test_rmse_mae(self):
        self.assertAlmostEqual(rmse([1,2],[1,3]),2**-.5)
        self.assertAlmostEqual(mae([1,2],[1,3]),.5)

    def test_no_cross_study_calibration_access(self):
        data,_=self.synthetic_studies(6,10)
        others=[s for s in data if s!="testStudy005"]
        beta=fit_line(data,others)
        changed={k:v.copy() for k,v in data.items()}
        changed["testStudy005"][:,1]+=1000
        np.testing.assert_allclose(beta,fit_line(changed,others))

    def test_fewshot_levels_and_exclusions(self):
        data,_=self.synthetic_studies(5,10)
        data["too_short"]=data["testStudy000"][:4].copy()
        out=fewshot(data,repetitions=2)
        self.assertEqual(out["eligible_studies"],5)
        self.assertEqual(out["excluded_small_studies"],1)
        self.assertIn("partial_pool_k5",out["results"])
        self.assertTrue(out["paired_study_uncertainty"]["exploratory"])

    def test_published_unpublished_group_split(self):
        data,groups=self.synthetic_studies(70,10)
        tr,cal,holdout,other=split_studies(data,groups)
        self.assertEqual([len(tr),len(cal),len(holdout),len(other)],[24,8,8,30])
        self.assertEqual(len(set(tr+cal+holdout+other)),70)
        self.assertTrue(all(groups[s]=="unpublished" for s in other))

    def test_calibration_does_not_peek_at_unpublished_labels(self):
        data,groups=self.synthetic_studies(70,10)
        baseline=ood_calibration(data,groups)
        changed={key:value.copy() for key,value in data.items()}
        for key,group in groups.items():
            if group=="unpublished":
                changed[key][:,1]+=100
        updated=ood_calibration(changed,groups)
        self.assertAlmostEqual(baseline["q90_calibration_error"],updated["q90_calibration_error"])
        self.assertAlmostEqual(baseline["ood_abs_effect_cutoff"],updated["ood_abs_effect_cutoff"])
        self.assertNotEqual(baseline["unpublished_group"]["rmse"],updated["unpublished_group"]["rmse"])

    def test_char_hash_features_deterministic(self):
        a=text_features("今日はとても面白い")
        b=text_features("今日はとても面白い")
        self.assertEqual(a.shape,(24,))
        np.testing.assert_array_equal(a,b)
        self.assertAlmostEqual(float(np.linalg.norm(a)),1.)

    def test_feature_matrix_uses_description_not_manga_dialogue(self):
        text={0:"こんにちは",1:"どうも"}
        descriptions={i:"二人が話す短い漫画の場面" for i in range(400)}
        x=feature_matrix([0,1],text,descriptions)
        self.assertEqual(x.shape,(800,28))
        self.assertTrue(np.isfinite(x).all())

    def test_regularized_solver(self):
        x=np.array([[1.,0.],[1.,1.],[1.,2.]])
        y=np.array([0.,1.,2.])
        beta=ridge_fit(x,y,0.001)
        self.assertTrue(np.isfinite(beta).all())
        self.assertTrue(rmse(y,x@beta)<.01)

    def test_one_scalar_negative_transfer_not_bfm(self):
        data,groups=self.synthetic_studies(70,10)
        train=np.ones((4,400))*.2
        target=np.ones((3,400))*.2
        fake={"task_data":{"train_scores":train,
            "train_img_leave_one_context_avg":np.ones((4,400))*.21+np.arange(400)[None,:]*1e-5,
            "train_ids":np.arange(4),
            "test_scores":target,
            "test_base":np.ones(3*400)*.21,
            "center_mean":.2}}
        out=transfer_experiment(data,groups,fake)
        self.assertIn("NOT unified BFM",out["model_class"])
        self.assertIn("after_equal_task_replay",out)

if __name__=="__main__":
    unittest.main()