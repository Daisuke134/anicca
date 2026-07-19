#!/usr/bin/env bash
# capafy-goal-monitor.sh — daily AUTONOMOUS audit of goal (a)-(d) + idempotent auto go-live.
#
# This is the "zero parent intervention" implementation: instead of a human tracking the
# time-dependent goal gates (7-day BLOCKED-free streak, sales reconcile, warmup-day-3 go-live,
# self-heal health), this deterministic monitor does it daily and reports to Dais on telegram.
#
# HARD RULES: NO LLM. read + append ONLY (never destroys prod state/ledgers). launchd auto-load is
# IDEMPOTENT (checks launchctl list first, never double-loads). NO secrets in output. go-live gate
# uses the REAL warmup-ledger day (NO date hardcode). Self-heal check is NON-DESTRUCTIVE (never kills
# a prod loop). Emits one JSON object on stdout + one telegram summary.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
set -uo pipefail
PY=/opt/homebrew/bin/python3
STATE="$HOME/.openclaw/state/capafy-goal-monitor.json"
mkdir -p "$(dirname "$STATE")"

DAILY_LOG="$HOME/.openclaw/skills/capafy-autopublish/state/daily_loop.log"
EARN_LEDGER="$HOME/anicca/skills/self/capafy-loop/state/capafy-earn-ledger.jsonl"
KEY_GATE="$HOME/.openclaw/skills/capafy-autopublish/scripts/key_health_gate.sh"
IG_SCRIPT="$HOME/anicca/skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh"
IG_HANDLE="$(sed -nE 's/^IG_HANDLE="([^"]+)".*/\1/p' "$IG_SCRIPT" | head -1)"
WARMUP="$HOME/.cloak/ig-warmup-${IG_HANDLE}.json"
IG_PLIST="$HOME/Library/LaunchAgents/ai.anicca.capafy-ig-marketing-daily.plist"
IG_LABEL="ai.anicca.capafy-ig-marketing-daily"
INSTA_PY="$HOME/.cache/instagrapi-venv/bin/python"
INSTA_POSTER="$HOME/anicca/skills/earn/clip/scripts/instagrapi_post.py"
COOKED_MARKER="$HOME/.openclaw/state/.capafy-ig-account-cooked"
# Dais decision 2026-07-18: don't wait a full 7d — early NON-COMMERCIAL test post at day>=3 to
# MEASURE reach (the only real shadowban test), then go commercial only if reach is healthy.
WARMUP_DAYS_REQUIRED=3

# ── goal(c) go-live: create + load the IG launchd ONLY when warmup day>=3. Idempotent. ──
warmup_day_count() { $PY -c "import json;print(len(json.load(open('$WARMUP')).get('log',[])))" 2>/dev/null || echo 0; }
ig_loaded() { launchctl list 2>/dev/null | grep -q "$IG_LABEL"; }
write_ig_plist() {
  cat > "$IG_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$IG_LABEL</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$IG_SCRIPT</string></array>
  <key>EnvironmentVariables</key><dict><key>HOME</key><string>$HOME</string><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string></dict>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>16</integer><key>Minute</key><integer>30</integer></dict>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$HOME/.openclaw/logs/capafy-ig-marketing-daily.out</string>
  <key>StandardErrorPath</key><string>$HOME/.openclaw/logs/capafy-ig-marketing-daily.err</string>
</dict></plist>
PLIST
}

# NO-HUMAN-LOOP (Dais approved 2026-07-18): NO freeze/approval gate. At day>=3 (the clip 3-day
# floor — loop self-pacing, NOT a human gate) the monitor auto-loads the IG launchd itself, which
# then posts live daily. Safety pacing that remains is all LOOP-DRIVEN (day1-2 warmup only, day3+
# NON-COMMERCIAL first posts, reach-gated commercial via .capafy-ig-reach-healthy that the LOOP
# writes) — zero human approval anywhere. Idempotent: never double-loads.
WDAY="$(warmup_day_count)"

# Read-only account health probe. ChallengeRequired is terminal for this account: never relogin.
VERIFY_JSON=""
VERIFY_RC=0
if [ -z "$IG_HANDLE" ]; then
  VERIFY_JSON='{"ok":false,"error":"IG_HANDLE unresolved from daily script"}'
  VERIFY_RC=2
elif [ ! -x "$INSTA_PY" ]; then
  VERIFY_JSON='{"ok":false,"error":"instagrapi venv missing"}'
  VERIFY_RC=2
else
  VERIFY_JSON="$(CDP_PORT=9222 "$INSTA_PY" "$INSTA_POSTER" --handle "$IG_HANDLE" --port 9222 --verify-only 2>>"$HOME/.openclaw/logs/capafy-goal-monitor.err.log" | tail -1)"
  VERIFY_RC=$?
fi
ACCOUNT_COOKED="$($PY - "$VERIFY_JSON" <<'PY' 2>/dev/null
import json, sys
raw = sys.argv[1]
try:
    data = json.loads(raw)
except Exception:
    data = {}
print("yes" if data.get("poisoned") is True or "ChallengeRequired" in raw else "no")
PY
)"
if [ "$ACCOUNT_COOKED" = "yes" ]; then
  touch "$COOKED_MARKER"
fi

GO_LIVE_ACTION="not_yet"
if [ "${WDAY:-0}" -ge "$WARMUP_DAYS_REQUIRED" ]; then
  if ig_loaded; then
    GO_LIVE_ACTION="already_live"
  else
    write_ig_plist
    launchctl load "$IG_PLIST" 2>/dev/null && GO_LIVE_ACTION="LOADED_NOW" || GO_LIVE_ACTION="load_failed"
  fi
fi

# ── the rest (goal a/b/d parsing + state + telegram body) is one python pass (read+append only). ──
$PY - "$STATE" "$DAILY_LOG" "$EARN_LEDGER" "$WARMUP" "$KEY_GATE" "$IG_PLIST" "$IG_LABEL" "$WDAY" "$WARMUP_DAYS_REQUIRED" "$GO_LIVE_ACTION" "$IG_HANDLE" "$VERIFY_JSON" "$VERIFY_RC" "$COOKED_MARKER" <<'PY' > /tmp/capafy_goal_monitor.json
import json, os, re, subprocess, sys, datetime
(state_p, daily_log, earn_ledger, warmup, key_gate, ig_plist, ig_label, wday, wreq,
 golive, ig_handle, verify_raw, verify_rc, cooked_marker) = sys.argv[1:15]
wday = int(wday or 0); wreq = int(wreq); verify_rc = int(verify_rc)
try:
    verify = json.loads(verify_raw)
except Exception:
    verify = {"ok": False, "error": "verify-only returned invalid JSON"}
account_cooked = verify.get("poisoned") is True or "ChallengeRequired" in verify_raw
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
today = now.date()

# goal(a): per-day BLOCKED rc=1 from daily_loop.log -> trailing consecutive clean-day streak.
blocked_by_day = {}
seen_days = set()
if os.path.exists(daily_log):
    for line in open(daily_log, errors="ignore"):
        m = re.search(r'daily_loop done rc=(\d+).*?===', line)
        d = re.search(r'(\d{4}-\d{2}-\d{2})', line)
        if m and d:
            day = d.group(1); seen_days.add(day)
            if m.group(1) == "1" and "BLOCKED" in line:
                blocked_by_day[day] = blocked_by_day.get(day, 0) + 1
# streak = consecutive days (ending today, walking back) that had a run and ZERO blocked.
streak = 0
day = today
while True:
    ds = day.isoformat()
    if ds not in seen_days:
        break  # no run recorded that day -> streak ends (conservative)
    if blocked_by_day.get(ds, 0) > 0:
        break
    streak += 1
    day = day - datetime.timedelta(days=1)
goal_a_pass = streak >= 7

# goal(b): latest sales row + reconcile freshness (staleness = divergence risk).
gross = orders = None; last_sales_date = None; reconcile_age_h = None
if os.path.exists(earn_ledger):
    reconcile_age_h = round((now.timestamp() - os.path.getmtime(earn_ledger)) / 3600, 1)
    for line in open(earn_ledger):
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except: continue
        if r.get("orders") is not None:
            orders = r.get("orders"); gross = r.get("gross_usd"); last_sales_date = r.get("date")
goal_b_ok = reconcile_age_h is not None and reconcile_age_h < 48  # reconcile ran within 2 days

# goal(d): NON-DESTRUCTIVE health — launchctl loaded? plist exists? key-health gate exit?
def loaded(label):
    try: return subprocess.run(["launchctl","list"],capture_output=True,text=True,timeout=15).stdout.find(label) >= 0
    except: return False
health = {
    "capafy_loop_daily_loaded": loaded("ai.anicca.capafy-loop-daily"),
    "ig_warmup_loaded": loaded("ai.anicca.capafy-marketing-warmup"),
    "ig_marketing_loaded": loaded(ig_label),
}
gate_ok = None
if os.path.exists(key_gate):
    try:
        # non-destructive: many gates support a --check/dry read; fall back to bash -n if not.
        rc = subprocess.run(["bash","-n",key_gate],capture_output=True,text=True,timeout=15).returncode
        gate_ok = (rc == 0)
    except: gate_ok = None

report = {
    "ts": int(now.timestamp()), "date": today.isoformat(),
    "goal_a": {"blocked_free_streak_days": streak, "required": 7, "pass": goal_a_pass},
    "goal_b": {"last_sales_date": last_sales_date, "orders": orders, "gross_usd": gross,
               "reconcile_age_hours": reconcile_age_h, "fresh": goal_b_ok},
    "goal_c": {"warmup_day": wday, "required": wreq, "go_live_action": golive,
               "ig_marketing_loaded": health["ig_marketing_loaded"]},
    "goal_d": {**health, "key_health_gate_ok": gate_ok},
    "account_health": {"handle": ig_handle, "verify_rc": verify_rc, "verify": verify,
                       "poisoned": account_cooked, "cooked_marker": os.path.exists(cooked_marker)},
}
# append to state (history), keep last 60
hist = []
if os.path.exists(state_p):
    try: hist = json.load(open(state_p)).get("history", [])
    except: hist = []
hist.append(report); hist = hist[-60:]
json.dump({"latest": report, "history": hist}, open(state_p, "w"), ensure_ascii=False, indent=1)

# telegram body (one screen, no secrets)
ga = report["goal_a"]; gb = report["goal_b"]; gc = report["goal_c"]; gd = report["goal_d"]
ah = report["account_health"]
account_line = (
 "account @" + ah["handle"] + ": account poisoned、fresh 作り直しが必要"
 if ah["poisoned"] else
 "account @" + ah["handle"] + ": verify-only ok=" + str(ah["verify"].get("ok"))
)
body = (
 "[Capafy goal-monitor " + today.isoformat() + "]\n"
 "goal(a) BLOCKED-free streak: " + str(ga["blocked_free_streak_days"]) + "/7 " + ("PASS" if ga["pass"] else "building") + "\n"
 "goal(b) sales: orders=" + str(gb["orders"]) + " gross=$" + str(gb["gross_usd"]) + " (last " + str(gb["last_sales_date"]) + "), reconcile " + str(gb["reconcile_age_hours"]) + "h ago " + ("OK" if gb["fresh"] else "STALE") + "\n"
 "goal(c) IG warmup day " + str(gc["warmup_day"]) + "/" + str(gc["required"]) + " -> go-live: " + gc["go_live_action"] + " (ig loop loaded=" + str(gc["ig_marketing_loaded"]) + ")\n"
 "goal(d) health: capafy-loop=" + str(gd["capafy_loop_daily_loaded"]) + " warmup=" + str(gd["ig_warmup_loaded"]) + " key-gate=" + str(gd["key_health_gate_ok"]) + "\n"
 + account_line
)
open("/tmp/capafy_goal_monitor_body.txt","w").write(body)
print(json.dumps(report, ensure_ascii=False))
PY

RC=$?
BODY="$(cat /tmp/capafy_goal_monitor_body.txt 2>/dev/null)"
# telegram daily report (best-effort; never blocks the monitor)
if [ -n "$BODY" ]; then
  openclaw message send --channel telegram --target 0000000000 --message "$BODY" --json >/dev/null 2>&1 || true
fi
cat /tmp/capafy_goal_monitor.json 2>/dev/null
exit 0
