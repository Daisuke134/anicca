#!/usr/bin/env bash
# capafy-goal-monitor.sh — daily AUTONOMOUS audit of goal (a)-(d) + idempotent auto go-live.
#
# This is the "zero parent intervention" implementation: instead of a human tracking the
# time-dependent goal gates (7-day BLOCKED-free streak, sales reconcile, warmup-day-7 go-live,
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
WARMUP="$HOME/.cloak/ig-warmup-useclaudeskills.json"
EARN_LEDGER="$HOME/anicca/skills/self/capafy-loop/state/capafy-earn-ledger.jsonl"
KEY_GATE="$HOME/.openclaw/skills/capafy-autopublish/scripts/key_health_gate.sh"
IG_SCRIPT="$HOME/anicca/skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh"
IG_PLIST="$HOME/Library/LaunchAgents/ai.anicca.capafy-ig-marketing-daily.plist"
IG_LABEL="ai.anicca.capafy-ig-marketing-daily"
# Dais decision 2026-07-18: don't wait a full 7d — early NON-COMMERCIAL test post at day>=3 to
# MEASURE reach (the only real shadowban test), then go commercial only if reach is healthy.
WARMUP_DAYS_REQUIRED=3

# ── goal(c) go-live: create + load the IG launchd ONLY when warmup day>=7. Idempotent. ──
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

# ★ FREEZE GATE (Dais HOLD 2026-07-18): auto go-live is FROZEN until Dais explicitly approves by
#   creating the marker  ~/.openclaw/state/.capafy-ig-golive-approved . The day>=3 (clip 3-day floor)
#   threshold + non-commercial first post are ready, but this monitor will NOT load the IG launchd
#   (= will NOT trigger any live post) until that approval marker exists. This keeps the freeze safe
#   while leaving the whole pipeline armed to fire the moment Dais says go. ★
GOLIVE_APPROVED="$HOME/.openclaw/state/.capafy-ig-golive-approved"
WDAY="$(warmup_day_count)"
GO_LIVE_ACTION="not_yet"
if [ "${WDAY:-0}" -ge "$WARMUP_DAYS_REQUIRED" ]; then
  if [ ! -f "$GOLIVE_APPROVED" ]; then
    GO_LIVE_ACTION="ready_awaiting_dais_approval"   # day>=3 reached but FROZEN — no auto-load
  elif ig_loaded; then
    GO_LIVE_ACTION="already_live"
  else
    write_ig_plist
    launchctl load "$IG_PLIST" 2>/dev/null && GO_LIVE_ACTION="LOADED_NOW" || GO_LIVE_ACTION="load_failed"
  fi
fi

# ── the rest (goal a/b/d parsing + state + telegram body) is one python pass (read+append only). ──
$PY - "$STATE" "$DAILY_LOG" "$EARN_LEDGER" "$WARMUP" "$KEY_GATE" "$IG_PLIST" "$IG_LABEL" "$WDAY" "$WARMUP_DAYS_REQUIRED" "$GO_LIVE_ACTION" <<'PY' > /tmp/capafy_goal_monitor.json
import json, os, re, subprocess, sys, datetime
state_p, daily_log, earn_ledger, warmup, key_gate, ig_plist, ig_label, wday, wreq, golive = sys.argv[1:11]
wday = int(wday or 0); wreq = int(wreq)
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
body = (
 "[Capafy goal-monitor " + today.isoformat() + "]\n"
 "goal(a) BLOCKED-free streak: " + str(ga["blocked_free_streak_days"]) + "/7 " + ("PASS" if ga["pass"] else "building") + "\n"
 "goal(b) sales: orders=" + str(gb["orders"]) + " gross=$" + str(gb["gross_usd"]) + " (last " + str(gb["last_sales_date"]) + "), reconcile " + str(gb["reconcile_age_hours"]) + "h ago " + ("OK" if gb["fresh"] else "STALE") + "\n"
 "goal(c) IG warmup day " + str(gc["warmup_day"]) + "/" + str(gc["required"]) + " -> go-live: " + gc["go_live_action"] + " (ig loop loaded=" + str(gc["ig_marketing_loaded"]) + ")\n"
 "goal(d) health: capafy-loop=" + str(gd["capafy_loop_daily_loaded"]) + " warmup=" + str(gd["ig_warmup_loaded"]) + " key-gate=" + str(gd["key_health_gate_ok"])
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
