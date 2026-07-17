#!/usr/bin/env bash
# capafy-x-marketing-daily.sh — B8 — DETERMINISTIC daily trigger for the Capafy X marketing loop.
# launchd calls this once/day (ai.anicca.capafy-x-marketing-daily, 15:00 JST — spaced 9h from the
# 06:00 article-daily post on the SHARED @aniccaen account). Same pattern as capafy-loop-daily.sh:
# launchd -> this script -> headless `claude -p` that runs selector -> writes copy (agent judgment)
# -> x_post_browser.py --live -> logged-out verify -> ledger -> report. Copy is NEVER hardcoded here.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
set -uo pipefail
CLAUDE="$(command -v claude || echo "$HOME/.local/bin/claude")"
LOG="$HOME/.openclaw/logs/capafy-x-marketing-daily.log"
ROT="$HOME/.openclaw/state/capafy-marketing-rotation.jsonl"
mkdir -p "$(dirname "$LOG")" "$(dirname "$ROT")"
echo "=== capafy-x-marketing-daily run $(date '+%F %T %Z') ===" >>"$LOG"

# ── B6/B7 run EVERY day (deterministic, no agent judgment) so the time-series fills even on
#    cadence no-op days — metrics of already-posted threads keep growing, attribution keeps joining. ──
/opt/homebrew/bin/python3 ~/anicca/skills/earn/capafy-marketing/scripts/x_metrics.py >>"$LOG" 2>&1 || echo "x_metrics failed (non-fatal)" >>"$LOG"
/opt/homebrew/bin/python3 ~/anicca/skills/earn/capafy-marketing/scripts/x_attribution.py >>"$LOG" 2>&1 || echo "x_attribution failed (non-fatal)" >>"$LOG"

# ── HARD SAFETY GATE: never post from a Dais-PERSONAL X account. The loop may only post from
#    an AI-OWNED, AI-created account (like IG @useclaudeskills). @aniccaen / @diceai0 are Dais's
#    personal accounts — Dais revoked a Capafy post to @aniccaen on 2026-07-18. If the account
#    logged in on :9222 is one of those (or no AI-owned X account is configured), REFUSE to post. ──
AI_X_HANDLE="${CAPAFY_X_AI_HANDLE:-}"   # set this to the AI-owned X handle once it exists
ACTIVE_X="$(/opt/homebrew/bin/python3 ~/.agents/skills/ig-account-create/scripts/cdp.py new 'https://x.com/home' 2>/dev/null | tr -d '"' | { read t; sleep 5; /opt/homebrew/bin/python3 ~/.agents/skills/ig-account-create/scripts/cdp.py eval "$t" - <<'JS' 2>/dev/null
(()=>{const h=(document.body.innerText.match(/@[a-zA-Z0-9_]+/g)||[]);return (h.find(x=>/aniccaen|diceai0|aniccaxxx/i.test(x))||h[0]||'?');})()
JS
} | tr -d '"' )"
case "$ACTIVE_X" in
  *aniccaen*|*diceai0*|*aniccaxxx*)
    echo "SAFETY GATE: :9222 active X = $ACTIVE_X is a DAIS-PERSONAL account — REFUSING to post (loop needs an AI-owned X account, like @useclaudeskills for IG). No-op." >>"$LOG"
    touch "$HOME/.openclaw/state/.capafy-x-marketing-last-pass" 2>/dev/null || true
    exit 0 ;;
esac
if [ -z "$AI_X_HANDLE" ]; then
  echo "SAFETY GATE: no AI-owned X handle configured (CAPAFY_X_AI_HANDLE unset). Metrics ran above; skipping post. No-op." >>"$LOG"
  touch "$HOME/.openclaw/state/.capafy-x-marketing-last-pass" 2>/dev/null || true
  exit 0
fi

# ── DETERMINISTIC CADENCE GATE (clip pattern): no-op if the last X thread was < 20h ago.
#    A rolling 20h window (not a calendar day) prevents a 23:00 + next-06:00 double-post on the
#    SHARED @aniccaen account. Reads the most recent platform=x ts from the rotation ledger. ──
if [ -f "$ROT" ] && /opt/homebrew/bin/python3 - "$ROT" <<'PY'
import json,sys,time
rot=sys.argv[1]
last=0
for line in open(rot):
    line=line.strip()
    if not line: continue
    try: r=json.loads(line)
    except: continue
    if r.get("platform")=="x" and r.get("ts"):
        last=max(last,int(r["ts"]))
# gate CLOSES (exit 0) when the last X post was less than 20h (72000s) ago
sys.exit(0 if last and (time.time()-last) < 72000 else 1)
PY
then
  echo "cadence gate: last X thread < 20h ago — no-op (prevents @aniccaen double-post)." >>"$LOG"
  touch "$HOME/.openclaw/state/.capafy-x-marketing-last-pass" 2>/dev/null || true
  exit 0
fi

PROMPT='You are the Anicca Capafy X-marketing loop (headless, self-improving; goal = drive Capafy skill subscribers, revenue → Dais bank; human NOT in this loop). This pass was triggered by a real launchd daily schedule (ai.anicca.capafy-x-marketing-daily) — do NOT self-register any cron. You post ONE promo thread today to the AI-OWNED X account whose handle the bash caller passed as $AI_X_HANDLE (it is logged in on the CloakBrowser daily-driver :9222). ★NEVER post to a Dais-personal account (@aniccaen / @diceai0 / @aniccaxxx) — the bash caller already hard-refuses those; if you somehow see one of them as the active account, STOP and report, do not post.★ The bash caller already enforced the 1-thread/day + safety gates, so you WILL post this pass unless a real blocker appears.

CADENCE CHECK (do first, agent judgment): open https://x.com/$AI_X_HANDLE via ~/.agents/skills/ig-account-create/scripts/cdp.py (new tab, read-only) and look at the most recent post time. If it posted something within the LAST ~2 HOURS, DEFER this pass (report a no-op and finish cleanly; do not post on top of a just-published article). Otherwise proceed.

STEP1 SELECT (deterministic tool): run  python3 ~/anicca/skills/earn/capafy-marketing/scripts/select_listing.py  — it returns ONE online Capafy listing {agent_id,name,desc,url} with rotation/dedup. Use exactly that listing.

STEP2 COPY (YOUR judgment — never a template): from the listing name+desc, WRITE a native X tweet (value-first, <=280 chars, NO link, no "excited to announce" slop — lead with the problem the skill kills, then what it does) and a short reply CTA line. The link goes ONLY in the reply (x tanks link-in-body). Use only facts from the desc; invent no stats.

STEP3 POST (deterministic tool):  python3 ~/anicca/skills/earn/capafy-marketing/scripts/x_post_browser.py --url "<the url>" --tweet "<your native tweet>" --reply "Try the skill here:" --live  — it drives compose (root no-link + reply with the UTM-tagged url), posts as @aniccaen, and prints JSON with root_url + reply_url. It appends the ledger and records the post time in the rotation state. If it returns ok:false, do NOT retry-spam — read the error, fix the input if it is a copy problem (link in native / >280), otherwise report the failure and stop.

STEP4 VERIFY (logged-out, MANDATORY — a claim is not proof): from the reply_url open the tweet, grab its t.co link, and  curl -s -o /dev/null -w "%{url_effective} %{http_code}" -L "<t.co>"  with NO auth — confirm it resolves to a capafy.ai URL carrying utm_medium=x_reply and HTTP 200. If it does not resolve to capafy with the UTM, report FAILURE (the link did not land).

STEP5 REPORT (MANDATORY, success or failure): openclaw message send --channel telegram --target 0000000000 --message "<one-screen honest report: listing name, root_url, reply_url, the logged-out resolved capafy url + http code, and online-listing count>" --json  — confirm it returns a real message id; also run  bash ~/anicca/skills/report/loop-report.sh capafy-x-marketing "<what you posted + verified link>" <success|failure|no-op> 0 "<reply_url or none>"  if that script exists. Never inflate: there is no revenue number here yet, only reach.

STEP6 REFLECT (weekly learning line — the bash caller already refreshed capafy-marketing-metrics.jsonl + capafy-attribution.jsonl before you ran; SKELETON until data accrues): count distinct root_url in ~/.openclaw/state/capafy-marketing-metrics.jsonl. If FEWER than 7 distinct threads, this is a NO-OP — just note "reflect: insufficient data (<7 posts)" and move on. If 7+, compute the median views; for the threads whose latest views are >= the median, read their copy from the x-ledger and extract 1-2 concrete winning patterns (hook style / structure / the specific angle) and let them shape the copy you write in STEP2 next time (this is the clip REFLECT / above-average gate pattern; do not overfit to 1-2 samples). Never invent a pattern from thin data.

FINALLY always touch ~/.openclaw/state/.capafy-x-marketing-last-pass to prove the pass completed. A deferred cadence pass or a caught error is a clean finish, never a hang.'

# Headless auth via local CLIProxyAPI (:8317) — plain-file creds refresh headlessly (keychain is locked under launchd).
CLIPROXY_KEY="$(cat "$HOME/.cli-proxy-api-key" 2>/dev/null || true)"
if [ -n "$CLIPROXY_KEY" ]; then
  export ANTHROPIC_BASE_URL="http://127.0.0.1:8317"
  export ANTHROPIC_AUTH_TOKEN="$CLIPROXY_KEY"
fi

env -u ANTHROPIC_API_KEY "$CLAUDE" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" -p "$PROMPT" >>"$LOG" 2>&1
RC=$?
echo "=== capafy-x-marketing-daily done rc=$RC $(date '+%F %T %Z') ===" >>"$LOG"
touch "$HOME/.openclaw/state/.capafy-x-marketing-last-pass" 2>/dev/null || true
exit 0
