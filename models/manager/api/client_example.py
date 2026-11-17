"""Call the Manager API from the shell — the proof that Manager is callable.

Usage:
  python client_example.py score
  python client_example.py intervene
  python client_example.py generate
Server: MANAGER_API_URL (default http://127.0.0.1:8791)
"""

import json
import os
import sys
import urllib.request

BASE = os.environ.get("MANAGER_API_URL", "http://127.0.0.1:8791")

HISTORY = {
    "recency": 9,
    "history": 182.53,
    "mens": 1,
    "womens": 0,
    "zip_code": "Surburban",
    "newbie": 0,
    "channel": "Web",
}


def call(path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE + path, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "score"
    if cmd == "score":
        for backend in ("prior", "manager-v1"):
            print(backend, call("/v1/score", {"personal_history": HISTORY, "backend": backend}))
    elif cmd == "intervene":
        payload = {
            "personal_history": HISTORY,
            "candidates": [
                {"intervention_id": "womens_email", "arm": "womens_email"},
                {"intervention_id": "no_contact", "arm": "none"},
            ],
            "backend": "manager-v1",
        }
        print(call("/v1/intervene", payload))
    elif cmd == "generate":
        print(call("/v1/generate", {
            "prompt": "大喜利のお題に一言でボケて答えてください。\nお題: 世界一使えないカーナビ、なんて言う？\n回答:",
            "backend": "manager-v1",
        }))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
