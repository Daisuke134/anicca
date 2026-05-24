#!/usr/bin/env python3
"""
anicca peer agent-api — minimal HTTP for Anicca-to-Anicca comms.

Direct port of the CORE of sutando src/agent-api.py (read line-by-line):
file-backed task queue + poll/callback, token auth, SSRF-guarded callback.
Twilio/voice/web-UI parts of sutando are intentionally dropped — Anicca only
needs the peer contract the replication + peer-revive skills rely on.

Endpoints (the #20/#27 contract):
  GET  /ping          -> {"pong":true}                 alive check
  GET  /status        -> {tier, alive, mrr, beat, caps} health (peer-revive reads this)
  POST /task          -> {from,task,priority,callback_url} enqueue for the heartbeat loop
  GET  /result/<id>   -> {status, result}               poll

Queue: writes ops/peer-inbox/<id>.json; the heartbeat loop drains it into
ops/steps.json (priority urgent>normal>low, sutando task_priority). Result
written to ops/peer-results/<id>.json; callback POSTed if given.

Security: ANICCA_PEER_TOKEN in env -> Bearer required. Callback URL must be
https + public IP (SSRF guard, ported from sutando _is_safe_callback_url).
Bind 127.0.0.1 by default; ANICCA_PEER_BIND=0.0.0.0 for LAN/peer access.
"""
import http.server, ipaddress, json, os, re, socket, sys, time
from pathlib import Path
from urllib.parse import urlparse

WS = Path(os.environ.get("ANICCA_WORKSPACE", str(Path.home() / ".openclaw" / "workspace")))
INBOX = WS / "ops" / "peer-inbox"
RESULTS = WS / "ops" / "peer-results"
STATE = WS / "ops" / "heartbeat_state.json"
ALIVE = WS / "ops" / ".alive"
INBOX.mkdir(parents=True, exist_ok=True)
RESULTS.mkdir(parents=True, exist_ok=True)
PORT = int(os.environ.get("ANICCA_PEER_PORT", "7843"))
TOKEN = os.environ.get("ANICCA_PEER_TOKEN", "")

_PRIV = [ipaddress.ip_network(b) for b in (
    "127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
    "169.254.0.0/16", "0.0.0.0/8", "100.64.0.0/10", "::1/128", "fc00::/7", "fe80::/10")]


def _safe_id(raw: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-.]", "", raw)[:64]


def _safe_callback(url: str):
    """SSRF guard, ported from sutando _is_safe_callback_url: https only, no private IP."""
    try:
        p = urlparse(url)
    except Exception:
        return False
    if p.scheme != "https" or not p.hostname:
        return False
    try:
        infos = socket.getaddrinfo(p.hostname, None)
    except socket.gaierror:
        return False
    for *_x, sa in infos:
        try:
            ip = ipaddress.ip_address(sa[0])
            if any(ip in n for n in _PRIV):
                return False
        except ValueError:
            return False
    return True


def get_status() -> dict:
    st = {}
    try:
        st = json.loads(STATE.read_text())
    except Exception:
        pass
    return {
        "agent": "anicca",
        "alive": ALIVE.exists() and (time.time() - ALIVE.stat().st_mtime < 1800),
        "tier": st.get("tier", "unknown"),
        "p5h": st.get("p5h"), "weekly": st.get("weekly"),
        "lastBeat": st.get("cachedAt"),
        "capabilities": ["self-improve", "earn", "replicate", "peer-revive"],
        "endpoints": {"task": "POST /task", "status": "GET /status", "ping": "GET /ping"},
    }


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _j(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b)

    def _auth(self) -> bool:
        if not TOKEN:
            return True
        import hmac
        tok = self.headers.get("Authorization", "").replace("Bearer ", "")
        if hmac.compare_digest(tok, TOKEN):
            return True
        self._j(401, {"error": "unauthorized"})
        return False

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/ping":
            self._j(200, {"pong": True})
        elif path == "/status":
            self._j(200, get_status())
        elif path.startswith("/result/"):
            rid = _safe_id(path[len("/result/"):])
            rf = RESULTS / f"{rid}.json"
            if rf.exists():
                self._j(200, {"task_id": rid, "status": "completed", "result": json.loads(rf.read_text())})
            elif (INBOX / f"{rid}.json").exists():
                self._j(200, {"task_id": rid, "status": "pending"})
            else:
                self._j(404, {"error": "not found"})
        else:
            self._j(404, {"error": "not found"})

    def do_POST(self):
        if urlparse(self.path).path != "/task":
            self._j(404, {"error": "not found"})
            return
        if not self._auth():
            return
        n = int(self.headers.get("Content-Length", 0))
        try:
            d = json.loads(self.rfile.read(n))
        except Exception:
            self._j(400, {"error": "invalid JSON"})
            return
        task = d.get("task", "")
        if not task:
            self._j(400, {"error": "task required"})
            return
        cb = d.get("callback_url", "")
        if cb and not _safe_callback(cb):
            self._j(400, {"error": "callback_url failed SSRF check"})
            return
        tid = f"peer-{int(time.time()*1000)}"
        (INBOX / f"{tid}.json").write_text(json.dumps({
            "id": tid, "from": _safe_id(str(d.get("from", "unknown"))),
            "task": task, "priority": d.get("priority", "normal"),
            "callback_url": cb if cb else None, "ts": time.time(),
        }))
        self._j(200, {"ok": True, "task_id": tid, "result_url": f"/result/{tid}"})


if __name__ == "__main__":
    bind = os.environ.get("ANICCA_PEER_BIND", "127.0.0.1")
    print(f"anicca peer agent-api -> http://{bind}:{PORT}  (/ping /status /task /result)")
    if bind == "127.0.0.1":
        print("  localhost only — set ANICCA_PEER_BIND=0.0.0.0 for peer access")
    try:
        http.server.HTTPServer((bind, PORT), H).serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
