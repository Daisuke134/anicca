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

# ── DETERMINISTIC CADENCE GATE: 1 X thread/day. If a platform=x entry already exists for
#    today (Asia/Tokyo), no-op and exit (never double-post the shared @aniccaen account). ──
TODAY="$(TZ=Asia/Tokyo date '+%Y-%m-%d')"
if [ -f "$ROT" ] && /opt/homebrew/bin/python3 - "$ROT" "$TODAY" <<'PY'
import json,sys,datetime
rot,today=sys.argv[1],sys.argv[2]
for line in open(rot):
    line=line.strip()
    if not line: continue
    try: r=json.loads(line)
    except: continue
    if r.get("platform")=="x" and r.get("ts"):
        d=datetime.datetime.fromtimestamp(r["ts"],datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d")
        if d==today:
            sys.exit(0)   # already posted today -> gate closes
sys.exit(1)
PY
then
  echo "cadence gate: already posted an X thread today ($TODAY) — no-op." >>"$LOG"
  touch "$HOME/.openclaw/state/.capafy-x-marketing-last-pass" 2>/dev/null || true
  exit 0
fi

PROMPT='You are the Anicca Capafy X-marketing loop (headless, self-improving; goal = drive Capafy skill subscribers, revenue → Dais bank; human NOT in this loop). This pass was triggered by a real launchd daily schedule (ai.anicca.capafy-x-marketing-daily) — do NOT self-register any cron. You post ONE promo thread today to X account @aniccaen (phase 1; it is already logged in on the CloakBrowser daily-driver :9222). The bash caller already enforced the 1-thread/day gate, so you WILL post this pass unless a real blocker appears.

CADENCE CHECK (do first, agent judgment): open https://x.com/aniccaen via ~/.agents/skills/ig-account-create/scripts/cdp.py (new tab, read-only) and look at the most recent post time. article-daily posts at 06:00 JST; you run at 15:00 JST. If — and only if — @aniccaen posted something within the LAST ~2 HOURS, DEFER this pass (report a no-op and finish cleanly; do not post on top of a just-published article). Otherwise proceed.

STEP1 SELECT (deterministic tool): run  python3 ~/anicca/skills/earn/capafy-marketing/scripts/select_listing.py  — it returns ONE online Capafy listing {agent_id,name,desc,url} with rotation/dedup. Use exactly that listing.

STEP2 COPY (YOUR judgment — never a template): from the listing name+desc, WRITE a native X tweet (value-first, <=280 chars, NO link, no "excited to announce" slop — lead with the problem the skill kills, then what it does) and a short reply CTA line. The link goes ONLY in the reply (x tanks link-in-body). Use only facts from the desc; invent no stats.

STEP3 POST (deterministic tool):  python3 ~/anicca/skills/earn/capafy-marketing/scripts/x_post_browser.py --url "<the url>" --tweet "<your native tweet>" --reply "Try the skill here:" --live  — it drives compose (root no-link + reply with the UTM-tagged url), posts as @aniccaen, and prints JSON with root_url + reply_url. It appends the ledger and records the post time in the rotation state. If it returns ok:false, do NOT retry-spam — read the error, fix the input if it is a copy problem (link in native / >280), otherwise report the failure and stop.

STEP4 VERIFY (logged-out, MANDATORY — a claim is not proof): from the reply_url open the tweet, grab its t.co link, and  curl -s -o /dev/null -w "%{url_effective} %{http_code}" -L "<t.co>"  with NO auth — confirm it resolves to a capafy.ai URL carrying utm_medium=x_reply and HTTP 200. If it does not resolve to capafy with the UTM, report FAILURE (the link did not land).

STEP5 REPORT (MANDATORY, success or failure): openclaw message send --channel telegram --target 0000000000 --message "<one-screen honest report: listing name, root_url, reply_url, the logged-out resolved capafy url + http code, and online-listing count>" --json  — confirm it returns a real message id; also run  bash ~/anicca/skills/report/loop-report.sh capafy-x-marketing "<what you posted + verified link>" <success|failure|no-op> 0 "<reply_url or none>"  if that script exists. Never inflate: there is no revenue number here yet, only reach.

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
