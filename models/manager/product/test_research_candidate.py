import unittest
from pathlib import Path
from research_candidate import load_candidate,predict,mobile_preflight,SCOPE

class ResearchCandidateTests(unittest.TestCase):
    path=Path(__file__).parent/"research_candidate40.json"
    def setUp(self):
        self.model=load_candidate(self.path)
        self.context={"Month":"Nov","VisitorType":"Returning_Visitor","Weekend":"TRUE","SpecialDay":0}
    def test_probability(self):
        self.assertTrue(0<predict(self.model,self.context,scope=SCOPE)<1)
    def test_scope(self):
        with self.assertRaises(PermissionError):predict(self.model,self.context,scope="anicca_mobile")
        self.assertEqual(mobile_preflight(self.path)["status"],"BLOCKED_OUT_OF_SCOPE")
        self.assertFalse(mobile_preflight(self.path)["release_approved"])
    def test_unknown(self):
        with self.assertRaises(ValueError):predict(self.model,dict(self.context,Month="unknown"),scope=SCOPE)
    def test_bad_numeric(self):
        with self.assertRaises(ValueError):predict(self.model,dict(self.context,SpecialDay=float("nan")),scope=SCOPE)
