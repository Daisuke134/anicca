import unittest
import numpy as np
from ope_adapter import prepare, evaluate


def row(i, action='a', reward=1, target=None):
    return dict(id=str(i), candidates=[dict(id='a',kind='reflection',probability=.5),dict(id='n',kind='none',probability=.5)], chosen_id=action,pscore=.5,target=target or {'a':.75,'n':.25},reward=reward)


class TestOPE(unittest.TestCase):
    def test_projection_and_weights(self):
        d,m=prepare([row(1),row(2,'n',0)])
        self.assertEqual(d['action_dist'].shape,(2,2,1))
        self.assertAlmostEqual(m['ess'],1.6)
        np.testing.assert_array_equal(d['action'],[0,1])
        self.assertAlmostEqual(m['mean_weight'],1)
    def test_missing(self):
        r=evaluate([row(1),row(2,reward=None)])
        self.assertIsNone(r['ipw']); self.assertEqual(r['diagnostics']['missing'],1)
    def test_zero_support(self):
        r=row(1); r['candidates'][0]['probability']=1; r['candidates'][1]['probability']=0; r['pscore']=1
        with self.assertRaisesRegex(ValueError,'support'): prepare([r])
    def test_propensity_mismatch(self):
        r=row(1); r['pscore']=.4
        with self.assertRaisesRegex(ValueError,'propensity'): prepare([r])
    def test_duplicate(self):
        with self.assertRaisesRegex(ValueError,'duplicate'): prepare([row(1),row(1)])
    def test_zero_effective_sample(self):
        r=evaluate([row(1,'n',0,{'a':1,'n':0})]); self.assertEqual(r['status'],'UNMEASURED')
    def test_variable_candidate_counts(self):
        r=row(2); r['candidates'].append(dict(id='b',kind='reflection',probability=.2)); r['candidates'][0]['probability']=.3; r['pscore']=.3; r['target']={'a':.4,'b':.4,'n':.2}
        d,m=prepare([row(1),r]); self.assertEqual(d['action_dist'].shape,(2,3,1)); self.assertEqual(d['action_dist'][0,2,0],0)
    def test_invalid_distribution(self):
        r=row(1,target={'a':.8,'n':.8})
        with self.assertRaisesRegex(ValueError,'sum'): prepare([r])
    def test_official_obp_if_available(self):
        try: import obp.ope
        except ImportError: self.skipTest('OBP not installed')
        r=evaluate([row(1),row(2,'n',0)]); self.assertAlmostEqual(r['ipw'],.75); self.assertAlmostEqual(r['snipw'],.75)

if __name__=='__main__': unittest.main()
