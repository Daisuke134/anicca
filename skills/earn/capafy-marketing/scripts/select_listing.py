#!/usr/bin/env python3
"""
B1 — Capafy promotion selector (deterministic TOOL, no LLM).

Reads the seller endpoint GET /agent/agents (no buyer token needed), keeps only
agentStatus=="online" listings, and picks ONE with rotation + dedup so we don't
promote the same listing twice in a row. Records each pick in a rotation ledger.

Emits a single clean JSON object on stdout with the selected listing — this is the
handoff to B2 (the running agent writes the tweet copy from name+desc) and then to
x_post.py (--url/--tweet/--reply).

The copy is NOT written here (that is the agent's judgment, per the skill's design).
This tool only selects + resolves the URL + does bookkeeping.
"""
import json, os, subprocess, sys, time
from pathlib import Path

REPO_ROOT = Path(os.environ.get("LIFE_MANAGER_REPO", Path(__file__).resolve().parents[4]))
CAPAFY_HTTP = str(REPO_ROOT / "skills/capafy-autopublish/vendor/capafy-user/scripts/capafy_http.py")
ROTATION = os.path.expanduser("~/.local/state/life-manager/state/capafy-marketing-rotation.jsonl")
LISTING_URL_FMT = "https://capafy.ai/agent/{agent_id}"


def _fetch_agents() -> list:
    out = subprocess.run(
        ["/opt/homebrew/bin/python3", CAPAFY_HTTP, "GET", "/agent/agents"],
        capture_output=True, text=True, timeout=60,
    ).stdout
    # capafy_http prints a log line then the JSON body; grab from the first { or [
    start = min((i for i in (out.find("{"), out.find("[")) if i >= 0), default=-1)
    if start < 0:
        raise RuntimeError("no JSON in capafy_http output")
    d = json.loads(out[start:])

    def find_list(x):
        if isinstance(x, list) and x and isinstance(x[0], dict):
            return x
        if isinstance(x, dict):
            for v in x.values():
                r = find_list(v)
                if r:
                    return r
        return None
    return find_list(d) or []


def _load_rotation() -> dict:
    last = {}
    if os.path.exists(ROTATION):
        for line in open(ROTATION):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                last[r["agent_id"]] = r["ts"]
            except Exception:  # noqa: BLE001
                continue
    return last


def _record(agent_id: str) -> None:
    os.makedirs(os.path.dirname(ROTATION), exist_ok=True)
    with open(ROTATION, "a") as f:
        f.write(json.dumps({"agent_id": agent_id, "ts": int(time.time())}) + "\n")


def main() -> int:
    agents = _fetch_agents()
    online = [a for a in agents if a.get("agentStatus") == "online"]
    if not online:
        print(json.dumps({"ok": False, "error": "no online listings"}))
        return 1

    last = _load_rotation()
    # rotation: pick the online listing promoted least recently (never-promoted = ts 0).
    online.sort(key=lambda a: last.get(str(a.get("agentId")), 0))
    pick = online[0]
    agent_id = str(pick.get("agentId"))

    _record(agent_id)
    out = {
        "ok": True,
        "agent_id": agent_id,
        "name": pick.get("name"),
        "desc": (pick.get("desc") or "")[:600],
        "sales": pick.get("sales"),
        "rating": pick.get("rating"),
        "url": LISTING_URL_FMT.format(agent_id=agent_id),
        "online_pool": len(online),
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
