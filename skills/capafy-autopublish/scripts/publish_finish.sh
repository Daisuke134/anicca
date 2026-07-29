#!/usr/bin/env bash
# publish_finish.sh — DETERMINISTIC second half of a Capafy publish, run AFTER the
# agent has driven CP1 (Agent-Card save) to isConfirmedSkills=1.
#   verify-CP1 -> configure -> CP2(key host) -> ship -> CP3(submit) -> verify -> ledger
# Fail-closed: refuses to start unless isConfirmedSkills=1; exits 0 only if the final
# remote-status is status=1 (under review) AND isConfirmedConfigKeys=1.
#
# Usage: publish_finish.sh <agent-id> <skill-name> [LISTING.md]
set -uo pipefail

ID="${1:?agent-id required}"
SKILL_NAME="${2:?skill-name required}"
LISTING="${3:-}"

AUTO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PUB="$AUTO/vendor/capafy-publisher"
LIFE_MANAGER_STATE_HOME="${LIFE_MANAGER_STATE_HOME:-$HOME/.local/state/life-manager}"
VENV="${CAPAFY_BROWSER_PYTHON:-python3}"
cd "$PUB" || { echo "❌ cd PUB"; exit 1; }

step(){ echo ""; echo "━━━ $* ━━━"; }
die(){ echo "❌ $*"; exit 1; }

# 2026-07-18 A1: fail-closed key-health gate. A submit/resubmit into an under-funded
# OpenRouter account is what triggered the "billing error" review rejections. Refuse to
# proceed unless the host key has balance AND a live sonnet-4.6 probe returns 200.
"$AUTO/scripts/key_health_gate.sh" 2.00 || die "KEY-HEALTH gate FAIL — top up OpenRouter (>= \$2 remaining) before (re)submitting; see state/lessons.md"
# strict=False: remote-status JSON embeds raw newlines in the description field
# ("Invalid control character" would otherwise crash json.load -> empty gate -> false die).
rstat(){ python3 packager.py publish-remote-status --agent-id "$ID" 2>/dev/null | python3 -c "import json,sys
try: print(json.loads(sys.stdin.read(),strict=False).get('latest_version',{}).get('$1'))
except Exception: print('')"; }
refresh(){ python3 packager.py publish-refresh-url --agent-id "$ID" --step "$1" 2>/dev/null | python3 -c "import json,sys
try: print(json.loads(sys.stdin.read(),strict=False).get('review_url',''))
except Exception: print('')"; }
# poll a remote-status field until it reaches <want> (server is eventually-consistent:
# a browser save lands a few seconds AFTER the toast/URL flips, so a ONE-SHOT read of a
# stale value is a false negative — that race is what stalled the loop). $2=field $3=want.
poll(){ local field="$1" want="$2" tries="${3:-15}" slp="${4:-5}" i v
  for ((i=0;i<tries;i++)); do v="$(rstat "$field")"; [ "$v" = "$want" ] && { echo "$field=$v (${i}x)"; return 0; }; sleep "$slp"; done
  echo "$field=$v (want $want, gave up ${tries}x${slp}s)"; return 1; }

step "[2b] verify CP1 (fail-closed, polled)"
# Short poll (not one-shot): the agentic CP1 save may still be registering server-side.
poll isConfirmedSkills 1 6 5 || die "CP1 not confirmed (isConfirmedSkills!=1) — drive CP1 agentically first (CP1_AGENTIC.md)"
echo "isConfirmedSkills=1 ✓"

# configure + CP2 are idempotent-skippable: if the key is already hosted (cfg=1),
# re-running drive_checkpoint2 risks dirtying a good card — skip straight through.
if [ "$(rstat isConfirmedConfigKeys)" = "1" ]; then
  echo "isConfirmedConfigKeys=1 already ✓ — skip configure+CP2"
else
  step "[3] configure (deep-scan, empty findings)"
  chmod -R u+w "$PUB/.temp/staging" 2>/dev/null; rm -rf "$PUB/.temp/staging" 2>/dev/null
  python3 packager.py publish-configure --agent-id "$ID" --deep-scan >/dev/null 2>&1
  python3 -c "import json;json.dump({'generic':[],'env_var':[]},open('.temp/dsf.json','w'))"
  python3 packager.py publish-configure --agent-id "$ID" --deep-scan-findings-file "$PUB/.temp/dsf.json" >/dev/null 2>&1
  echo "configured"

  step "[4] CP2 key host (drive_checkpoint2.py)"
  export CAPAFY_HOST_OPENROUTER_KEY="${CAPAFY_HOST_OPENROUTER_KEY:-$(grep '^CAPAFY_HOST_OPENROUTER_KEY=' "$LIFE_MANAGER_STATE_HOME/.env" 2>/dev/null | cut -d= -f2-)}"
  CP2="$(refresh configure)"
  timeout 150 "$VENV" "$AUTO/scripts/drive_checkpoint2.py" "$CP2" 2>&1 | grep -vE "Deprecation|warnings.warn" | tail -4
  # AUTHORITATIVE gate = server isConfirmedConfigKeys, POLLED. drive_checkpoint2 can
  # exit just before the server registers the hosted key -> a one-shot read false-dies.
  poll isConfirmedConfigKeys 1 12 5 || die "CP2 key host NOT confirmed (isConfirmedConfigKeys!=1) — drive CP2 agentically (PUBLISHING_RUNBOOK.md)"
  echo "isConfirmedConfigKeys=1 ✓"
fi

# ship + CP3 are skipped if the agent is ALREADY submitted (status=1) — makes a
# re-run idempotent (resume a half-done agent without double-submitting).
if [ "$(rstat status)" = "1" ]; then
  echo "status=1 already ✓ — already submitted, skip ship+CP3"
else
  step "[5] ship"
  SHIP_OUT="$(python3 packager.py publish-ship --agent-id "$ID" 2>&1)"
  if echo "$SHIP_OUT" | grep -q '"ok": true\|shipped'; then echo "shipped"; else
    # ONLY the specific "already uploaded for this local publish work-state" error is
    # benign (idempotent re-run of a ship that already matched this agent_id). Any
    # other error (e.g. "agent_id does not match local publish work-state") means the
    # local work-state points at a DIFFERENT agent and this ship was a silent no-op —
    # treating it as benign resubmits STALE content under a false "shipped" status
    # (bit us 2026-07-17: resubmitted a rejected package unchanged). Fail closed.
    if echo "$SHIP_OUT" | grep -q "already uploaded the package for this local publish work-state"; then
      PKG="$(rstat packageUrl)"
      [ -n "$PKG" ] && [ "$PKG" != "None" ] && echo "ship: package already present ($PKG)" || die "ship failed: $SHIP_OUT"
    else
      die "ship failed: $SHIP_OUT"
    fi
  fi

  step "[6] CP3 submit (審査に提出) — retry until server status=1"
  for attempt in 1 2 3; do
    [ "$(rstat status)" = "1" ] && break
    echo "CP3 submit attempt $attempt"
    CP3="$(refresh ship)"
    EDITURL="$CP3" timeout 95 "$VENV" - <<'PY' 2>&1 | grep -vE "Deprecation|warnings.warn" | tail -3
import time,os,urllib.request
from playwright.sync_api import sync_playwright
def _detect_cdp():
    override=os.environ.get("CP1_CDP_URL")
    if override: return override
    for port in (9222,9223):
        url=f"http://localhost:{port}"
        try:
            with urllib.request.urlopen(f"{url}/json/version", timeout=2) as r:
                if r.status==200: return url
        except Exception: continue
    return "http://localhost:9222"
pw=sync_playwright().start(); br=pw.chromium.connect_over_cdp(_detect_cdp())
caps=[p for c in br.contexts for p in c.pages if 'capafy.ai' in (p.url or '')]
pg=caps[-1] if caps else br.contexts[0].new_page()
pg.bring_to_front(); pg.goto(os.environ["EDITURL"], wait_until="networkidle", timeout=60000); time.sleep(7)
r=pg.evaluate("""()=>{const c=[...document.querySelectorAll('button')].filter(e=>/審査に提出|提出$/i.test((e.textContent||'').trim())&&(e.textContent||'').length<16&&!e.disabled);if(c.length){const b=c[c.length-1];b.scrollIntoView();const r=b.getBoundingClientRect();return{x:r.x+r.width/2,y:r.y+r.height/2};}return null;}""")
if r: pg.mouse.click(r['x'],r['y']); print("審査に提出"); time.sleep(3)
m=pg.evaluate("""()=>{const b=[...document.querySelectorAll('button')].find(e=>/提出を確認|Confirm|確定/.test((e.textContent||'').trim())&&e.offsetParent&&e.getBoundingClientRect().width<340);if(b){b.click();return 'confirmed';}return 'no-modal';}""")
print("confirm:",m); time.sleep(4)
PY
    poll status 1 6 5 && break
  done
fi

step "[7] FINAL VERIFY (remote-status, polled)"
poll status 1 6 5 >/dev/null || true
python3 packager.py publish-remote-status --agent-id "$ID" 2>/dev/null | python3 -c "
import json,sys
v=json.loads(sys.stdin.read(),strict=False).get('latest_version',{})
st=v.get('status'); cfg=v.get('isConfirmedConfigKeys'); sk=v.get('isConfirmedSkills'); au=v.get('auditStatus')
print(f'status={st} skills={sk} cfg={cfg} audit={au} title={str(v.get(\"title\"))[:42]}')
sys.exit(0 if (st==1 and cfg==1) else 1)
" || die "FINAL VERIFY failed (status/cfg not 1) for agent $ID"

step "[8] ledger"
python3 - "$ID" "$SKILL_NAME" "$LISTING" <<'PY'
import json,sys
aid,sn,listing=sys.argv[1],sys.argv[2],sys.argv[3]
title=sn
try:
    for ln in open(listing):
        if ln.strip().startswith('## Title'): continue
    # best-effort title from LISTING
    lines=[l.strip() for l in open(listing)]
    if '## Title' in lines:
        i=lines.index('## Title'); title=lines[i+1] if i+1<len(lines) else sn
except Exception: pass
ledger="../../state/published.jsonl"
# dedup: resuming an already-ledgered agent must not append a duplicate row
import os
if os.path.exists(ledger) and any(('"agent_id":"%s"'%aid) in l or ('"agent_id": "%s"'%aid) in l for l in open(ledger)):
    print("ledger already has", aid, "— not duplicating")
else:
    open(ledger,"a").write(json.dumps({
     "agent_id":aid,"skill":sn,"title":title,
     "status":"submitted (status=1 under review) — agentic CP1","date":__import__("datetime").date.today().isoformat()
    },ensure_ascii=False)+"\n")
    print("ledger appended", aid)
PY
echo ""
echo "✅ PUBLISHED + VERIFIED: agent_id=$ID ($SKILL_NAME) — status=1 under review."
