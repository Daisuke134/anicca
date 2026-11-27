import hashlib,tempfile,unittest,subprocess,sys,json
from pathlib import Path
from capability_scorecard import build_scorecard,pinned,probability,gemma_track,anomaly_track,valid_count_audit,BEHAVIOR_SOURCE,BEHAVIOR_SHA

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

    def test_real_denominator_source(self):
        root=Path(__file__).resolve().parents[3]
        v=valid_count_audit(pinned(root/BEHAVIOR_SOURCE,BEHAVIOR_SHA))
        self.assertEqual(v['receipted_arms'],68)
        self.assertEqual(v['known_valid_count_arms'],48)
        self.assertEqual(v['unknown_valid_count_arms'],20)
        self.assertEqual(v['known_valid_predictions_sum'],33018)
        self.assertIsNone(v['all_valid_predictions'])
    def test_reject_inconsistent_denominator(self):
        root=Path(__file__).resolve().parents[3]
        d=pinned(root/BEHAVIOR_SOURCE,BEHAVIOR_SHA)
        r=next(v for v in d['results'].values() if (v.get('metadata') or {}).get('num_valid_predictions') is not None)
        r['metadata']['num_valid_predictions']=-1
        with self.assertRaisesRegex(ValueError,'inconsistent'):valid_count_audit(d)
    def test_cli_missing_receipt_fails_without_output(self):
        root=Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'replay.json';card=Path(d)/'card.json';bad=Path(d)/'bad.json';bad.write_text('{}')
            p=subprocess.run([sys.executable,str(Path(__file__).with_name('run.py')),'--root',str(root),'--output',str(out),'--capability-scorecard',str(card),'--gemma-receipt',str(bad)],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertIn('digest mismatch',p.stderr)
            self.assertFalse(out.exists())
            self.assertFalse(card.exists())
    def test_cli_alias_rejected(self):
        root=Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as d:
            pth=Path(d)/'same.json'
            p=subprocess.run([sys.executable,str(Path(__file__).with_name('run.py')),'--root',str(root),'--output',str(pth),'--capability-scorecard',str(pth)],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertIn('paths must be distinct',p.stderr)
            self.assertFalse(pth.exists())

    def test_cli_preflight_invalid_destination_preserves_outputs(self):
        root=Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d)
            out=tmp/'replay.json'
            out.write_text('existing sentinel')
            for card in (tmp/'missing'/'card.json',tmp):
                with self.subTest(card=card):
                    p=subprocess.run([sys.executable,str(Path(__file__).with_name('run.py')),'--root',str(root),'--output',str(out),'--capability-scorecard',str(card)],capture_output=True,text=True)
                    self.assertNotEqual(p.returncode,0)
                    self.assertIn('output destination must be a file in an existing directory',p.stderr)
                    self.assertEqual(out.read_text(),'existing sentinel')
            card=tmp/'card.json'
            p=subprocess.run([sys.executable,str(Path(__file__).with_name('run.py')),'--root',str(root),'--output',str(tmp/'missing'/'replay.json'),'--capability-scorecard',str(card)],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertIn('output destination must be a file in an existing directory',p.stderr)
            self.assertFalse(card.exists())
