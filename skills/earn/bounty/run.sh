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
import os
# GitHub search intermittently returns total_count>0 but items:[] (rate-limit/consistency).
# Don't clobber good prior data on a transient empty response.
if not items and os.path.exists(sys.argv[1]):
    print(len(json.load(open(sys.argv[1])).get("open_bounties",[]))); sys.exit()
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

# ── gate: filter discovered bounties to genuinely-attemptable ones (the drizzle#1188 lesson) ──
# Deterministic checks via gh: (a) funder NOT withdrawn (issue comments), (b) NO existing open PR
# referencing the issue. (c) fix-not-blocked + (d) agent-doable are left to the brain's judgment on
# the survivors. Bounded to the top N candidates (gh rate-limit + time).
gate(){
  local bj="$STATE/bounties.json" gj="$STATE/gated.json" n="${BOUNTY_GATE_N:-12}"
  [ -f "$bj" ] || discover >/dev/null 2>&1
  "$PY" - "$bj" "$gj" "$n" <<'PY' 2>/dev/null
import json,sys,subprocess,re
bj,gj,n=sys.argv[1],sys.argv[2],int(sys.argv[3])
def sh(args):
    try: return subprocess.run(args,capture_output=True,text=True,timeout=30).stdout
    except Exception: return ""
items=json.load(open(bj)).get("open_bounties",[])[:n]
survivors=[]
for it in items:
    repo=it.get("repo",""); url=it.get("url","")
    m=re.search(r'/issues/(\d+)',url)
    if not repo or not m: continue
    num=m.group(1)
    # (a) funder withdrawn? scan comments
    cj=sh(["gh","issue","view",num,"-R",repo,"--json","comments,closed,state"])
    try: d=json.loads(cj) if cj.strip() else {}
    except Exception: d={}
    if d.get("state")!="OPEN": continue
    comments=d.get("comments",[])
    body=" ".join(c.get("body","") for c in comments)
    if re.search(r'removing the bounty|bounty.*(removed|withdrawn|cancell?ed|no longer)|no bounty', body, re.I):
        continue
    # keystatic#340 lesson: Algora marks a WITHDRAWN bounty by rendering the bot's bounty comment
    # in ~~strikethrough~~. Skip if any algora-pbc comment has its bounty line struck through.
    algora=[c for c in comments if "algora" in (c.get("author",{}) or {}).get("login","").lower()]
    if any(re.search(r'~~.{0,40}bounty', c.get("body",""), re.I|re.S) for c in algora):
        continue
    # require an ACTIVE (non-struck) algora bounty comment to exist at all
    if not any(re.search(r'\bbounty\b', c.get("body","")) and not c.get("body","").lstrip().startswith("~~") for c in algora):
        continue
    # (b) existing open PR referencing the issue?
    pl=sh(["gh","pr","list","-R",repo,"--state","open","--search",f"#{num} in:body","--json","number"])
    try: prs=json.loads(pl) if pl.strip() else []
    except Exception: prs=[]
    if prs: continue   # someone already has an open PR
    # (c) REAL project? filter the fake/farm layer (test repos, throwaway numeric-username accounts,
    # near-zero-star playgrounds) the research flagged as fake-money. Require a real org + some traction.
    owner=repo.split("/")[0]; name=repo.split("/")[-1]
    if name.lower() in ("test","young","playground","sandbox","demo") or re.fullmatch(r'\d{6,}',owner):
        continue
    rj=sh(["gh","repo","view",repo,"--json","stargazerCount,isFork,description"])
    try: r=json.loads(rj) if rj.strip() else {}
    except Exception: r={}
    if int(r.get("stargazerCount",0)) < 50: continue   # real funded projects have traction
    # (d) REAL USD, not a self-issued token (Rustchain#2239 lesson: paid in 'RTC', algora page 404).
    blob=(it.get("title","")+" "+body+" "+(r.get("description") or "")).lower()
    if re.search(r'\bearn [a-z]{2,5}\b|\b\d+\s*(rtc|\$[a-z]{2,6}|tokens?)\b|token.?farm|social mining|clanker|/tip', blob):
        continue   # token-reward / tip farm, not USD
    survivors.append({**it,"issue":int(num),"stars":r.get("stargazerCount",0),"gate":"passed (funder-active, no-open-PR, real-repo>=50★, USD-not-token)"})
json.dump({"survivors":survivors,"checked":len(items)}, open(gj,"w"), indent=2)
print(f"{len(survivors)}/{len(items)}")
PY
  local s; s=$([ -f "$gj" ] && "$PY" -c "import json;print(len(json.load(open('$gj')).get('survivors',[])))" 2>/dev/null || echo 0)
  echo "[bounty] gate: $s candidates passed (funder-active + no-open-PR) of top $n"
  emit "gate: $s attemptable bounties (state/gated.json). Brain then judges fix-not-blocked + agent-doable, picks ONE."
}

case "$EARN_MODE" in track) track ;; gate) gate ;; *) discover ;; esac
exit 0
