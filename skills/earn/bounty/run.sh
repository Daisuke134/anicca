#!/usr/bin/env bash
# earn/bounty — ONE Anicca loop slot. Algora GitHub bounties (the one VERIFIED-live platform 2026):
# claim an OPEN bounty → submit a PR → TRACK the PR thread until MERGED → payout. EARN_MODE:
#   discover — gh-search live open Algora bounties → state/bounties.json (agent-doable ranked).
#   track    — for each attempt in state/attempts.jsonl, poll its PR (reviews/state); on MERGE,
#              record-earn (real external USDC only, INV-7). The loop is NOT one-off: it iterates.
# NO HUMAN for discover/track; the PR coding is the brain's job; payout KYC (Stripe) = honest gap.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EARN_MODE="${EARN_MODE:-discover}"
WAKE="${WAKE_ID:-$(date -u +%s)}"
PY=/opt/homebrew/bin/python3
STATE="$HERE/state"; mkdir -p "$STATE"
emit(){ printf '{"slot":"earn/bounty","did":%s,"earn_usdc":0,"cost_usdc":0}\n' \
  "$(printf '%s' "$1" | "$PY" -c 'import json,sys;print(json.dumps(sys.stdin.read()))')"; }

discover(){
  local bj="$STATE/bounties.json"
  # live open Algora bounties (the algora-pbc bot comments on the funded issue)
  gh api -X GET search/issues -f q='commenter:algora-pbc state:open' -f per_page=50 2>/dev/null \
    | "$PY" - "$bj" "$WAKE" <<'PY' 2>/dev/null
import json,sys,re
d=json.load(sys.stdin); items=d.get("items",[])
out=[]
for it in items:
    if it.get("pull_request"): continue          # issues only
    if it.get("assignee"): continue              # skip assigned
    repo=re.sub(r'.*/repos/','',it.get("repository_url","")).strip()
    out.append({"title":it.get("title","")[:80],"url":it.get("html_url",""),"repo":repo,
                "comments":it.get("comments",0)})
json.dump({"fetched_at":sys.argv[2],"open_bounties":out}, open(sys.argv[1],"w"), indent=2)
print(len(out))
PY
  local n; n=$([ -f "$bj" ] && "$PY" -c "import json;print(len(json.load(open('$bj')).get('open_bounties',[])))" 2>/dev/null || echo 0)
  echo "[bounty] discover wake=$WAKE open_algora_bounties=$n"
  emit "discover: $n open Algora bounties (state/bounties.json). Claim agent-doable ones via a PR; payout = Stripe KYC gate."
}

track(){
  local af="$STATE/attempts.jsonl" merged=0 tracked=0
  [ -f "$af" ] || { emit "track: no attempts yet (state/attempts.jsonl empty)"; return; }
  # each line: {"repo":"o/r","pr":N,"issue":N,"bounty_usd":X}
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    local repo pr; repo=$("$PY" -c "import json,sys;print(json.loads(sys.argv[1]).get('repo',''))" "$line" 2>/dev/null)
    pr=$("$PY" -c "import json,sys;print(json.loads(sys.argv[1]).get('pr',''))" "$line" 2>/dev/null)
    [ -n "$repo" ] && [ -n "$pr" ] || continue
    tracked=$((tracked+1))
    local st; st=$(gh pr view "$pr" -R "$repo" --json state,reviewDecision 2>/dev/null | "$PY" -c "import json,sys;d=json.load(sys.stdin);print(d.get('state',''),d.get('reviewDecision',''))" 2>/dev/null)
    echo "[bounty] track $repo#$pr → $st"
    case "$st" in MERGED*) merged=$((merged+1));; esac
  done < "$af"
  emit "track: $tracked PR(s) monitored, $merged merged. (on merge → record-earn when payout lands)"
}

case "$EARN_MODE" in track) track ;; *) discover ;; esac
exit 0
