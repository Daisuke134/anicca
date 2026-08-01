#!/usr/bin/env python3
"""
B1 — Capafy promotion selector (deterministic TOOL, no LLM).

Reads the seller endpoint and the private evidence-audited portfolio. It selects
only an owned, online, evidence-backed ``promote`` product with no unmeasured
experiment conflict. Rotation is only a tie-breaker inside that eligible pool.

Emits a single clean JSON object on stdout with the selected listing — this is the
handoff to B2 (the running agent writes the tweet copy from name+desc) and then to
x_post.py (--url/--tweet/--reply).

The copy is NOT written here (that is the agent's judgment, per the skill's design).
This tool only selects + resolves the URL + does bookkeeping.
"""
import json, os, subprocess, sys, time
from pathlib import Path

import capafy_portfolio

CAPAFY_HTTP = os.path.expanduser(
    "~/.openclaw/skills/capafy-autopublish/vendor/capafy-user/scripts/capafy_http.py"
)
ROTATION = os.path.expanduser("~/.openclaw/state/capafy-marketing-rotation.jsonl")
PORTFOLIO = os.path.expanduser("~/.openclaw/state/capafy-portfolio.json")
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


def select_from(agents: list[dict], snapshot: dict, last: dict[str, int]) -> dict:
    """Select from observed ownership and agent-authored portfolio evidence."""
    products = snapshot.get("products", [])
    unmeasured = [
        product
        for product in products
        if isinstance(product.get("experiment"), dict)
        and product["experiment"].get("status") in {"proposed", "active"}
    ]
    if unmeasured:
        experiment = unmeasured[0]["experiment"]
        return {
            "ok": False,
            "error": (
                f"experiment {experiment.get('experiment_id', 'unknown')} must be "
                "measured before replacement"
            ),
        }

    owned_online = {
        str(agent.get("agentId")): agent
        for agent in agents
        if agent.get("agentStatus") == "online" and agent.get("agentId") is not None
    }
    eligible: list[tuple[dict, dict]] = []
    for product in products:
        agent_id = str(product.get("agent_id") or "")
        if (
            agent_id in owned_online
            and product.get("observed_status") == "online"
            and product.get("decision") == "promote"
            and isinstance(product.get("evidence"), list)
            and bool(product["evidence"])
            and product.get("public_url") == LISTING_URL_FMT.format(agent_id=agent_id)
        ):
            eligible.append((product, owned_online[agent_id]))
    if not eligible:
        return {"ok": False, "error": "no evidence-eligible owned listings"}

    eligible.sort(key=lambda pair: last.get(pair[0]["agent_id"], 0))
    product, remote = eligible[0]
    return {
        "ok": True,
        "agent_id": product["agent_id"],
        "name": remote.get("name") or product["name"],
        "desc": (remote.get("desc") or product["description"] or "")[:600],
        "sales": remote.get("sales"),
        "rating": remote.get("rating"),
        "url": product["public_url"],
        "online_pool": len(owned_online),
        "eligible_pool": len(eligible),
        "portfolio_decision": product["decision"],
        "evidence_count": len(product["evidence"]),
    }


def main() -> int:
    try:
        agents = _fetch_agents()
        path = Path(os.environ.get("CAPAFY_PORTFOLIO", PORTFOLIO))
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        errors = capafy_portfolio.validate_snapshot(snapshot)
        if errors:
            raise ValueError("; ".join(errors))
        out = select_from(agents, snapshot, _load_rotation())
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        out = {"ok": False, "error": f"portfolio selection failed: {exc}"}
    if not out["ok"]:
        print(json.dumps(out, ensure_ascii=False))
        return 1
    _record(out["agent_id"])
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
