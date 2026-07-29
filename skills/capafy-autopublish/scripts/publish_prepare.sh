#!/usr/bin/env bash
# publish_prepare.sh — DETERMINISTIC first half of a Capafy publish.
#   lint -> clean-WS copy -> publish-init -> build edit URL -> print target pricing.
# After this, the AGENT drives CP1 (Agent-Card save) AGENTICALLY via cp1_agent.py
# (look at screenshots, fix the pricing plan cards, save) until the server shows
# isConfirmedSkills=1 — see CP1_AGENTIC.md. Then run publish_finish.sh <agent-id>.
#
# WHY split: the old monolithic drive_cp1.py hardcoded DOM coordinates/positions and
# silently broke when Capafy changed the pricing widget (plan cards re-sort on period
# change -> positional price/cap writes get scrambled -> price tab red -> card never
# saves -> isConfirmedSkills=0 -> loop STOP). Per "build agents, don't hardcode", the
# card-save step is now agent-driven, not a brittle script.
#
# Usage: publish_prepare.sh <skill-dir> <LISTING.md> <icon.png>
# Prints (machine-greppable):  AGENT_ID=<id>  EDIT_URL=<url>  then the target pricing.
set -uo pipefail

SKILL_DIR="${1:?skill-dir required}"
LISTING="${2:?LISTING.md required}"
ICON="${3:?icon path required}"

AUTO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PUB="$AUTO/vendor/capafy-publisher"
LIFE_MANAGER_STATE_HOME="${LIFE_MANAGER_STATE_HOME:-$HOME/.local/state/life-manager}"
VENV="${CAPAFY_BROWSER_PYTHON:-python3}"
WS="${CAPAFY_WORKSPACE:-$LIFE_MANAGER_STATE_HOME/work/capafy}"
SKILL_NAME="$(basename "$SKILL_DIR")"

step(){ echo ""; echo "━━━ $* ━━━"; }
die(){ echo "❌ $*"; exit 1; }

step "[0] LINT $LISTING"
python3 "$AUTO/scripts/lint_listing.py" "$LISTING" || die "lint FAIL — fix the listing first"
[ -f "$ICON" ] || die "icon not found: $ICON"
[ -d "$SKILL_DIR" ] || die "skill dir not found: $SKILL_DIR"

step "[0b] KEY-HEALTH GATE (fail-closed) — never publish into an under-funded host key"
# 2026-07-18 A1: 4 agents were rejected with a billing error caused by a THIN OpenRouter
# balance (NOT a stale key / NOT the provider-name label). Block the publish here so the
# loop stops cleanly instead of shipping into a $-low account and getting re-rejected.
"$AUTO/scripts/key_health_gate.sh" 2.00 || die "KEY-HEALTH gate FAIL — top up OpenRouter (>= \$2 remaining) before publishing; see state/lessons.md"

step "clean-WS copy"
rm -rf "$WS/skills/$SKILL_NAME" 2>/dev/null
cp -R "$SKILL_DIR" "$WS/skills/$SKILL_NAME" || die "clean-WS copy failed"

step "[1] publish-init"
cd "$PUB" || die "cd PUB"
TITLE="$(grep -A1 '^## Title' "$LISTING" | tail -1)"
# write selections via python (heredoc redirects can be blocked by the sandbox)
"$VENV" - "$TITLE" "$SKILL_NAME" <<'PY'
import json,sys,os
title,sn=sys.argv[1],sys.argv[2]
os.makedirs(".temp",exist_ok=True)
json.dump({"title":title,"description":title,
  "skills":[{"path":f".openclaw/skills/{sn}","name":sn,"purpose":sn}],
  "plugins":[],"crons":[]}, open(".temp/sel_one.json","w"), ensure_ascii=False)
PY
# RESUME GUARD: every failed run used to publish-init a NEW draft, so failures piled
# up orphan drafts that eat the 5-slot cap until the loop hard-blocks. Reuse an
# EXACT-title agent that already exists (the "(LM generated…)" auto-stub has a suffix
# so it is NOT matched). draft -> resume its CP1; under_review/online -> already done.
ID="$(python3 packager.py publish-list 2>/dev/null | TITLE="$TITLE" python3 -c "
import json,os,sys
want=os.environ['TITLE'].strip()
try: lst=json.loads(sys.stdin.read(),strict=False)['agents']['list']
except Exception: sys.exit(0)
rank={'online':3,'approved':3,'under_review':2,'draft':1}; best=None
for a in lst:
  if (a.get('name') or '').strip()==want:
    r=rank.get(a.get('agentStatus'),0)
    if not best or r>best[0]: best=(r,a.get('agentId'),a.get('agentStatus'))
if best: print(best[1])
")"
if [ -n "$ID" ]; then
  echo "RESUME existing agent_id=$ID (title match) — not creating a new draft"
  # BUG FIX 2026-07-17: this branch used to skip publish-init entirely, leaving the
  # LOCAL publish work-state (.temp/publish-work-state.json) pointed at whatever
  # agent_id a PRIOR run last touched. publish-ship then failed closed with
  # "agent_id does not match local publish work-state" — but publish_finish.sh's ship
  # fallback (now also fixed) treated that failure as benign and resubmitted STALE
  # content unchanged. Rebind local state to THIS agent_id now. If the agent is
  # currently under_review (not editable), this call fails — that's fine, it means
  # there is no fixed content to ship yet; ship will correctly refuse later instead
  # of silently no-op'ing.
  python3 packager.py publish-init --env openclaw --runtime-dir "$WS" --skill-dir "$WS/skills/$SKILL_NAME" --agent-id "$ID" --selections-file "$PUB/.temp/sel_one.json" >/dev/null 2>&1 \
    && echo "local publish work-state rebound to agent_id=$ID" \
    || echo "WARN: could not rebind local publish work-state to $ID (agent likely under_review, not editable) — publish_finish.sh ship step will fail closed rather than resubmit stale content"
else
  ID="$(python3 packager.py publish-init --env openclaw --runtime-dir "$WS" --skill-dir "$WS/skills/$SKILL_NAME" --selections-file "$PUB/.temp/sel_one.json" 2>&1 | python3 -c "import json,sys
try: print(json.loads(sys.stdin.read()).get('agent_id',''))
except: print('')")"
  [ -n "$ID" ] || die "publish-init returned no agent_id (dup title? cap full = 5 unlisted max? see publish-list)"
fi

RAW="$(python3 packager.py publish-refresh-url --agent-id "$ID" --step init 2>/dev/null)"
TOK="$(echo "$RAW" | python3 -c "import json,sys;print(json.load(sys.stdin).get('review_url',''))" | grep -oE '[0-9]{15,}' | head -1)"
EDIT="https://capafy.ai/developer/createAgent?source=temp-link&token=${TOK}&page=edit"
python3 "$AUTO/scripts/build_config.py" "$LISTING" "$ICON" "$EDIT" "$PUB/.temp/cfg_one.json" >/dev/null 2>&1 || die "build_config failed"

step "PREPARE DONE — hand off to agentic CP1"
echo "AGENT_ID=$ID"
echo "EDIT_URL=$EDIT"
echo ""
echo "TARGET PRICING (drive each plan card to these EXACT values on the 価格設定 tab):"
python3 - "$PUB/.temp/cfg_one.json" <<'PY'
import json,sys
c=json.load(open(sys.argv[1]))
for p in c["plans"]:
    tr = p.get("trial")
    print(f"  {p['cycle']:5} : price ${p['price']}  cap {p['cap']}  trial={'No Free Trial' if not tr else str(tr)+'h'}")
print("  category:", c.get("category"), "| model:", c.get("model"))
PY
echo ""
echo "NEXT: drive CP1 agentically (CP1_AGENTIC.md), then: publish_finish.sh $ID"
