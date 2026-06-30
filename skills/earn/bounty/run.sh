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

# ── attempt: turn the top gated survivor into a WORK-ORDER the coding-brain executes (FIND-001) ──
# Writes an attempts.jsonl entry {repo,issue,bounty_usd,status:claim} so track() has something to
# watch and the brain/coding-subagent has a concrete handoff (claim /attempt + open the PR, then set
# pr:N). The actual fix IS real engineering (legitimately the brain's job) — but the artifact exists.
attempt(){
  local gj="$STATE/gated.json" af="$STATE/attempts.jsonl"
  [ -f "$gj" ] || gate >/dev/null 2>&1
  local pick; pick=$("$PY" -c "import json;s=json.load(open('$gj')).get('survivors',[]);print(json.dumps(s[0]) if s else '')" 2>/dev/null)
  [ -n "$pick" ] || { emit "attempt: no gated survivor to claim (real-USD inventory empty)"; return; }
  # don't double-claim the same issue
  local key; key=$("$PY" -c "import json,sys;d=json.loads(sys.argv[1]);print(d['repo']+'#'+str(d['issue']))" "$pick" 2>/dev/null)
  if [ -f "$af" ] && grep -qF "\"key\":\"$key\"" "$af" 2>/dev/null; then emit "attempt: $key already claimed (tracking)"; return; fi
  "$PY" -c "import json,sys;d=json.loads(sys.argv[1]);print(json.dumps({'key':d['repo']+'#'+str(d['issue']),'repo':d['repo'],'issue':d['issue'],'bounty_usd':d.get('bounty_usd',0),'pr':None,'status':'claim','wake':sys.argv[2]}))" "$pick" "$WAKE" >> "$af"
  emit "attempt: WORK-ORDER written for $key (\$$(printf '%s' "$pick"|"$PY" -c 'import json,sys;print(json.load(sys.stdin).get("bounty_usd",0))' 2>/dev/null)). Brain: /attempt + fix(VSDD) + PR → set pr:N."
}

track(){
  local af="$STATE/attempts.jsonl" merged=0 tracked=0
  [ -f "$af" ] || { emit "track: no attempts yet (state/attempts.jsonl empty)"; return; }
  # each line: {"key","repo":"o/r","pr":N|null,"issue":N,"bounty_usd":X,"status"}
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    local repo pr; repo=$("$PY" -c "import json,sys;print(json.loads(sys.argv[1]).get('repo',''))" "$line" 2>/dev/null)
    pr=$("$PY" -c "import json,sys;v=json.loads(sys.argv[1]).get('pr');print(v if v else '')" "$line" 2>/dev/null)
    [ -n "$repo" ] || continue
    tracked=$((tracked+1))
    [ -n "$pr" ] || { echo "[bounty] track $repo (no PR yet — awaiting brain)"; continue; }
    local st; st=$(gh pr view "$pr" -R "$repo" --json state,reviewDecision 2>/dev/null | "$PY" -c "import json,sys;d=json.load(sys.stdin);print(d.get('state',''),d.get('reviewDecision',''))" 2>/dev/null)
    echo "[bounty] track $repo#$pr → $st"
    case "$st" in MERGED*) merged=$((merged+1));; esac
  done < "$af"
  # SETTLE (FIND-002): if anything merged, call the chain oracle — only real external USDC counts (INV-7)
  if [ "$merged" -gt 0 ]; then
    local re="${ANICCA_HOME:-$HOME/anicca}/skills/self/founder-loop/record-earn.mjs"
    if [ -f "$re" ]; then local out; out=$(timeout 45 node "$re" --source bounty --task settle --wake "$WAKE" 2>&1 || true); echo "[bounty] settle: $out"; fi
  fi
  emit "track: $tracked attempt(s), $merged merged → record-earn settle (real USDC only)."
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
    # (c) not an obvious throwaway/farm repo (name/owner heuristic only — NOT a star cut, which
    # over-drops real small-org bounties like microg/GmsCore $1340). Token-farms are caught by (d).
    owner=repo.split("/")[0]; name=repo.split("/")[-1]
    if name.lower() in ("test","young","playground","sandbox","demo") or re.fullmatch(r'\d{6,}',owner):
        continue
    # (d) REAL USD — read the AMOUNT from the active algora-pbc comment, do NOT keyword-guess (the old
    # `\d+ tokens?` regex false-matched ORM/CSS "N tokens" and wrongly dropped real bounties like
    # drizzle/zod). An active bounty line "$200 bounty" → USD + amount. "75 RTC" (no $) → token, skip.
    active=[c.get("body","") for c in algora if not c.get("body","").lstrip().startswith("~~")]
    amt=0
    for b in active:
        mm=re.search(r'\$([0-9][0-9,]*)\s*(?:bounty|reward|tip)', b, re.I) or re.search(r'bounty.{0,12}\$([0-9][0-9,]*)', b, re.I)
        if mm: amt=max(amt,int(mm.group(1).replace(",",""))); break
    if amt<=0: continue   # no USD ($) amount in the active algora comment → token/none, skip
    rj=sh(["gh","repo","view",repo,"--json","stargazerCount"])
    try: stars=json.loads(rj).get("stargazerCount",0) if rj.strip() else 0
    except Exception: stars=0
    survivors.append({**it,"issue":int(num),"stars":stars,"bounty_usd":amt,"gate":"passed (active+funded $%d, no-PR, USD-from-comment)"%amt})
json.dump({"survivors":survivors,"checked":len(items)}, open(gj,"w"), indent=2)
print(f"{len(survivors)}/{len(items)}")
PY
  local s; s=$([ -f "$gj" ] && "$PY" -c "import json;print(len(json.load(open('$gj')).get('survivors',[])))" 2>/dev/null || echo 0)
  echo "[bounty] gate: $s candidates passed (funder-active + no-open-PR) of top $n"
  emit "gate: $s attemptable bounties (state/gated.json). Brain then judges fix-not-blocked + agent-doable, picks ONE."
}

case "$EARN_MODE" in track) track ;; gate) gate ;; attempt) attempt ;; *) discover ;; esac
exit 0
