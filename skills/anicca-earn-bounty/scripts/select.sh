#!/usr/bin/env bash
# anicca-earn-bounty/scripts/select.sh
# scan 結果 から 1 件 を Claude API で feasibility 判定して pick

set -uo pipefail
[ -f "$HOME/.openclaw/.env" ] && set -a && source "$HOME/.openclaw/.env" && set +a

SKILL_DIR="$HOME/.openclaw/skills/anicca-earn-bounty"
STATE="$SKILL_DIR/state"
LATEST_SCAN="$STATE/latest-scan.json"

if [ ! -f "$LATEST_SCAN" ]; then
  echo "[select] no scan found, run scan.sh first" >&2
  exit 1
fi

# Filter: budget >= $10, exclude crypto-only or AI-art or content-grind
CANDIDATES=$(jq '[.[] | select(.amount_usd >= 10) | select(.title | test("(?i)pi |sphere|spam|每日|info-flow") | not)] | sort_by(-.amount_usd) | .[:15]' "$LATEST_SCAN")

CAND_COUNT=$(echo "$CANDIDATES" | jq 'length')
if [ "$CAND_COUNT" -eq 0 ]; then
  echo "[select] no candidates >= \$10 found" >&2
  exit 2
fi

echo "[select] $CAND_COUNT candidates >= \$10 to evaluate" >&2

# Use Claude API if available, else fallback to deterministic top-amount pick
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  SYSTEM='You are an autonomous AI coding agent (Anicca, running on OpenClaw + Claude SDK). You evaluate GitHub bounty issues and pick ONE that you can actually solve in 1-3 hours, deliver via PR, and earn USDC (Algora AutoPay).

Selection criteria (in order):
1. Code change feasible with LLM-only (no domain expertise, no UI testing, no manual setup)
2. Self-contained (single file or small set, clear bug or feature)
3. Language match: Python, TypeScript, JavaScript, Go, Solidity, Bash
4. Budget $10-500 (avoid >$1000 = likely too complex)
5. Recent (created in last 60 days)
6. Repo not abandoned (avoid <10 stars or no recent commits)

Output JSON ONLY: {"picked_index": N, "reason": "...", "confidence": 0.0-1.0}
picked_index = 0-indexed into candidates array. confidence < 0.5 → return -1.'

  USER_PROMPT="Candidates (max 15, sorted by amount):
$CANDIDATES

Pick 1 you can deliver in 1-3 hours. Output JSON only."

  RESP=$(curl -sS https://api.anthropic.com/v1/messages \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    -d "$(SYS="$SYSTEM" USR="$USER_PROMPT" python3 -c '
import json, os
print(json.dumps({
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 800,
  "system": os.environ["SYS"],
  "messages": [{"role": "user", "content": os.environ["USR"]}]
}))')" --max-time 60)

  PICK=$(echo "$RESP" | python3 -c '
import json, sys, re
d = json.load(sys.stdin)
if "error" in d:
    sys.stderr.write(f"API error: {d.get(\"error\")}\n")
    sys.exit(1)
text = d.get("content",[{}])[0].get("text","")
# Extract JSON
m = re.search(r"\{[^{}]*\"picked_index\"[^{}]*\}", text, re.DOTALL)
if m:
    print(m.group(0))
else:
    print(text)
')
  echo "[select] Claude verdict: $PICK" >&2

  IDX=$(echo "$PICK" | jq -r .picked_index 2>/dev/null || echo "-1")
  CONFIDENCE=$(echo "$PICK" | jq -r .confidence 2>/dev/null || echo "0")

  if [ "$IDX" = "-1" ] || [ "$IDX" = "null" ]; then
    echo "[select] Claude declined all candidates" >&2
    exit 3
  fi
else
  echo "[select] no ANTHROPIC_API_KEY, fallback to top-amount" >&2
  IDX=0
  PICK='{"picked_index":0,"reason":"fallback: highest amount","confidence":0.3}'
fi

# Output picked bounty
PICKED=$(echo "$CANDIDATES" | jq ".[$IDX]")
echo "$PICKED" > "$STATE/picked-bounty.json"

# Add to history
echo "$PICK" | jq --argjson b "$PICKED" --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '. + {bounty: $b, selected_at: $ts}' >> "$SKILL_DIR/data/selection-history.jsonl"

echo "[select] picked:"
echo "$PICKED" | jq '{title, amount_usd, url, repo}'
