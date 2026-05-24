#!/usr/bin/env python3
"""dais-x-feed-digest : Grok X Search source (alternative to RSSHub).

Calls Hermes Agent's internal `x_search_tool` Python API (uses Dais's
X Premium subscription via xai-oauth, NOT the paid xAI API -> no cost).
Returns the raw Grok analysis JSON. This is a SEARCH SOURCE only
(same role as fetch_rsshub.py); theme condensation / FRAME2 spec /
verification are still done by the skill model itself (HARD RULE #6).

Usage:
  uvx --from hermes-agent python run_x_search.py "<query>" [--raw]
    default : prints {"answer": ...} markdown only
    --raw   : prints the full x_search_tool JSON (answer + citations)

Ref: https://hermes-agent.nousresearch.com/docs/user-guide/features/x-search
"""
import json
import sys

from tools.x_search_tool import x_search_tool  # provided inside hermes-agent venv

if len(sys.argv) < 2:
    print("usage: run_x_search.py \"<query>\" [--raw]", file=sys.stderr)
    sys.exit(2)

query = sys.argv[1]
raw = "--raw" in sys.argv[2:]

s = x_search_tool(query)
data = json.loads(s)

if raw:
    print(json.dumps(data, ensure_ascii=False, indent=2))
else:
    if not data.get("success"):
        print(json.dumps(data, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    print(data.get("answer", ""))
