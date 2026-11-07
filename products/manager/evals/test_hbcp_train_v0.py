"""G2 real trained study-arm head: software-only fixtures guarding source leakage."""
import copy
import json
import unittest
import numpy as np
from hbcp_train_v0 import frozen_study_split, fit_model, predict_artifact, train_artifact

def fixture():
    groups=[f"study-{i//3:03}" for i in range(60)]
    X=np.asarray([[i%7, np.nan if i%4==0 else float(i%5), 1+(i%3)] for i in range(60)],dtype=float)
    y=np.asarray([10 + (i%7)*2 + (i%3) + (i%5)*.1 for i in range(60)],dtype=float)
    return X,y,groups,["freq","indicator","batch"]

class G2TrainingTests(unittest.TestCase):
    def test_study_split_excludes_every_heldout_group(self):
        _,_,groups,_=fixture()
        tr,cal,te=frozen_study_split(groups,seed=20261107)
        self.assertEqual(len(tr)+len(cal)+len(te),len(groups))
        self.assertEqual(len(set(tr)|set(cal)|set(te)),len(groups))
        def studies(indices):return {groups[i] for i in indices}
        self.assertFalse(studies(tr)&studies(te))
        self.assertFalse(studies(tr)&studies(cal))
        self.assertFalse(studies(cal)&studies(te))

    def test_artifact_serializes_and_predicts_identically(self):
        X,y,groups,columns=fixture()
        tr,ca,te=frozen_study_split(groups)
        model=fit_model(X,y,columns,tr,ca,te)
        loaded=json.loads(json.dumps(model))
        a=predict_artifact(model,X[te],columns)
        b=predict_artifact(loaded,X[te],columns)
        np.testing.assert_allclose(a,b)
        self.assertGreaterEqual(float(a.min()),0)
        self.assertLessEqual(float(a.max()),100)
        self.assertFalse(model["trained_universal_bfm"])

    def test_test_labels_are_not_used_to_fit_or_calibrate(self):
        X,y,groups,cols=fixture()
        tr,ca,te=frozen_study_split(groups)
        model=fit_model(X,y,cols,tr,ca,te)
        altered=y.copy();altered[te]=90
        other=fit_model(X,altered,cols,tr,ca,te)
        self.assertEqual(model["head"],other["head"])
        self.assertEqual(model["preprocessing"],other["preprocessing"])
        self.assertEqual(model["calibration_halfwidth"],other["calibration_halfwidth"])
        self.assertNotEqual(model["test_metrics"]["ridge"]["mae"],other["test_metrics"]["ridge"]["mae"])

    def test_calibration_labels_never_train_weights(self):
        X,y,groups,cols=fixture()
        tr,ca,te=frozen_study_split(groups)
        original=fit_model(X,y,cols,tr,ca,te)
        changed=y.copy();changed[ca]=60
        another=fit_model(X,changed,cols,tr,ca,te)
        self.assertEqual(original["head"],another["head"])
        self.assertNotEqual(original["calibration_halfwidth"],another["calibration_halfwidth"])

    def test_reloaded_artifact_rejects_tampered_head_and_missing_digest(self):
        X,y,groups,columns=fixture()
        tr,ca,te=frozen_study_split(groups)
        trained=fit_model(X,y,columns,tr,ca,te)
        bad=json.loads(json.dumps(trained))
        bad["head"]["weights"][0]+=1
        with self.assertRaises(ValueError):
            predict_artifact(bad,X[te],columns)
        missing=json.loads(json.dumps(trained))
        missing.pop("trained_head_sha256")
        with self.assertRaises(ValueError):
            predict_artifact(missing,X[te],columns)

    def test_schema_wrong_features_and_nonfinite_outcome_rejected(self):
        X,y,groups,cols=fixture()
        tr,ca,te=frozen_study_split(groups)
        model=fit_model(X,y,cols,tr,ca,te)
        with self.assertRaises(ValueError):
            predict_artifact(model,X[te],list(reversed(cols)))
        with self.assertRaises(ValueError):
            predict_artifact(model,X[te,:2],cols)
        bad=y.copy();bad[0]=float("nan")
        with self.assertRaises(ValueError):
            fit_model(X,bad,cols,tr,ca,te)

    def test_legitimate_feedback_on_outcomes_technique_is_not_target_leakage(self):
        X,y,groups,cols=fixture()
        cols[1]="(6452761, '2.7 Feedback on outcome(s) of behavior')"
        tr,ca,te=frozen_study_split(groups)
        model=fit_model(X,y,cols,tr,ca,te)
        self.assertEqual(model["n_features"],3)
        self.assertIn("Feedback on outcome(s) of behavior",model["preprocessing"]["columns"][1])

    def test_duplicate_features_or_overlap_rejected(self):
        X,y,groups,cols=fixture()
        tr,ca,te=frozen_study_split(groups)
        with self.assertRaises(ValueError):
            fit_model(X,y,["same"]*3,tr,ca,te)
        with self.assertRaises(ValueError):
            fit_model(X,y,cols,tr,np.r_[ca,tr[:1]],te)

    def test_no_personal_intervention_or_user_model_claim(self):
        X,y,groups,cols=fixture()
        tr,ca,te=frozen_study_split(groups)
        model=fit_model(X,y,cols,tr,ca,te)
        self.assertEqual(model["domain"],"HBCP_PUBLISHED_SMOKING_CESSATION_RCT_ARMS")
        self.assertFalse(model["individual_user_predictions_authorized"])
        self.assertFalse(model["trained_universal_bfm"])
        self.assertNotIn("participant_id",json.dumps(model))

if __name__=="__main__":
    unittest.main()
