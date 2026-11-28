import copy, unittest
from local_runtime_receipt import audit

class AuditTests(unittest.TestCase):
    def fixture(self):
        row={"case":"json","text":"{\"send\":false}","valid":True,"correct":True,"seconds":.01}
        return {"cases":[["json","p","{\"send\":false}"]],"results":{k:[copy.copy(row)] for k in ("magnitude","magnitude_warm","llama_cpp")}}
    def test_valid(self): self.assertFalse(audit(self.fixture())["promotion_eligible"])
    def test_boolean_strict(self):
        r=self.fixture();r["results"]["magnitude"][0]["text"]='{"send":0}'
        with self.assertRaises(ValueError):audit(r)
    def test_timeout_not_correct(self):
        r=self.fixture();r["results"]["magnitude"][0]={"case":"json","error":"timeout","valid":False,"correct":False}
        self.assertEqual(audit(r)["summary"]["magnitude"]["valid"],0)
    def test_missing(self):
        r=self.fixture();r["results"]["llama_cpp"]=[]
        with self.assertRaises(ValueError):audit(r)
