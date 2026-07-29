#!/usr/bin/env bash
# publish_one.sh — LEGACY monolithic Capafy publish. The CP1 step uses the old
# drive_cp1.py, which hardcodes DOM coordinates and BREAKS on Capafy pricing-UI
# changes (plan cards re-sort on period change → positional price/cap writes get
# scrambled → price tab red → isConfirmedSkills=0 → STOP). 2026-07-05.
#   ★ PREFER the agentic flow: publish_prepare.sh → agentic CP1 (CP1_AGENTIC.md /
#     cp1_agent.py, YOUR eyes on screenshots) → publish_finish.sh. See DAILY_LOOP.md. ★
# This file is kept for reference / the deterministic non-CP1 steps only.
#   lint → init → CP1(browser) → configure → CP2(browser) → ship → CP3(browser) → remote verify → ledger
#
# Usage:
#   publish_one.sh <skill-dir> <LISTING.md> <icon.png>
# Env:
#   VCSDD=1   also require a manual VCSDD adversary PASS BEFORE running (you spawn it; this only reminds)
# Exit: 0 only if remote-status shows status=1 (under review) AND isConfirmedConfigKeys=1.
set -uo pipefail

SKILL_DIR="${1:?skill-dir required}"
LISTING="${2:?LISTING.md required}"
ICON="${3:?icon path required}"

# A4: self-locating from the canonical repository.
AUTO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PUB="$AUTO/vendor/capafy-publisher"               # A3: vendored Capafy CLI (self-contained tree)
LIFE_MANAGER_STATE_HOME="${LIFE_MANAGER_STATE_HOME:-$HOME/.local/state/life-manager}"
VENV="${CAPAFY_BROWSER_PYTHON:-python3}"
WS="${CAPAFY_WORKSPACE:-$LIFE_MANAGER_STATE_HOME/work/capafy}"
SKILL_NAME="$(basename "$SKILL_DIR")"

step(){ echo ""; echo "━━━ $* ━━━"; }
die(){ echo "❌ $*"; exit 1; }

# ── [0] LINT (rejection-proof, fail-closed) ────────────────────────────────
step "[0] LINT $LISTING"
python3 "$AUTO/scripts/lint_listing.py" "$LISTING" || die "lint FAIL — fix the listing before publishing"

[ -f "$ICON" ] || die "icon not found: $ICON"
[ -d "$SKILL_DIR" ] || die "skill dir not found: $SKILL_DIR"

# ── leak guard: copy ONLY the skill into the clean workspace ────────────────
step "clean-WS copy"
rm -rf "$WS/skills/$SKILL_NAME" 2>/dev/null
cp -R "$SKILL_DIR" "$WS/skills/$SKILL_NAME" || die "clean-WS copy failed"

# ── [1] publish-init (new agent, claims a slot) ────────────────────────────
step "[1] publish-init"
cd "$PUB" || die "cd PUB"
TITLE="$(grep -A1 '^## Title' "$LISTING" | tail -1)"
cat > "$PUB/.temp/sel_one.json" <<JSON
{"title":"${TITLE//\"/}","description":"${TITLE//\"/}","skills":[{"path":".openclaw/skills/$SKILL_NAME","name":"$SKILL_NAME","purpose":"$SKILL_NAME"}],"plugins":[],"crons":[]}
JSON
ID="$(python3 packager.py publish-init --env openclaw --runtime-dir "$WS" --skill-dir "$WS/skills/$SKILL_NAME" --selections-file "$PUB/.temp/sel_one.json" 2>&1 | python3 -c "import json,sys
try: print(json.loads(sys.stdin.read()).get('agent_id',''))
except: print('')")"
[ -n "$ID" ] || die "publish-init returned no agent_id (cap full? = 5 unlisted max)"
echo "agent_id=$ID"

refresh(){ python3 packager.py publish-refresh-url --agent-id "$ID" --step "$1" 2>/dev/null | python3 -c "import json,sys;print(json.load(sys.stdin).get('review_url',''))"; }

# ── [2] CP1 (browser, all 15 gotchas + price-tab GREEN self-verify) ────────
step "[2] CP1 drive_cp1.py"
RAW="$(refresh init)"; TOK="$(echo "$RAW" | grep -oE '[0-9]{15,}' | head -1)"
EDIT="https://capafy.ai/developer/createAgent?source=temp-link&token=${TOK}&page=edit"
python3 "$AUTO/scripts/build_config.py" "$LISTING" "$ICON" "$EDIT" "$PUB/.temp/cfg_one.json" || die "build_config failed"
timeout 280 "$VENV" "$AUTO/scripts/drive_cp1.py" "$PUB/.temp/cfg_one.json" 2>&1 | grep -vE "Deprecation|warnings.warn" | tail -3
SKILLS="$(python3 packager.py publish-remote-status --agent-id "$ID" 2>/dev/null | python3 -c "import json,sys;print(json.load(sys.stdin).get('latest_version',{}).get('isConfirmedSkills'))")"
[ "$SKILLS" = "1" ] || die "CP1 did not confirm skills (isConfirmedSkills=$SKILLS) — card not saved"
echo "CP1 OK (skills=1)"

# ── [3] configure (deep-scan, empty findings) ──────────────────────────────
step "[3] configure"
chmod -R u+w "$PUB/.temp/staging" 2>/dev/null; rm -rf "$PUB/.temp/staging" 2>/dev/null
python3 packager.py publish-configure --agent-id "$ID" --deep-scan >/dev/null 2>&1
echo '{"generic": [], "env_var": []}' > "$PUB/.temp/dsf.json"
python3 packager.py publish-configure --agent-id "$ID" --deep-scan-findings-file "$PUB/.temp/dsf.json" >/dev/null 2>&1

# ── [4] CP2 (browser, OpenRouter Claude key host + VERIFY) ──────────────────
step "[4] CP2 drive_checkpoint2.py"
export CAPAFY_HOST_OPENROUTER_KEY="${CAPAFY_HOST_OPENROUTER_KEY:-$(grep '^CAPAFY_HOST_OPENROUTER_KEY=' "$LIFE_MANAGER_STATE_HOME/.env" 2>/dev/null | cut -d= -f2-)}"
CP2="$(refresh configure)"
R2="$(timeout 130 "$VENV" "$AUTO/scripts/drive_checkpoint2.py" "$CP2" 2>&1 | grep -E 'RESULT' | tail -1)"
echo "$R2"
echo "$R2" | grep -q "VERIFIED" || die "CP2 key host NOT verified ($R2)"

# ── [5] ship + [6] CP3 (browser submit) ────────────────────────────────────
step "[5] ship + [6] CP3 submit"
python3 packager.py publish-ship --agent-id "$ID" >/dev/null 2>&1
CP3="$(refresh ship)"
EDITURL="$CP3" timeout 95 "$VENV" - <<'PY' 2>&1 | grep -vE "Deprecation|warnings.warn" | tail -2
import time,os
from playwright.sync_api import sync_playwright
pw=sync_playwright().start(); br=pw.chromium.connect_over_cdp("http://localhost:9222"); ctx=br.contexts[0]
pg=ctx.new_page(); pg.bring_to_front(); pg.goto(os.environ["EDITURL"], wait_until="networkidle", timeout=60000); time.sleep(7)
r=pg.evaluate("""()=>{const c=[...document.querySelectorAll('button')].filter(e=>/審査に提出|提出$/i.test((e.textContent||'').trim())&&(e.textContent||'').length<16&&!e.disabled);if(c.length){const b=c[c.length-1];b.scrollIntoView();const r=b.getBoundingClientRect();return{x:r.x+r.width/2,y:r.y+r.height/2};}return null;}""")
if r: pg.mouse.click(r['x'],r['y']); print("審査に提出"); time.sleep(3)
m=pg.evaluate("""()=>{const b=[...document.querySelectorAll('button')].find(e=>/提出を確認|Confirm|確定/.test((e.textContent||'').trim())&&e.offsetParent&&e.getBoundingClientRect().width<320);if(b){b.click();return 'confirmed';}return 'no-modal';}""")
print("confirm:",m); time.sleep(4)
PY

# ── [7] FINAL VERIFY (remote-status real data) ─────────────────────────────
step "[7] FINAL VERIFY (remote-status)"
V="$(python3 packager.py publish-remote-status --agent-id "$ID" 2>/dev/null)"
echo "$V" | python3 -c "
import json,sys
v=json.load(sys.stdin).get('latest_version',{})
st=v.get('status'); cfg=v.get('isConfirmedConfigKeys'); at=v.get('agentType'); md=v.get('model'); ti=str(v.get('title'))[:42]
print(f'status={st} cfg={cfg} type={at} model={md} title={ti}')
sys.exit(0 if (st==1 and cfg==1) else 1)
" || die "FINAL VERIFY failed (status/cfg not 1) for agent $ID"

# ── [8] ledger ─────────────────────────────────────────────────────────────
echo "{\"agent_id\":\"$ID\",\"skill\":\"$SKILL_NAME\",\"listing\":\"$LISTING\",\"status\":\"submitted status=1\"}" >> "$AUTO/state/published.jsonl"
echo ""
echo "✅ PUBLISHED + VERIFIED: agent_id=$ID ($SKILL_NAME) — status=1 under review."
echo "   (Do the browser render check yourself, then commit+push the ledger.)"
