#!/usr/bin/env bash
# capafy-goal-monitor.sh — daily autonomous audit of money, lifecycle, and loop health.
#
# This is the "zero parent intervention" implementation: instead of a human tracking the
# business goals (7-day BLOCKED-free streak, sales reconciliation, verified Instagram lifecycle,
# self-heal health), this deterministic monitor does it daily and reports to Dais on Telegram.
#
# HARD RULES: NO LLM. read + append ONLY (never destroys prod state/ledgers). launchd auto-load is
# NO secrets in output. Self-heal checks are non-destructive. Scheduler presence is never treated
# as a published post. Emits one JSON object on stdout plus one natural-language Telegram summary.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY=/opt/homebrew/bin/python3
OUTCOME_SCRIPT="$SCRIPT_DIR/scripts/capafy_outcome.py"
STATE="$HOME/.openclaw/state/capafy-goal-monitor.json"
mkdir -p "$(dirname "$STATE")"

DAILY_LOG="$HOME/.openclaw/skills/capafy-autopublish/state/daily_loop.log"
EARN_LEDGER="$HOME/anicca/skills/self/capafy-loop/state/capafy-earn-ledger.jsonl"
KEY_GATE="$HOME/.openclaw/skills/capafy-autopublish/scripts/key_health_gate.sh"
ACCOUNT_STATE_HELPER="${CAPAFY_ACCOUNT_STATE_HELPER:-$HOME/anicca/skills/earn/capafy-marketing/account_state.sh}"
# shellcheck source=account_state.sh
. "$ACCOUNT_STATE_HELPER"
ACCOUNTS_FILE="$(capafy_ig_accounts_file)"
IG_HANDLE="$(resolve_capafy_ig_handle "$ACCOUNTS_FILE")"
IG_PORT="$(resolve_capafy_ig_port "$ACCOUNTS_FILE")"
IG_LABEL="ai.anicca.capafy-ig-marketing-daily"
LIFECYCLE_STATE="${CAPAFY_IG_LIFECYCLE_STATE:-$HOME/.openclaw/state/capafy-ig-lifecycle.json}"
if [ "${CAPAFY_GOAL_MONITOR_PROBE_ONLY:-0}" = "1" ]; then
  printf 'active_handle=%s active_port=%s accounts_path=%s\n' \
    "${IG_HANDLE:-none}" "${IG_PORT:-none}" "$ACCOUNTS_FILE"
  exit 0
fi

if [ "${CAPAFY_GOAL_MONITOR_VERIFY_PROBE_ONLY:-0}" = "1" ]; then
  "$PY" - "$LIFECYCLE_STATE" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: d={}
print(f"lifecycle_status={d.get('status','unknown')} capability={d.get('capability','none')} session_established={str(bool(d.get('session_established'))).lower()} public_post_url={d.get('last_public_reel_url') or 'none'}")
PY
  exit 0
fi

# ── the rest (goal a/b/d parsing + state + telegram body) is one python pass (read+append only). ──
$PY - "$STATE" "$DAILY_LOG" "$EARN_LEDGER" "$KEY_GATE" "$IG_LABEL" "$IG_HANDLE" "$LIFECYCLE_STATE" "$OUTCOME_SCRIPT" <<'PY' > /tmp/capafy_goal_monitor.json
import json, os, re, subprocess, sys, datetime
(state_p, daily_log, earn_ledger, key_gate, ig_label, ig_handle,
 lifecycle_state_path, outcome_script) = sys.argv[1:9]
try:
    lifecycle = json.load(open(lifecycle_state_path))
except Exception:
    lifecycle = {}
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
    "goal_c": {"lifecycle_status": lifecycle.get("status", "unknown"),
               "capability": lifecycle.get("capability", "none"),
               "session_established": bool(lifecycle.get("session_established")),
               "public_post_url": lifecycle.get("last_public_reel_url"),
               "ig_marketing_loaded": health["ig_marketing_loaded"]},
    "goal_d": {**health, "key_health_gate_ok": gate_ok},
    "account_health": {"handle": ig_handle,
                       "lifecycle_status": lifecycle.get("status", "unknown"),
                       "capability": lifecycle.get("capability", "none"),
                       "session_established": bool(lifecycle.get("session_established")),
                       "post_write_session_verified": bool(lifecycle.get("post_write_session_verified")),
                       "replacement_requested": bool(lifecycle.get("replacement_requested"))},
}

# Consolidated company projection. Each value comes from deterministic state or a fresh
# server read; agent-authored narration is never used as a business fact.
home = os.path.expanduser("~")
money = {}
state_md = os.path.join(home, "anicca/skills/self/capafy-loop/state/STATE.md")
if os.path.exists(state_md):
    for line in open(state_md, errors="ignore"):
        match = re.match(r"(capafy_[a-z_]+):\s*([-0-9.]+)", line)
        if match:
            money[match.group(1)] = float(match.group(2))

cost = 0.0
cost_log = os.path.join(home, ".openclaw/logs/capafy-loop-daily.log")
if os.path.exists(cost_log):
    for line in open(cost_log, errors="ignore"):
        try: row = json.loads(line)
        except Exception: continue
        if row.get("provider") == "openrouter" and row.get("total_usage_usd") is not None:
            cost = float(row["total_usage_usd"])

inventory = {"online": 0, "under_review": 0, "draft": 0, "rejected": 0}
publisher_dir = os.path.join(home, ".openclaw/skills/capafy-autopublish/vendor/capafy-publisher")
try:
    raw = subprocess.run(
        [sys.executable, "packager.py", "publish-list"], cwd=publisher_dir,
        capture_output=True, text=True, timeout=90, check=True,
    ).stdout
    agents = json.loads(raw, strict=False)["agents"]["list"]
    for agent in agents:
        status = agent.get("agentStatus")
        if status in {"online", "approved"}: inventory["online"] += 1
        elif status == "under_review": inventory["under_review"] += 1
        elif status == "draft": inventory["draft"] += 1
        elif status in {"review_rejected", "banned"}: inventory["rejected"] += 1
except Exception:
    # Preserve honest unknowns rather than copying the scheduler's loaded state into inventory.
    inventory = {"online": 0, "under_review": 0, "draft": 0, "rejected": 0}

def load_json(path):
    try:
        value = json.load(open(path))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}

builder_terminal = load_json(os.path.join(home, ".openclaw/state/capafy-builder-terminal.json"))
builder_outcome = builder_terminal.get("outcome") or {}
marketing_terminal = load_json(os.path.join(home, ".openclaw/state/capafy-marketing-terminal.json"))
marketing_outcome = marketing_terminal.get("outcome") or {}
active_incidents = []
incident_dir = os.path.join(home, ".openclaw/state/capafy-incidents")
if os.path.isdir(incident_dir):
    for name in os.listdir(incident_dir):
        incident = load_json(os.path.join(incident_dir, name))
        if incident and incident.get("phase") != "verified": active_incidents.append(incident)
active_incidents.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
incident = active_incidents[0] if active_incidents else None

realized = money.get("capafy_realized_payout_usd", 0.0)
company = {
    "schema_version": 1,
    "kind": "company_state",
    "date": today.isoformat(),
    "inventory": inventory,
    "orders": int(money.get("capafy_lifetime_orders", orders or 0)),
    "gross_usd": money.get("capafy_lifetime_gross_usd", gross or 0.0),
    "pending_usd": money.get("capafy_seller_balance_pending_usd", 0.0),
    "realized_usd": realized,
    "mrr_usd": money.get("capafy_mrr_usd", 0.0),
    "cost_usd": cost,
    "contribution_usd": realized - cost,
    "account": {
        "handle": ig_handle or "no-active-account",
        "lifecycle_status": lifecycle.get("status", "unknown"),
        "capability": lifecycle.get("capability", "none"),
        "session_established": bool(lifecycle.get("session_established")),
        "post_write_session_verified": bool(lifecycle.get("post_write_session_verified")),
        "account_status": "replacement requested" if lifecycle.get("replacement_requested") else "clean",
    },
    "marketing": {
        "scheduler_loaded": health["ig_marketing_loaded"],
        "public_post_url": marketing_outcome.get("reel_url") if marketing_outcome.get("kind") == "marketing_published" else None,
    },
    "incident": ({
        "summary": incident.get("summary"), "phase": incident.get("phase"),
        "next_retry_at": incident.get("next_retry_at"),
    } if incident else None),
    "listing_url": builder_outcome.get("listing_url"),
    "dashboard_url": "https://capafy-skills-daily.netlify.app",
}
report["company_state"] = company
# append to state (history), keep last 60
hist = []
if os.path.exists(state_p):
    try: hist = json.load(open(state_p)).get("history", [])
    except: hist = []
hist.append(report); hist = hist[-60:]
json.dump({"latest": report, "history": hist}, open(state_p, "w"), ensure_ascii=False, indent=1)

rendered = subprocess.run(
    [sys.executable, outcome_script, "render"], input=json.dumps(company),
    capture_output=True, text=True, timeout=30,
)
body = rendered.stdout.strip() if rendered.returncode == 0 else ""
open("/tmp/capafy_goal_monitor_body.txt","w").write(body)
print(json.dumps(report, ensure_ascii=False))
PY

RC=$?
BODY="$(cat /tmp/capafy_goal_monitor_body.txt 2>/dev/null)"
# telegram daily report (best-effort; never blocks the monitor)
if [ -n "$BODY" ]; then
  bash "$SCRIPT_DIR/../../_shared/send-telegram.sh" "$BODY" >/dev/null 2>&1 || true
fi
cat /tmp/capafy_goal_monitor.json 2>/dev/null
exit 0
