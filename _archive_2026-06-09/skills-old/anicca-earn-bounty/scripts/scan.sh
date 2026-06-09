#!/usr/bin/env bash
# anicca-earn-bounty/scripts/scan.sh
# GitHub native search 経由で bounty 付き issue を discover (= 認証 不要、 rate-limit 60/hr without PAT, 5000/hr with PAT)

set -uo pipefail
[ -f "$HOME/.openclaw/.env" ] && set -a && source "$HOME/.openclaw/.env" && set +a

SKILL_DIR="$HOME/.openclaw/skills/anicca-earn-bounty"
STATE="$SKILL_DIR/state"
DATA="$SKILL_DIR/data"
mkdir -p "$STATE" "$DATA"

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
OUT="$STATE/scan-$(date -u +%s).json"

# Auth header (optional - higher rate limit with PAT)
AUTH_HEADER=""
if [ -n "${GITHUB_TOKEN:-}" ]; then
  AUTH_HEADER="-H Authorization:Bearer\ $GITHUB_TOKEN"
fi

# GitHub search queries (= 各 bounty platform の signature pattern)
declare -a QUERIES=(
  # Algora bounties (= 💎 emoji or "algora" mention)
  'is:issue+is:open+label:"%F0%9F%92%8E+Bounty"'
  'is:issue+is:open+label:bounty+algora+in:body'
  # OnlyDust (= "OnlyDust" / "OD" label)
  'is:issue+is:open+label:OnlyDust'
  # Plain bounty label (= 全体総合)
  'is:issue+is:open+label:bounty+%24+in:title'
  'is:issue+is:open+%2Fbounty+%24+in:body'
  'is:issue+is:open+bounty:+%24'
  'is:issue+is:open+reward+%24+in:body'
  # Replit
  'is:issue+is:open+replit+bounty+in:body'
)

all_results="[]"
total=0

for q in "${QUERIES[@]}"; do
  url="https://api.github.com/search/issues?q=$q&sort=created&order=desc&per_page=30"
  echo "[scan] query: $q" >&2

  if [ -n "${GITHUB_TOKEN:-}" ]; then
    resp=$(curl -sS -H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/vnd.github+json" \
      "$url" --max-time 20 2>/dev/null)
  else
    resp=$(curl -sS -H "Accept: application/vnd.github+json" "$url" --max-time 20 2>/dev/null)
  fi

  count=$(echo "$resp" | jq '.items | length' 2>/dev/null || echo 0)
  total=$((total + count))

  # Normalize
  norm=$(echo "$resp" | python3 -c '
import json, sys, re
try:
    raw = sys.stdin.read().strip() or "{}"
    data = json.loads(raw)
    items = data.get("items", [])
    out = []
    for it in items[:30]:
        if not isinstance(it, dict): continue
        body = (it.get("body","") or "")[:500]
        title = (it.get("title","") or "")[:200]
        labels = [l.get("name","") for l in it.get("labels",[])]
        # Extract bounty amount (= "$XXX" / "💎 $XXX" pattern)
        bounty_text = " ".join([title, body, " ".join(labels)])
        m = (
            re.search(r"/bounty\s*\$\s*([\d,]+(?:\.\d+)?)", bounty_text, re.I)
            or re.search(r"bounty:\s*\$\s*([\d,]+(?:\.\d+)?)", bounty_text, re.I)
            or re.search(r"\$\s*([\d,]+(?:\.\d+)?)", bounty_text)
        )
        amount = float(m.group(1).replace(",","")) if m else 0
        # Detect language from repo
        repo_url = it.get("repository_url","")
        repo = "/".join(repo_url.split("/repos/")[-1].split("/")[:2]) if repo_url else ""
        out.append({
            "platform": "github-search",
            "id": str(it.get("id","")),
            "title": title,
            "url": it.get("html_url",""),
            "amount_usd": amount,
            "repo": repo,
            "description": body,
            "labels": labels,
            "comments": it.get("comments", 0),
            "created_at": it.get("created_at",""),
        })
    print(json.dumps(out))
except Exception as e:
    print("[]", file=sys.stderr)
    print("[]")
')

  all_results=$(jq -n --argjson a "$all_results" --argjson b "$norm" '$a + $b')

  # Polite rate limit
  sleep 2
done

# Dedup by url
deduped=$(echo "$all_results" | jq 'unique_by(.url)')
dedup_count=$(echo "$deduped" | jq 'length')

echo "$deduped" > "$OUT"
ln -sf "$(basename "$OUT")" "$STATE/latest-scan.json"

jq -n \
  --arg ts "$TS" \
  --argjson raw_total "$total" \
  --argjson unique_total "$dedup_count" \
  --arg out "$OUT" \
  '{
    queried_at: $ts,
    raw_results: $raw_total,
    unique_bounties: $unique_total,
    output_path: $out
  }'
