"""Bounded loopback-only research API. Never routes actual intervention requests."""
from dataclasses import dataclass
import json
import time
import urllib.request
from urllib.parse import urlsplit

CASES = {
    "arith": "Return only the integer: 17 + 25.",
    "history": "A person meditated on Monday and Tuesday but not Wednesday. How many days did they meditate? Return only the integer.",
    "format": "Return only the word CALM in uppercase.",
}
SCOPE = "synthetic_runtime_research"

@dataclass(frozen=True)
class Backend:
    name: str
    endpoint: str
    model: str
    def __post_init__(self):
        u = urlsplit(self.endpoint)
        if u.scheme != "http" or u.hostname != "127.0.0.1" or not u.port or u.username or u.password or u.query or u.fragment or u.path != "/v1/chat/completions":
            raise ValueError("only explicit loopback research endpoint supported")
        if not self.name or not self.model:
            raise ValueError("identity required")

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise OSError("redirect forbidden")

def call(backend, prompt, timeout):
    req = urllib.request.Request(backend.endpoint,data=json.dumps({"model":backend.model,"messages":[{"role":"user","content":prompt}],"temperature":0,"max_tokens":24,"stream":False}).encode(),headers={"Content-Type":"application/json"},method="POST")
    # Ignore inherited proxy environment for local-only route.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    with opener.open(req,timeout=timeout) as response:
        raw=response.read(65537)
    if len(raw)>65536:raise ValueError("response too large")
    obj=json.loads(raw)
    if obj.get("model") != backend.model:raise ValueError("returned model mismatch")
    c=obj["choices"][0]
    if c.get("finish_reason")!="stop":raise ValueError("incomplete answer")
    text=c["message"]["content"]
    if not isinstance(text,str) or not text.strip() or text.startswith("⚠"):raise ValueError("invalid output")
    return text

class ResearchRouter:
    def __init__(self,backends,invoke=call,timeout=5):
        self.backends=tuple(backends)
        if not 1<=len(self.backends)<=2 or len({b.name for b in self.backends})!=len(self.backends) or not 0<timeout<=10:
            raise ValueError("bounded routes required")
        self.invoke=invoke
        self.timeout=timeout
    def generate(self,case_id,scope):
        if scope!=SCOPE:raise PermissionError("research scope only")
        if case_id not in CASES:raise ValueError("unknown case")
        attempts=[]
        for b in self.backends:
            t=time.monotonic()
            try:
                answer=self.invoke(b,CASES[case_id],self.timeout)
                if not isinstance(answer,str) or not answer.strip():raise ValueError("invalid output")
            except (OSError,ValueError,KeyError,TypeError,IndexError) as e:
                attempts.append({"backend":b.name,"model":b.model,"status":"unavailable_or_invalid","error_type":type(e).__name__,"seconds":time.monotonic()-t})
                continue
            attempts.append({"backend":b.name,"model":b.model,"status":"output","seconds":time.monotonic()-t})
            return {"status":"output_requires_evaluation","text":answer,"backend":b.name,"model":b.model,"attempts":attempts,"production_eligible":False}
        return {"status":"unavailable","attempts":attempts,"production_eligible":False}
