#!/usr/bin/env bash
# cook/run.sh — the EXPLORE earner: search the web for a NEW way to earn, surface candidates, and
# (when the model decides) share the find to the colony forum so peers can try it too.
#
# HARD RULE #0: this is a TOOL, not a decision. cook does NOT decide WHAT to build or WHETHER a lead is
# good — it brings the model fresh, real candidates (with URLs) and the model decides. Pattern copied
# from vinid/einstein-arena (explore → try → share-numbers) + BlockRunAI/Franklin (the model judges from
# real context, no hardcoded seed list). NOTHING hardcoded: the search query comes from $ANICCA_ARGS
# (the model's curiosity this wake) or a small rotating default; we do not pin specific repos/links.
#
# Env: ANICCA_ARGS (JSON, optional) — {"query":"<what to look for>"}; WAKE_ID.
# Output: records ONE narrate line to the earn ledger (source=cook) + prints the candidates as JSON so
# the model sees them next wake. Never spends money, never bricks.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WAKE="${WAKE_ID:-$(date -u +%s)}"
LEDGER="${EARN_LEDGER:-$HERE/../earn/state/earn-ledger.jsonl}"
ARGS="${ANICCA_ARGS:-{}}"

# the model's search intent this wake (its own words), or a neutral default that rotates by hour so we
# never re-search the same thing — automaton-style "find externally new options", no hardcoded links.
QUERY=$(printf '%s' "$ARGS" | python3 -c "
import json,sys,time
try: q=(json.load(sys.stdin) or {}).get('query','')
except Exception: q=''
if not q:
    seeds=['new x402 paid API agents pay for','open-source DeFi yield strategy 2026 base','agent micro-task marketplace USDC','new onchain fee-earning protocol base','sell data or research for crypto agent']
    q=seeds[int(time.time()//3600)%len(seeds)]
print(q)
" 2>/dev/null)
echo "[cook] exploring: $QUERY"

# Real web search via firecrawl (the project's canonical web tool) — bring back live candidates + URLs.
RESULTS=$(/opt/homebrew/bin/firecrawl scrape "https://www.google.com/search?q=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$QUERY earn USDC agent github")" markdown 2>/dev/null \
  | grep -oE "https://github.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+" | grep -viE "google|search" | sort -u | head -5)
[ -z "$RESULTS" ] && RESULTS="(no fresh candidates this wake; try a different query)"
echo "[cook] candidates:"; printf '%s\n' "$RESULTS" | sed 's/^/  - /'

# record a narrate line so the wake is logged + the candidates ride into the next wake's context.
CANDJSON=$(printf '%s' "$RESULTS" | python3 -c "import sys,json;print(json.dumps([l for l in sys.stdin.read().split('\n') if l.strip()]))")
JSON=$(python3 -c "import json;print(json.dumps({'source':'cook','task':'explore: ${QUERY//\'/}','candidates':$CANDJSON,'earn_usdc':0,'cost_usdc':0,'wake':'$WAKE'}))" 2>/dev/null)
node "$HERE/../_shared/lib/record.mjs" "$JSON" "$LEDGER" 2>/dev/null || node "$HERE/../earn/lib/record.mjs" "$JSON" "$LEDGER" 2>/dev/null || echo "$JSON" >> "$LEDGER"
echo "[cook] recorded explore wake (candidates surfaced for the model to try next)."
exit 0
