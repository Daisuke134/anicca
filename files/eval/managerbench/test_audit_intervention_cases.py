"""TDD tests for additive, read-only intervention decision consistency audit.
Only fictional test rows. No user outcomes or causal effects estimated.
"""
import json
import tempfile
import unittest
from pathlib import Path
from audit_intervention_cases import AuditError, validate_case, audit_cases, audit_paths, main

def toy(**kw):
    x={"case_id":"toy-1","person_id":"toy-p","decision_point_at":"2026-11-14T10:00:00Z",
       "available":True,"personal_history":{"prior_response":0},
       "treatment_assigned":True,"assigned_probability":.5,"intervention_id":"toy-nudge",
       "delivery_id":"toy-delivery","proximal_outcome":1,"outcome_window_sec":3600,
       "outcome_observed":True,"outcome_observed_at":"2026-11-14T20:05:00+09:00"}
    x.update(kw)
    return x

class CaseContract(unittest.TestCase):
    def test_valid_treated(self):
        self.assertIsNone(validate_case(toy()))
    def test_valid_control(self):
        self.assertIsNone(validate_case(toy(treatment_assigned=False,intervention_id=None,
                                            delivery_id=None,proximal_outcome=False)))
    def test_unavailable_control_not_randomized(self):
        x=toy(available=False,treatment_assigned=False,intervention_id=None,
              delivery_id=None,proximal_outcome=None,outcome_observed=False,
              outcome_observed_at=None)
        d=audit_cases([x])
        self.assertEqual((d["unavailable_decisions"],d["available_randomized_decisions"]),(1,0))
    def test_unobserved_must_have_null_outcome(self):
        with self.assertRaisesRegex(AuditError,"unobserved.*null"):
            validate_case(toy(outcome_observed=False,proximal_outcome=1))
    def test_observed_requires_outcome(self):
        with self.assertRaisesRegex(AuditError,"observed.*non-null"):
            validate_case(toy(proximal_outcome=None))
    def test_observed_flag_required_in_strict_audit(self):
        d=toy(); del d["outcome_observed"]
        with self.assertRaisesRegex(AuditError,"outcome_observed"):validate_case(d)
    def test_boolean_flags_enforced(self):
        for k,v in [("available",1),("treatment_assigned","true"),("outcome_observed",1)]:
            with self.subTest(k=k),self.assertRaisesRegex(AuditError,k):
                validate_case(toy(**{k:v}))
    def test_unavailable_cannot_be_treated(self):
        with self.assertRaisesRegex(AuditError,"unavailable.*treatment"):
            validate_case(toy(available=False))
    def test_treated_requires_valid_intervention_and_delivery(self):
        for k,v in [("intervention_id",None),("delivery_id",None),("delivery_id","  ")]:
            with self.subTest(k=k),self.assertRaisesRegex(AuditError,k):
                validate_case(toy(**{k:v}))
    def test_required_history_and_fields(self):
        d=toy();del d["personal_history"]
        with self.assertRaisesRegex(AuditError,"missing required"):validate_case(d)
        with self.assertRaisesRegex(AuditError,"personal_history"):
            validate_case(toy(personal_history={}))
    def test_propensity_finite_and_inside_unit_interval(self):
        for p in (0,1,-.1,1.2,float("nan"),float("inf"),True,"0.5"):
            with self.subTest(p=p),self.assertRaisesRegex(AuditError,"assigned_probability"):
                validate_case(toy(assigned_probability=p))
    def test_outcome_finite_numeric_or_boolean(self):
        for y in (float("nan"),float("inf"),"yes",[],{}):
            with self.subTest(y=str(y)),self.assertRaisesRegex(AuditError,"proximal_outcome"):
                validate_case(toy(proximal_outcome=y))
    def test_window_positive_int_not_bool(self):
        for v in (0,-1,1.2,True,False,"60"):
            with self.subTest(v=v),self.assertRaisesRegex(AuditError,"outcome_window_sec"):
                validate_case(toy(outcome_window_sec=v))
    def test_ids_nonempty(self):
        for k in ("case_id","person_id"):
            for v in ("","  ",None,123):
                with self.subTest(k=k,v=v),self.assertRaisesRegex(AuditError,k):
                    validate_case(toy(**{k:v}))
    def test_decision_timestamp_tz_required(self):
        for v in ("2026-11-14T10:00:00","garbage",None):
            with self.subTest(v=v),self.assertRaisesRegex(AuditError,"decision_point_at"):
                validate_case(toy(decision_point_at=v))
    def test_optional_observed_timestamp_tz_required(self):
        with self.assertRaisesRegex(AuditError,"outcome_observed_at"):
            validate_case(toy(outcome_observed_at="2026-11-14T11:05:00"))
    def test_observation_timestamp_not_before_decision(self):
        with self.assertRaisesRegex(AuditError,"before decision"):
            validate_case(toy(outcome_observed_at="2026-11-14T09:59:00Z"))
    def test_late_observation_acceptable(self):
        self.assertIsNone(validate_case(toy(outcome_observed_at="2026-11-19T10:00:00Z")))
    def test_unobserved_timestamp_not_permitted(self):
        with self.assertRaisesRegex(AuditError,"unobserved.*timestamp"):
            validate_case(toy(outcome_observed=False,proximal_outcome=None))
    def test_absent_optional_observation_timestamp_allowed(self):
        d=toy();del d["outcome_observed_at"]
        self.assertIsNone(validate_case(d))

class AggregateContract(unittest.TestCase):
    def test_zero_is_zero_not_efficacy(self):
        d=audit_cases([])
        self.assertEqual((d["validated_decisions"],d["observed_outcomes"]),(0,0))
        self.assertFalse(d["causal_effect_estimated"])
        self.assertFalse(d["real_user_benefit_proven"])
    def test_observed_and_missing_counted(self):
        d=audit_cases([toy(),toy(case_id="toy-2",person_id="toy-p2",
                               outcome_observed=False,proximal_outcome=None,
                               outcome_observed_at=None)])
        self.assertEqual((d["validated_decisions"],d["observed_outcomes"],d["missing_outcomes"],
                          d["distinct_person_ids"]),(2,1,1,2))
    def test_duplicate_case_rejected(self):
        with self.assertRaisesRegex(AuditError,"duplicate case_id"):
            audit_cases([toy(),toy(person_id="toy-other")])
    def test_error_shows_index_no_person_id(self):
        with self.assertRaisesRegex(AuditError,"index 0"):
            audit_cases([toy(available="yes")])
    def test_evidence_level_explicit(self):
        d=audit_cases([toy()])
        self.assertEqual(d["evidence_level"],"SCHEMA_CONSISTENCY_ONLY_NOT_CAUSAL_EFFECT")
    def test_list_and_cases_object_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"rows.json"
            for content in ([toy()],{"cases":[toy()]}):
                f.write_text(json.dumps(content))
                self.assertEqual(audit_paths([f])["validated_decisions"],1)
    def test_nonintervention_manifest_rejected_not_silently_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"old.json";f.write_text('{"mode":"replay","rows":[]}')
            with self.assertRaisesRegex(AuditError,"cases.*list"):audit_paths([f])
    def test_zero_cases_list_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"empty.json";f.write_text("[]")
            self.assertEqual(audit_paths([f])["validated_decisions"],0)
    def test_no_file_paths_rejected(self):
        with self.assertRaisesRegex(AuditError,"at least one"):audit_paths([])
    def test_duplicate_case_across_files_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"a.json";g=Path(tmp)/"b.json"
            f.write_text(json.dumps([toy()]));g.write_text(json.dumps([toy()]))
            with self.assertRaisesRegex(AuditError,"duplicate case_id"):audit_paths([f,g])
    def test_invalid_json_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"broken.json";f.write_text("{")
            with self.assertRaisesRegex(AuditError,"invalid JSON"):audit_paths([f])
    def test_cli_minimum_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"empty.json";f.write_text("[]")
            code,r=main([str(f)],return_report=True)
            self.assertEqual((code,r["validated_decisions"]),(0,0))
            self.assertEqual(r["gate_status"],"PASS_ZERO_CASES")
            code,r=main([str(f),"--require-min","1"],return_report=True)
            self.assertEqual((code,r["gate_status"]),(1,"FAIL_UNDER_MINIMUM"))
    def test_nonzero_pass_is_consistency_only_not_human_impact(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"synthetic-one.json";f.write_text(json.dumps([toy()]))
            code,r=main([str(f)],return_report=True)
            self.assertEqual(code,0)
            self.assertEqual(r["gate_status"],"PASS_CONSISTENCY_ONLY")
            self.assertFalse(r["real_user_benefit_proven"])

    def test_missing_file_rejected(self):
        with self.assertRaisesRegex(AuditError,"cannot read"):
            audit_paths([Path("/definitely/not/here/fake.json")])

if __name__=="__main__":unittest.main()