import unittest
from paired_binary import compare_binary

class MatchedBinaryTests(unittest.TestCase):
    def test_counts_and_strict_denominator(self):
        r=compare_binary(["a","b","c","d"],{"a":"correct","b":"incorrect","c":"correct","d":"invalid"},{"a":"correct","b":"correct","c":"abstain","d":"invalid"})
        self.assertEqual((r["both_correct"],r["improved"],r["regressed"],r["both_not_correct"]),(1,1,1,1))
        self.assertEqual(r["candidate"]["strict_accuracy"],.5)
        self.assertEqual(r["candidate"]["invalid"],1)
        self.assertEqual(r["candidate"]["abstain"],1)
        self.assertEqual(r["mcnemar_exact_two_sided_unadjusted"],1)
    def test_missing_extra_and_duplicate(self):
        for ids,base,cand in [(["a"],{},{"a":"correct"}),(["a"],{"a":"correct"},{"a":"correct","b":"correct"}),(["a","a"],{"a":"correct"},{"a":"correct"}),([],{}, {})]:
            with self.subTest(ids=ids),self.assertRaises(ValueError): compare_binary(ids,base,cand)
    def test_reject_unknown_status(self):
        for v in (None,True,"missing","CORRECT"):
            with self.subTest(v=v),self.assertRaises(ValueError): compare_binary(["a"],{"a":"correct"},{"a":v})
    def test_exact_known(self):
        ids=list("abcdef")
        r=compare_binary(ids,dict.fromkeys(ids,"incorrect"),dict.fromkeys(ids,"correct"))
        self.assertEqual(r["mcnemar_exact_two_sided_unadjusted"],.03125)
        self.assertEqual(r["delta_strict_accuracy"],1)
    def test_no_discordance(self):
        r=compare_binary(["a"],{"a":"correct"},{"a":"correct"})
        self.assertEqual(r["mcnemar_exact_two_sided_unadjusted"],1)

    def test_matched_metadata(self):
        from paired_binary import compare_matched_runs
        c={"dataset_revision":"revision1","split":"test","case_manifest_sha256":"a"*64,
           "evaluator_revision":"revision2","prompt_sha256":"b"*64,"inference_protocol_sha256":"c"*64}
        a={"condition":c,"model_id":"base","outcomes":{"a":"incorrect"}}
        b={"condition":dict(c),"model_id":"candidate","outcomes":{"a":"correct"}}
        self.assertEqual(compare_matched_runs(["a"],a,b)["delta_strict_accuracy"],1)
        b["condition"]["inference_protocol_sha256"]="d"*64
        with self.assertRaisesRegex(ValueError,"condition mismatch"): compare_matched_runs(["a"],a,b)
        b["condition"]["prompt_sha256"]=None
        with self.assertRaisesRegex(ValueError,"value missing"): compare_matched_runs(["a"],a,b)
        b["condition"].pop("prompt_sha256")
        with self.assertRaisesRegex(ValueError,"fields incomplete"): compare_matched_runs(["a"],a,b)
