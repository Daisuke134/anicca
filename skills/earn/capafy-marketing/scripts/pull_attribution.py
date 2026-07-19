#!/usr/bin/env python3
"""Pull landing redirect counts and join them to the Capafy sales snapshot."""

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib import request

CAPAFY_HTTP = os.path.expanduser(
    "~/.openclaw/skills/capafy-autopublish/vendor/capafy-user/scripts/capafy_http.py"
)
DEFAULT_STATS_URL = "https://capafy-skills-daily.netlify.app/go-stats"
OUTPUT_FILE = Path(os.path.expanduser("~/.openclaw/state/capafy-attribution.jsonl"))


def _find_agent_list(value):
    if isinstance(value, list) and (not value or isinstance(value[0], dict)):
        return value
    if isinstance(value, dict):
        for nested in value.values():
            found = _find_agent_list(nested)
            if found is not None:
                return found
    return None


def _fetch_agents():
    result = subprocess.run(
        ["/opt/homebrew/bin/python3", CAPAFY_HTTP, "GET", "/agent/agents"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"capafy_http failed with exit {result.returncode}")
    start = min(
        (index for index in (result.stdout.find("{"), result.stdout.find("[")) if index >= 0),
        default=-1,
    )
    if start < 0:
        raise RuntimeError("no JSON in capafy_http output")
    return json.loads(result.stdout[start:])


def _existing_row(output_file: Path, day: str):
    if not output_file.exists():
        return None
    for line in output_file.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("date") == day:
            return row
    return None


def pull(
    stats_url: str = DEFAULT_STATS_URL,
    output_file: Path = OUTPUT_FILE,
    today: date | None = None,
):
    day = (today or date.today()).isoformat()
    existing = _existing_row(output_file, day)
    if existing is not None:
        return existing

    stats_request = request.Request(
        stats_url,
        headers={"Accept": "application/json", "User-Agent": "capafy-attribution/1"},
    )
    with request.urlopen(stats_request, timeout=30) as response:
        stats = json.load(response)
    if not isinstance(stats, dict):
        raise RuntimeError("go-stats response must be a JSON object")

    agents = _find_agent_list(_fetch_agents()) or []
    sales_by_id = {
        str(agent["agentId"]): agent
        for agent in agents
        if isinstance(agent, dict) and agent.get("agentId") is not None
    }
    joined = []
    for agent_id, clicks in sorted(stats.items(), key=lambda item: str(item[0])):
        snapshot = sales_by_id.get(str(agent_id), {})
        joined.append(
            {
                "agent_id": str(agent_id),
                "clicks": int(clicks),
                "sales": snapshot.get("sales"),
                "name": snapshot.get("name"),
            }
        )

    row = {"date": day, "agents": joined}
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("a", encoding="utf-8") as ledger:
        ledger.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    return row


def main() -> int:
    try:
        row = pull(stats_url=os.environ.get("CAPAFY_GO_STATS_URL", DEFAULT_STATS_URL))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **row}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
