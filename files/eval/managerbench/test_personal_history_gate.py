import unittest
from personal_history_gate import screen
class Tests(unittest.TestCase):
    def fixture(self):
        return {"test_n":42,"paired":{f"own_{s}-{m}_{s}":{"delta":-.01,"ci95":[-.02,-.001]} for s in (42,43,44) for m in ("none","other")}}
    def test_clear(self):
        r=screen(self.fixture());self.assertTrue(r["screen_pass"]);self.assertFalse(r["production_eligible"])
    def test_zero(self):
        x=self.fixture();x["paired"]["own_42-none_42"]["ci95"]=[-.02,0];self.assertFalse(screen(x)["screen_pass"])
    def test_missing(self):
        x=self.fixture();del x["paired"]["own_42-other_42"];self.assertFalse(screen(x)["screen_pass"])
    def test_nan(self):
        x=self.fixture();x["paired"]["own_43-none_43"]["delta"]=float("nan");self.assertFalse(screen(x)["screen_pass"])
    def test_bool(self):
        x=self.fixture();x["test_n"]=True;self.assertFalse(screen(x)["screen_pass"])
