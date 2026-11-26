import unittest, math
from history_eval import score
def fixture():
 return [dict(participant=i,case_id=j,mode=m,p_gold=p)
         for i in range(2) for j in range(2)
         for m,p in [('own',.8),('other',.5),('none',.4)]]
class HistoryTests(unittest.TestCase):
 def test_paired(self):
  r=score(fixture());self.assertEqual(r['n_cases'],4);self.assertEqual(r['n_participants'],2)
  self.assertAlmostEqual(r['conditional_nll']['own'],-math.log(.8))
  self.assertAlmostEqual(r['own_minus']['other']['delta'],math.log(.5/.8))
 def test_missing(self):
  with self.assertRaises(ValueError):score(fixture()[:-1])
 def test_duplicate(self):
  a=fixture()
  with self.assertRaises(ValueError):score(a+[a[0]])
 def test_bad_probability(self):
  for p in [0,-.5,1.1,float('nan'),True]:
   a=fixture();a[0]['p_gold']=p
   with self.assertRaises(ValueError):score(a)
 def test_single_cluster(self):
  with self.assertRaises(ValueError):score([r for r in fixture() if r['participant']==0])
 def test_unequal_cluster_sizes(self):
  a=fixture();a.extend(dict(participant=0,case_id=2,mode=m,p_gold=p) for m,p in [('own',.1),('other',.5),('none',.5)])
  r=score(a);self.assertEqual(r['n_cases'],5)
  self.assertAlmostEqual(r['own_minus']['other']['delta'],(4*math.log(.5/.8)+math.log(.5/.1))/5)
if __name__=='__main__':unittest.main()
