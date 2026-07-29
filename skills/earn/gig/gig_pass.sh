#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
# gig_pass.sh — ONE gig pass as a deterministic prompt-chain (Anthropic best practice: workflows give
# predictability for well-defined multi-step tasks; a single 20KB agent prompt drops steps). Each step is
# a SEPARATE bounded claude sub-call with a short focused prompt, so no step is skipped and every
# component gets iterated every pass. Deterministic bookkeeping (passprep/funnel/verify/locks) is plain
# code. State passes between steps through the ~/gig/*.jsonl files (structured note-taking).
#
# Called every hour by the cron/tmux core instead of the monolithic prompt.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
B="$LIFE_MANAGER_REPO/skills/browser/scripts"; G="$LIFE_MANAGER_REPO/skills/earn/gig"
CLAUDE="$(command -v claude || echo "$HOME/.local/bin/claude")"
RB="$LIFE_MANAGER_REPO/skills/earn/gig/GIG_PASS_RUNBOOK.md"
log(){ echo "$(date '+%F %T') gig_pass: $*" >&2; }

# focused sub-call: run ONE step as its own agent. Short prompt + a pointer to the runbook for detail.
# env -u ANTHROPIC_API_KEY = subscription login (no interactive key prompt). Bounded so it cannot hang forever.
step(){ # $1=label  $2=prompt
  log "STEP $1 start"
  CLAUDE_CODE_SKIP_PROMPT_HISTORY=1 env -u ANTHROPIC_API_KEY timeout 900 "$CLAUDE" --model sonnet --dangerously-skip-permissions --no-session-persistence --add-dir "$HOME" \
    -p "You are the Anicca Coconala gig earn-core (mtdc). set -a; . $HOME/.local/state/life-manager/.env; set +a. Your CDP browser-context lease is named '$GIG_LEASE' (use EXACTLY that name for any cdp_context_lease.py acquire/release the runbook calls for; this pass owns it, never acquire/release the bare name gig). Do EXACTLY this ONE step, fully, then stop. Detail/rules are in $RB. $2" >/dev/null 2>&1
  log "STEP $1 done (rc=$?)"
}

# ── deterministic prelude ───────────────────────────────────────────────────
LOCKD=/tmp/anicca-gig-pass.lock.d
GIG_LEASE="gig-$$"; export GIG_LEASE   # per-pass lease name, NOT the shared "gig": the EXIT trap releases ONLY this pass's own context, so an interrupt/overlap of one pass never tears down another pass's (or another loop's) browser context. Sub-agent steps inherit GIG_LEASE (env + injected into their prompt) and reuse the same lease.
[ -d "$LOCKD" ] && [ $(( $(date +%s) - $(stat -f %m "$LOCKD" 2>/dev/null||echo 0) )) -gt 7200 ] && rmdir "$LOCKD" 2>/dev/null   # reap a crashed holder (>120min). 7200s (was 1800s): detached passes now survive well past the old 30min window (B1/PROFILE can run ~90min), so a 30min reaper would rmdir a LIVE pass's lock and let the next hourly tick start a 2nd concurrent pass -> duplicate real-market applications. 120min > worst-case pass.
mkdir "$LOCKD" 2>/dev/null || { log "another pass holds the lock — exit"; exit 0; }   # mkdir = atomic on macOS; only ONE gig_pass.sh runs
trap 'rmdir "$LOCKD" 2>/dev/null; python3 "$B/cdp_context_lease.py" release "$GIG_LEASE" >/dev/null 2>&1' EXIT
bash "$LIFE_MANAGER_REPO/skills/browser/ensure_browser.sh" >/dev/null 2>&1
python3 "$B/cdp_tab_gc.py" >/dev/null 2>&1
python3 "$B/session_vault.py" restore >/dev/null 2>&1
PREP=$(python3 "$G/passprep.py" 2>/dev/null); log "passprep: ${PREP:0:120}"
python3 "$B/cdp_context_lease.py" gc --idle-min 45 >/dev/null 2>&1   # reap per-pass leases a crashed/killed prior pass left behind (per-pass names would otherwise pile up in leases.json)
python3 "$B/cdp_context_lease.py" acquire "$GIG_LEASE" >/dev/null 2>&1

# ── the chain: every step runs, in order, as its own bounded agent ──────────
step "LEARN"   "STEP 0.5 LEARN: first read the LAST line of ~/gig/reflection.jsonl (the previous pass verbal reflection — what was tried and what to adjust) and let it steer this pass. Then read ~/gig/.selfimprove-todo.json and do any 'missing' steps. Then crwl a best-practice source + scout.py 2-3 TOP-SELLING listings in a target category, extract the generalized winning patterns and MERGE them into ~/gig/playbook.json (general[]+components{}; 3+ winners => tier=core)."
step "B0"      "B0 SHUPPIN: STOREFRONT/seller pages (services_lists, services/add, service edit) MUST be driven in the PERSISTENT DEFAULT browser context, NOT the gig lease — the incognito lease (cookie-only seed) is 302-redirected to /login by Coconala's seller area, while the default context carries the full authenticated session. Get a default-context tab with: python3 $LIFE_MANAGER_REPO/skills/browser/scripts/cdp_default_tab.py open <url> (drive the returned ws; NEVER navigate a tab you did not open; close each tab you opened with cdp_default_tab.py close <target_id> when done). open coconala.com/mypage/services_lists. ITERATE EXISTING first — for the WEAKEST 0-sale listing, fix its full component set toward the winners in playbook.json (title, 3-plan price, 文字入れ thumbnail image = generate+upload, 1000字 description). Then add a new listing if <6 published. Append each action (one compact json line) to ~/gig/shuppin.jsonl."
step "PROFILE" "B4-PROFILE: mypage/profile is a seller area that the gig lease is also 302'd on — drive it in the PERSISTENT DEFAULT context via python3 $LIFE_MANAGER_REPO/skills/browser/scripts/cdp_default_tab.py open <url> (drive the returned ws, close it with cdp_default_tab.py close <target_id> when done), NOT the lease. open coconala.com/mypage/profile. Pick the WEAKEST un-touched profile component vs the winners (default icon / short 自己紹介 / no キャッチコピー / no portfolio) and fix ONE via CDP (for the icon, generate+upload a PNG). Record it in ~/gig/strategy.json experiments."
step "B1"      "B1 NURTURE ALL: sweep every open talk-room at coconala.com/mypage/messages. Reply to new buyer messages; if 仮払い arrived, build the real deliverable and 納品; if 検収 ready, ask for 評価. FOLLOW-UP: any 応募 with a reply but no 仮払い after ~24h gets ONE polite value-adding follow-up. Ground purchase status ONLY on the real トークルーム system message. Append actions to ~/gig/applied.jsonl."
step "B2"      "B2 APPLY BROADLY — the funnel needs volume, do NOT stop at 0. Target up to 12 new applications this pass. Start at sort=new (掲載30分以内 non-saturated preferred); if fewer than 12 fresh exist, BROADEN to more categories/keywords (AI活用/資料作成/ライティング/翻訳/文字起こし/LP制作/SNS運用/WordPress) and older-but-still-open non-saturated 公開依頼 until you reach 12 or genuinely exhaust the board. For EACH, record BOTH the 相場/market price on the page AND your offered price (cold-start: offer ~80%% of 相場 + a reason). Append ONE COMPACT single-line json per apply to ~/gig/applied.jsonl {ts:integer,title,category,status:applied,market_price_jpy,price_jpy,requestId} — ts MUST be an integer not a string — and a map row to ~/loops/gig/state/task-request-map.jsonl. If truly exhausted, say so honestly."

# ── deterministic bookkeeping + close ───────────────────────────────────────
python3 "$G/gig_funnel.py" "$(date +%s)" >/dev/null 2>&1   # EARNED CHECK + FUNNEL (deterministic, exit 0 always)
python3 "$B/cdp_tab_gc.py" >/dev/null 2>&1
touch "$HOME/gig/.last-pass"
# self-report (so the verifier can compare claims to file evidence)
python3 - <<PYEOF 2>/dev/null || true
import json,time
open("$HOME/gig/pass-report.jsonl","a").write(json.dumps({"ts":int(time.time()),"driver":"gig_pass.sh","steps":["LEARN","B0","PROFILE","B1","B2","FUNNEL"]},ensure_ascii=False)+"\n")
PYEOF
step "REFLECT" "REFLECTION (Reflexion verbal reinforcement): read the last 2 rows of ~/gig/gig-funnel.jsonl (this pass vs previous) and tail -5 ~/gig/pass-report.jsonl. In ONE compact json line append to ~/gig/reflection.jsonl: {ts, tried:<what you changed this pass>, funnel_moved:<applied/replied/won/paid delta or flat>, next:<the single most promising thing to try next pass>}. Be concrete and honest; if nothing moved, say so and pick a different lever."
bash "$G/scripts/gig_selfimprove_verify.sh" >/dev/null 2>&1   # write next-pass todo from real evidence
log "pass complete"
