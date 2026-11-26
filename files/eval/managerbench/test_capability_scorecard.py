import hashlib,tempfile,unittest
from pathlib import Path
from capability_scorecard import build_scorecard,pinned,probability,gemma_track,anomaly_track

class CapabilityScorecardTests(unittest.TestCase):
    def test_missing_not_zero(self):
        r=build_scorecard({'rows':[{'family':'humor'}],'incomplete':[{}]})
        self.assertIsNone(r['global_score'])
        self.assertIsNone(r['global_rank'])
        self.assertFalse(r['promotion_eligible'])
        self.assertEqual(r['tracks']['gemma_pilot']['status'],'UNMEASURED_IN_THIS_VIEW')
        self.assertEqual(r['replay_family_row_counts'],{'humor':1})
        self.assertEqual(r['historical_incomplete_arms'],1)
    def test_digest(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.json';p.write_bytes(b'{}')
            self.assertEqual(pinned(p,hashlib.sha256(b'{}').hexdigest()),{})
            with self.assertRaisesRegex(ValueError,'digest'):pinned(p,'0'*64)
    def test_invalid_metric(self):
        for v in (None,True,float('nan'),float('inf'),-0.1,1.1):
            with self.subTest(v=v),self.assertRaises(ValueError):probability(v)
    def test_gemma_bad_frame(self):
        with self.assertRaises(ValueError):gemma_track({'bfm02_rows':[],'bfm02':{},'hillstrom':{'n':1000}})
    def test_anomaly_bad_frame(self):
        with self.assertRaises(ValueError):anomaly_track(dict(train=1,calibration=2048,normal=2048,authorized_change=2048,synthetic_deviation=1024))
