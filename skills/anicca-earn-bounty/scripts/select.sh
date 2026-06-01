#!/usr/bin/env bash
# anicca-earn-bounty/scripts/select.sh
# Relaxed filter — pick first viable candidate, attempt even if uncertain.
# Strategy: better to submit + lose than submit nothing.

set -uo pipefail
[ -f "$HOME/.openclaw/.env" ] && set -a && source "$HOME/.openclaw/.env" && set +a

SKILL_DIR="$HOME/.openclaw/skills/anicca-earn-bounty"
STATE="$SKILL_DIR/state"
LATEST_SCAN="$STATE/latest-scan.json"
[ -f "$LATEST_SCAN" ] || { echo "[select] no scan" >&2; exit 1; }

# Recent, concrete bounties only. Older or amount-less issues waste earn-loop beats.
CUTOFF_ISO=$(python3 - <<'PY'
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc) - timedelta(days=45)).strftime("%Y-%m-%dT%H:%M:%SZ"))
PY
)

# Relaxed filter:
#   - amount >= $10 (concrete bounty signal)
#   - created within last 45 days
#   - exclude stale/noisy repos that repeatedly waste beats
#   - exclude noisy/non-bounty content feeds that happen to contain "$"
#   - prefer issues w/ < 10 comments (= less competition)
#   - exclude joke / directory / content-farm issues
#   - exclude strategy / roadmap / business-plan / doc-only "bounties"
#   - require an explicit "approachable work" signal before spending a beat
#   - require software/code signals aligned with the skill's language match
CANDIDATES=$(jq '
  [.[] |
    select((.amount_usd // 0) >= 10 and (.amount_usd // 0) <= 50000) |
    select((.created_at // "") >= $cutoff) |
    select(.repo | test("(?i)fuzoe/pd-hunter|^bountysource/core$|BruceFeIix/picker|Tyaoo/picker|Mossaka/wassette") | not) |
    select(.title | test("(?i)calculate.{0,5}pi|alternatives.to|weekly research|每日信息流|daily info") | not) |
    select((((.title // "") + " " + (.description // "") + " " + ((.labels // []) | join(" "))) | test("(?i)\\b(epic|spec|roadmap|business plan|go-to-market|marketing plan|launch plan|monetization|sponsorship|distribution|growth plan|strategy|strategic|analysis|proposal|design doc|24-month|24 month|docs?/roadmap)\\b")) | not) |
    select((((.title // "") + " " + ((.labels // []) | join(" "))) | test("(?i)good first issue|help wanted|ai agent friendly|\\bbounty\\b|💎"))) |
    select((((.title // "") + " " + (.description // "") + " " + ((.labels // []) | join(" "))) | test("(?i)\\b(api|endpoint|route|page|component|auth|validation|schema|test|bug|fix|render|frontend|backend|python|typescript|javascript|node|react|next|go|golang|solidity|sql|cli|sdk|driver)\\b"))) |
    select((.comments // 0) < 30)
  ] | sort_by(if (.amount_usd // 0) < 100 then 1 else 0 end, (.comments // 0), -.amount_usd) | .[:20]
' --arg cutoff "$CUTOFF_ISO" "$LATEST_SCAN")

CAND_COUNT=$(echo "$CANDIDATES" | jq 'length')
[ "$CAND_COUNT" -eq 0 ] && {
  echo "[select] 0 viable recent bounties after concrete filter (cutoff=$CUTOFF_ISO)" >&2
  exit 2
}
echo "[select] $CAND_COUNT candidates passed relaxed filter" >&2

# Pick first (= lowest comments, then highest amount among <$100 / pure-amount otherwise)
PICKED=$(echo "$CANDIDATES" | jq '.[0]')
echo "$PICKED" > "$STATE/picked-bounty.json"
mkdir -p "$SKILL_DIR/data"
echo "{\"selected_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"bounty\":$PICKED,\"selector\":\"relaxed-fallback\"}" >> "$SKILL_DIR/data/selection-history.jsonl"

echo "[select] picked:"
echo "$PICKED" | jq '{title, amount_usd, url, repo, comments, created_at}'
