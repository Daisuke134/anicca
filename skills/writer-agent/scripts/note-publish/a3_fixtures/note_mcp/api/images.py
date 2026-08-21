import os, json
class _Img:
    def __init__(self, url): self.url=url
async def upload_body_image(sess, path, num):
    # A3_FAIL_UPLOAD: comma-separated substrings; any path containing one raises instead of
    # recording+succeeding, so stage2's partial-embed-failure path can be exercised offline
    # (no real network call either way — this whole module is the fake note_mcp).
    fail_on = [s for s in os.environ.get('A3_FAIL_UPLOAD', '').split(',') if s]
    if any(s in path for s in fail_on):
        raise RuntimeError(f"fake upload failure injected for {path}")
    f=os.environ['A3_REC']; d=json.load(open(f)) if os.path.exists(f) else []
    d.append({'call':'upload','path':path,'num':num}); json.dump(d, open(f,'w')); return _Img('https://fake.example/img.png')
