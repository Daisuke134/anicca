import unittest,tempfile
from pathlib import Path
import asyncio,httpx
class TestClient:
    def __init__(self,app):self.app=app
    def request(self,method,url,**kwargs):
        async def send():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url="http://test") as c:return await c.request(method,url,**kwargs)
        return asyncio.run(send())
    def post(self,url,**kw):return self.request("POST",url,**kw)
    def get(self,url,**kw):return self.request("GET",url,**kw)
from .research_router import Backend,ResearchRouter,SCOPE
from .http_api import create_app
def b(name,port):return Backend(name,f"http://127.0.0.1:{port}/v1/chat/completions","test")
class Tests(unittest.TestCase):
    def test_remote_forbidden(self):
        for url in ["https://example.com/v1/chat/completions","http://127.0.0.1:80/other","http://127.0.0.1:80/v1/chat/completions?x=1"]:
            with self.assertRaises(ValueError):Backend("a",url,"m")
    def test_fallback(self):
        def call(backend,prompt,timeout):
            if backend.name=="a":raise OSError("offline")
            return "42"
        r=ResearchRouter([b("a",1),b("b",2)],call).generate("arith",SCOPE)
        self.assertEqual(r["backend"],"b");self.assertEqual(len(r["attempts"]),2);self.assertFalse(r["production_eligible"])
    def test_no_fallback_on_output(self):
        r=ResearchRouter([b("a",1),b("b",2)],lambda *_:"wrong").generate("arith",SCOPE)
        self.assertEqual(len(r["attempts"]),1);self.assertEqual(r["status"],"output_requires_evaluation")
    def test_http(self):
        with tempfile.TemporaryDirectory() as d:
            app=create_app(Path(d)/"cases.db",b"x"*32,"synthetic-test",research_router=ResearchRouter([b("a",1)],lambda *_:"42"))
            c=TestClient(app);h={"Authorization":"Bearer synthetic-test","x-manager-subject":"synthetic"}
            url="/manager/research/generate";p={"case_id":"arith","scope":SCOPE}
            self.assertEqual(c.post(url,json=p).status_code,401)
            self.assertEqual(c.post(url,json={**p,"prompt":"private"},headers=h).status_code,422)
            self.assertEqual(c.post(url,json={**p,"scope":"mobile"},headers=h).status_code,403)
            self.assertEqual(c.post(url,json=p,headers=h).json()["text"],"42")
            self.assertEqual(c.get("/manager/health",headers=h).json()["default_backend"],"prior")
    def test_default_route_absent(self):
        with tempfile.TemporaryDirectory() as d:
            app=create_app(Path(d)/"cases.db",b"x"*32,"synthetic-test")
            self.assertEqual(TestClient(app).post("/manager/research/generate",json={}).status_code,404)
