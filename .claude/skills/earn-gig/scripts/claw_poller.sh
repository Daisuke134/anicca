#!/usr/bin/env bash
# Claw Earn poller — watches the REAL-USDC bounty board. When a TAKE-able
# research/data/code bounty appears, mail Dais + log it (then the model acts).
# No tests, no dry-runs — only fires on a real posted paid request.
# Runs under launchd every ~10 min.
set -uo pipefail

SKILL="$HOME/.claude/skills/earn-gig"
PY="/opt/homebrew/bin/python3"
STATE="$SKILL/state"; mkdir -p "$STATE"
SEEN="$STATE/claw_seen_tasks.txt"; touch "$SEEN"
LOG="$STATE/poller.log"
ENV="$HOME/.openclaw/.env"

ts(){ date -u +%FT%TZ; }
log(){ echo "[$(ts)] $*" >> "$LOG"; }

# Pull open tasks (public, no auth). Print NEW take-able ones as JSON lines.
NEW=$("$PY" - <<'PY'
import json,urllib.request,os
SEEN=os.path.expanduser("~/.claude/skills/earn-gig/state/claw_seen_tasks.txt")
seen=set(l.strip() for l in open(SEEN) if l.strip())
SKIP=("link building","seo","backlink","guest post","listing","sales","referral")
try:
    d=json.loads(urllib.request.urlopen(urllib.request.Request("https://aiagentstore.ai/claw/tasks",headers={"User-Agent":"claw-poller"}),timeout=20).read())
except Exception as e:
    print("ERR:"+str(e)[:80]); raise SystemExit(0)
items=d.get("items",[]) if isinstance(d,dict) else []
out=[]
for t in items:
    tid=str(t.get("taskId",t.get("id","")))
    if not tid or tid in seen: continue
    cat=str(t.get("category","")).lower(); title=str(t.get("title","")).lower()
    likely_skip=any(s in cat or s in title for s in SKIP)
    rw=t.get("reward",t.get("amount",0))
    try: usd=int(rw)/1e6
    except: usd=rw
    out.append({"id":tid,"title":t.get("title"),"usd":usd,"category":t.get("category"),
                "contract":t.get("contractAddress"),"prescreen":"likely_skip" if likely_skip else "CANDIDATE"})
for o in out: print(json.dumps(o,ensure_ascii=False))
PY
)

if [ -z "$NEW" ]; then log "no new tasks (board empty or all seen)"; exit 0; fi

# Mark seen + mail Dais about CANDIDATE (take-able) ones
echo "$NEW" | while IFS= read -r line; do
  [ -z "$line" ] && continue
  TID=$(echo "$line" | "$PY" -c "import json,sys;print(json.load(sys.stdin)['id'])" 2>/dev/null) || continue
  echo "$TID" >> "$SEEN"
  log "NEW task: $line"
done

CANDS=$(echo "$NEW" | grep '"prescreen": "CANDIDATE"' || true)
if [ -n "$CANDS" ]; then
  log "CANDIDATE(s) found → mailing Dais"
  BODY="$STATE/poller_alert.txt"
  { echo "Claw Earn (real USDC) に no-human で取れそうな bounty が出ました:"; echo "";
    echo "$CANDS"; echo "";
    echo "次: claw_agent.py で stake → 実行 → submit → USDC 着金 (要 stake 資本)."; } > "$BODY"
  set -a; . "$ENV" 2>/dev/null; set +a
  gog gmail send --account keiodaisuke@gmail.com --to keiodaisuke@gmail.com \
    --subject "[earn-gig] ★ Claw Earn real bounty 出現 — no-human candidate ★" \
    --body-file "$BODY" >> "$LOG" 2>&1 && log "mail sent" || log "mail FAILED"
fi
