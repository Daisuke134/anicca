"""Synthetic software regression tests for HBCP study-disjoint baseline."""
import unittest
import numpy as np
from hbcp_study_disjoint_lightweight import (
    study_folds, numeric_feature_matrix, ridge_on_train, evaluate_predictions,
)


class HBCPStudyHoldoutTests(unittest.TestCase):
    def test_group_folds_are_disjoint_and_cover_all_rows(self):
        groups=[f"study{i//3}" for i in range(45)]
        folds=study_folds(groups,n_splits=5)
        seen=[]
        for tr,te in folds:
            self.assertFalse(set(groups[i] for i in tr)&set(groups[i] for i in te))
            seen.extend(te)
        self.assertEqual(sorted(seen),list(range(45)))

    def test_extract_only_numeric_inputs_without_outcome_or_identifiers(self):
        rows=[
            {"doc":"a","arm":"x","doc_id":"9","arm_id":"3",
             "('Outcome', 'Outcome')":"12.3","good":"3.2","text":"hello"},
            {"doc":"b","arm":"y","doc_id":"8","arm_id":"4",
             "('Outcome', 'Outcome')":"4.3","good":"1.7","text":"world"}
        ]
        X, columns=numeric_feature_matrix(rows)
        self.assertEqual(X.shape,(2,1))
        self.assertEqual(columns,["good"])
        np.testing.assert_array_equal(X[:,0],[3.2,1.7])

    def test_ridge_uses_train_only_for_imputation(self):
        X=np.array([[1.,float('nan')],[2.,2.],[3.,float('nan')],[99999.,99999.]])
        y=np.array([1.,2.,3.,99.])
        p=ridge_on_train(X,y,np.array([0,1,2]),np.array([3]),alpha=30.)
        changed=X.copy()
        changed[3,:]=[-99999.,-99999.]
        other=ridge_on_train(changed,y,np.array([0,1,2]),np.array([3]),alpha=30.)
        self.assertTrue(np.isfinite(p).all())
        self.assertEqual(len(p),1)
        self.assertNotAlmostEqual(p[0],other[0])

    def test_no_leakage_of_test_target(self):
        X=np.array([[1.,2.],[2.,2.],[4.,5.],[3.,8.]])
        y=np.array([1.,2.,3.,4.])
        p=ridge_on_train(X,y,np.array([0,1,2]),np.array([3]),alpha=30.)
        y[-1]=1_000
        q=ridge_on_train(X,y,np.array([0,1,2]),np.array([3]),alpha=30.)
        np.testing.assert_allclose(p,q)

    def test_mae_rmse(self):
        metrics=evaluate_predictions(np.array([0.,2.]),np.array([1.,4.]))
        self.assertAlmostEqual(metrics["mae"],1.5)
        self.assertAlmostEqual(metrics["rmse"],np.sqrt(2.5))

if __name__=="__main__":
    unittest.main()
