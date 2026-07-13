#!/usr/bin/env python3
"""Post a tweet to X via API v2 (OAuth 1.0a user context). No browser, no collision.
Reads X creds from env (X_API_KEY/X_API_SECRET/X_ACCESS_TOKEN/X_ACCESS_SECRET).
Usage:
  python3 post_x.py --whoami
  python3 post_x.py --text "..."            # post text
  python3 post_x.py --text "..." --media /path.png[,/p2.png]   # with image(s)
"""
import os, sys, time, hmac, hashlib, base64, secrets, urllib.parse, json, urllib.request

CK=os.environ["X_API_KEY"]; CS=os.environ["X_API_SECRET"]
AT=os.environ["X_ACCESS_TOKEN"]; ATS=os.environ["X_ACCESS_SECRET"]

def _sign(method,url,params):
    base_params={**params,"oauth_consumer_key":CK,"oauth_nonce":secrets.token_hex(16),
        "oauth_signature_method":"HMAC-SHA1","oauth_timestamp":str(int(time.time())),
        "oauth_token":AT,"oauth_version":"1.0"}
    enc=lambda s: urllib.parse.quote(str(s),safe="~")
    pstr="&".join(f"{enc(k)}={enc(base_params[k])}" for k in sorted(base_params))
    base="&".join([method,enc(url),enc(pstr)])
    key=f"{enc(CS)}&{enc(ATS)}"
    sig=base64.b64encode(hmac.new(key.encode(),base.encode(),hashlib.sha1).digest()).decode()
    base_params["oauth_signature"]=sig
    header="OAuth "+", ".join(f'{enc(k)}="{enc(v)}"' for k,v in base_params.items() if k.startswith("oauth_"))
    return header

def _req(method,url,headers=None,data=None):
    req=urllib.request.Request(url,data=data,method=method,headers=headers or {})
    try:
        with urllib.request.urlopen(req,timeout=30) as r: return r.status, r.read().decode()
    except urllib.error.HTTPError as e: return e.code, e.read().decode()

def whoami():
    url="https://api.twitter.com/2/users/me"
    h={"Authorization":_sign("GET",url,{})}
    return _req("GET",url,h)

def upload_media(path):
    # v1.1 media upload (simple, <5MB images)
    url="https://upload.twitter.com/1.1/media/upload.json"
    raw=open(path,"rb").read()
    b64=base64.b64encode(raw).decode()
    body=urllib.parse.urlencode({"media_data":b64}).encode()
    # for body params in oauth sig, x-www-form-urlencoded params ARE signed
    params={"media_data":b64}
    h={"Authorization":_sign("POST",url,params),"Content-Type":"application/x-www-form-urlencoded"}
    st,resp=_req("POST",url,h,body)
    if st in (200,201): return json.loads(resp).get("media_id_string")
    raise RuntimeError(f"media upload failed {st}: {resp[:200]}")

def post(text, media_paths=None):
    url="https://api.twitter.com/2/tweets"
    payload={"text":text}
    if media_paths:
        ids=[upload_media(p) for p in media_paths if p]
        if ids: payload["media"]={"media_ids":ids}
    body=json.dumps(payload).encode()
    h={"Authorization":_sign("POST",url,{}),"Content-Type":"application/json"}
    return _req("POST",url,h,body)

if __name__=="__main__":
    a=sys.argv[1:]
    if "--whoami" in a:
        st,resp=whoami(); print(st,resp); sys.exit(0 if st==200 else 1)
    def g(f):
        return a[a.index(f)+1] if f in a else None
    text=g("--text")
    if not text: print("ERROR: --text required"); sys.exit(2)
    media=g("--media")
    paths=[p for p in (media.split(",") if media else [])]
    st,resp=post(text,paths)
    print(st,resp)
    sys.exit(0 if st in (200,201) else 1)
