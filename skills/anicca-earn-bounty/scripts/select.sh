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

# Relaxed filter:
#   - amount >= $10 (lower bar)
#   - created since 2026-02-01 (= older accepted)
#   - exclude obvious honeypots (SecureBananaLabs)
#   - exclude obviously stale (bountysource/core 2023)
#   - prefer issues w/ < 10 comments (= less competition)
#   - exclude PI calculation joke
CANDIDATES=$(jq '
  [.[] |
    select(.amount_usd >= 10 and .amount_usd <= 50000) |
    select(.repo | test("(?i)securebananalabs|fuzoe/pd-hunter|^bountysource/core$") | not) |
    select(.title | test("(?i)calculate.{0,5}pi|alternatives.to") | not) |
    select((.comments // 0) < 30)
  ] | sort_by(if (.amount_usd // 0) < 100 then 1 else 0 end, (.comments // 0), -.amount_usd) | .[:20]
' "$LATEST_SCAN")

CAND_COUNT=$(echo "$CANDIDATES" | jq 'length')
[ "$CAND_COUNT" -eq 0 ] && { echo "[select] still 0 after relaxed filter" >&2; exit 2; }
echo "[select] $CAND_COUNT candidates passed relaxed filter" >&2

# Pick first (= lowest comments, then highest amount among <$100 / pure-amount otherwise)
PICKED=$(echo "$CANDIDATES" | jq '.[0]')
echo "$PICKED" > "$STATE/picked-bounty.json"
mkdir -p "$SKILL_DIR/data"
echo "{\"selected_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"bounty\":$PICKED,\"selector\":\"relaxed-fallback\"}" >> "$SKILL_DIR/data/selection-history.jsonl"

echo "[select] picked:"
echo "$PICKED" | jq '{title, amount_usd, url, repo, comments, created_at}'
