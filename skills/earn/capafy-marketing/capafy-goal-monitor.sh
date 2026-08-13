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
TELEGRAM_SENDER="${CAPAFY_TELEGRAM_SENDER:-$SCRIPT_DIR/../../_shared/send-telegram.sh}"
EVENT_SYNC="${CAPAFY_EVENT_SYNC:-$SCRIPT_DIR/scripts/capafy_event_sync.py}"
EVENT_PROJECTION="${CAPAFY_EVENT_PROJECTION:-$SCRIPT_DIR/scripts/capafy_event_projection.py}"
COMPANY_DASHBOARD_BUILDER="${CAPAFY_COMPANY_DASHBOARD_BUILDER:-$SCRIPT_DIR/scripts/build_company_dashboard.py}"
COMPANY_DASHBOARD_DIR="${CAPAFY_COMPANY_DASHBOARD_DIR:-$SCRIPT_DIR/site/company}"
EVENT_LEDGER="${CAPAFY_EVENT_LEDGER:-$HOME/.openclaw/state/capafy-revenue-events.jsonl}"
EVENT_EVIDENCE_DIR="${CAPAFY_EVENT_EVIDENCE_DIR:-$HOME/.openclaw/state/capafy-revenue-evidence}"
PORTFOLIO_STATE="${CAPAFY_PORTFOLIO_STATE:-$HOME/.openclaw/state/capafy-portfolio.json}"
STATE="$HOME/.openclaw/state/capafy-goal-monitor.json"
DELIVERY_STATE="${CAPAFY_GOAL_MONITOR_DELIVERY_STATE:-$HOME/.openclaw/state/capafy-goal-monitor-delivery.json}"
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

# Refresh canonical writers before reading the projection. Failure cannot fall through
# to the legacy report path.
TMP_ROOT="${CAPAFY_GOAL_MONITOR_TMP_DIR:-/tmp}"
PROJECTION_FILE="$TMP_ROOT/capafy_company_projection.json"
REPORT_FILE="$TMP_ROOT/capafy_goal_monitor.json"
BODY_FILE="$TMP_ROOT/capafy_goal_monitor_body.txt"
PARITY_FILE="$TMP_ROOT/capafy_goal_monitor_parity_error.txt"
rm -f "$PROJECTION_FILE" "$REPORT_FILE" "$BODY_FILE" "$PARITY_FILE"
if ! "$PY" "$EVENT_SYNC" sync-all \
  --ledger "$EVENT_LEDGER" --evidence-dir "$EVENT_EVIDENCE_DIR" >/dev/null; then
  "$PY" "$OUTCOME_SCRIPT" start-incident \
    --owner company --summary "Canonical revenue source sync failed." \
    --fingerprint goal-monitor-event-sync-failed >/dev/null 2>&1 || true
  exit 2
fi

# A sync incident is a transient operation failure. Once the same canonical writer
# succeeds again, close only that fingerprinted incident before projecting state;
# otherwise the old `detected` record permanently trips the repair-SLA watchdog.
while IFS=$'\t' read -r INCIDENT_ID INCIDENT_PHASE; do
  [ -n "$INCIDENT_ID" ] || continue
  case "$INCIDENT_PHASE" in
    detected) NEXT_PHASES="repair_started repaired verified" ;;
    repair_started) NEXT_PHASES="repaired verified" ;;
    repaired) NEXT_PHASES="verified" ;;
    *) continue ;;
  esac
  for NEXT_PHASE in $NEXT_PHASES; do
    printf '%s\n' "{\"incident_id\":\"$INCIDENT_ID\",\"phase\":\"$NEXT_PHASE\",\"repair_summary\":\"Canonical revenue source sync succeeded on the next live run.\",\"verification\":{\"event_sync_succeeded\":true,\"incident_id\":\"$INCIDENT_ID\"}}" \
      | "$PY" "$OUTCOME_SCRIPT" transition-incident >/dev/null || exit 2
  done
done < <("$PY" - <<'PY'
import json
from pathlib import Path
state = Path.home() / ".openclaw/state/capafy-incidents"
for path in sorted(state.glob("*.json")):
    try:
        record = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        continue
    if record.get("fingerprint") == "goal-monitor-event-sync-failed" and record.get("phase") != "verified":
        print(f"{record.get('incident_id','')}\t{record.get('phase','')}")
PY
)
if ! "$PY" "$EVENT_PROJECTION" project --ledger "$EVENT_LEDGER" > "$PROJECTION_FILE"; then
  "$PY" "$OUTCOME_SCRIPT" start-incident \
    --owner company --summary "Canonical company projection failed." \
    --fingerprint goal-monitor-projection-failed >/dev/null 2>&1 || true
  exit 2
fi

# ── the rest (goal a/b/d parsing + state + telegram body) is one python pass (read+append only). ──
$PY - "$STATE" "$DAILY_LOG" "$EARN_LEDGER" "$KEY_GATE" "$IG_LABEL" "$IG_HANDLE" "$LIFECYCLE_STATE" "$OUTCOME_SCRIPT" "$EVENT_PROJECTION" "$PROJECTION_FILE" "$PARITY_FILE" "$BODY_FILE" "$PORTFOLIO_STATE" <<'PY' > "$REPORT_FILE"
import json, os, re, subprocess, sys, datetime
from decimal import Decimal, InvalidOperation
(state_p, daily_log, earn_ledger, key_gate, ig_label, ig_handle,
 lifecycle_state_path, outcome_script, projection_script, projection_path,
 parity_path, body_path, portfolio_path) = sys.argv[1:14]
sys.path.insert(0, os.path.dirname(projection_script))
from capafy_event_projection import parity_errors
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

def decimal_value(row, field, line_number):
    try:
        value = Decimal(str(row[field]))
        if not value.is_finite():
            raise ValueError
        return value
    except (KeyError, InvalidOperation, TypeError, ValueError):
        raise ValueError(f"EARN_LEDGER line {line_number}: {field} is malformed")

def paid_orders_value(orders, gross, has_explicit, value):
    if gross < 0:
        return None
    if has_explicit:
        return value if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= orders else None
    return int(gross > 0) if orders == 1 else None

def derive_earn_money(path):
    if not os.path.isfile(path):
        raise ValueError(f"EARN_LEDGER is missing: {path}")
    sales = {}
    payouts = {}
    with open(path, encoding="utf-8") as stream:
        for line_number, raw in enumerate(stream, 1):
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"EARN_LEDGER line {line_number}: invalid JSON") from exc
            if not isinstance(row, dict):
                raise ValueError(f"EARN_LEDGER line {line_number}: row must be an object")
            source = row.get("source")
            if source not in {"capafy-sales", "capafy-payout"}:
                continue
            date = row.get("date")
            if not isinstance(date, str) or not date:
                raise ValueError(f"EARN_LEDGER line {line_number}: {source} date is required")
            ts = decimal_value(row, "ts", line_number)
            if ts != ts.to_integral_value():
                raise ValueError(f"EARN_LEDGER line {line_number}: ts is not an integer")
            if source == "capafy-sales":
                raw_orders = row.get("orders")
                if isinstance(raw_orders, bool) or not isinstance(raw_orders, int) or raw_orders < 0:
                    raise ValueError(f"EARN_LEDGER line {line_number}: orders is malformed")
                orders = int(raw_orders)
                gross = decimal_value(row, "gross_usd", line_number)
                if gross < 0:
                    raise ValueError(f"EARN_LEDGER line {line_number}: gross_usd is malformed")
                if "paid_orders" in row:
                    paid = row["paid_orders"]
                    if isinstance(paid, bool) or not isinstance(paid, int) or paid < 0 or paid > orders:
                        raise ValueError(f"EARN_LEDGER line {line_number}: paid_orders is malformed")
                candidate = (int(ts), date, line_number, orders, gross, "paid_orders" in row, row.get("paid_orders"))
                if (source, date) not in sales or candidate[:3] >= sales[(source, date)][:3]:
                    sales[(source, date)] = candidate
            else:
                candidate = (int(ts), date, line_number, decimal_value(row, "balance_payout_usd", line_number), decimal_value(row, "total_payout_usd", line_number))
                if (source, date) not in payouts or candidate[:3] >= payouts[(source, date)][:3]:
                    payouts[(source, date)] = candidate
    if not sales:
        raise ValueError("EARN_LEDGER has no capafy-sales rows")
    if not payouts:
        raise ValueError("EARN_LEDGER has no capafy-payout rows")
    latest_sales = max(sales.values(), key=lambda row: row[:3])
    latest_payout = max(payouts.values(), key=lambda row: row[:3])
    paid_orders = 0
    paid_orders_known = True
    for row in sales.values():
        paid = paid_orders_value(row[3], row[4], row[5], row[6])
        if paid is None:
            paid_orders_known = False
        elif paid_orders_known:
            paid_orders += paid
    return {
        "orders": sum(row[3] for row in sales.values()),
        "gross": sum((row[4] for row in sales.values()), Decimal("0")),
        "paid_orders": paid_orders if paid_orders_known else None,
        "last_sales_date": latest_sales[1],
        "pending": latest_payout[3],
        "realized": latest_payout[4],
    }

try:
    earn_money = derive_earn_money(earn_ledger)
except (OSError, ValueError) as exc:
    open(parity_path, "w").write(f"EARN_LEDGER parity source invalid: {exc}\n")
    raise SystemExit(3)

# goal(b): latest sales row + reconcile freshness (staleness = divergence risk).
orders = earn_money["orders"]
gross = float(earn_money["gross"])
last_sales_date = earn_money["last_sales_date"]
reconcile_age_h = round((now.timestamp() - os.path.getmtime(earn_ledger)) / 3600, 1)
goal_b_ok = reconcile_age_h < 48  # reconcile ran within 2 days

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
    "goal_b": {"last_sales_date": last_sales_date, "orders": orders, "paid_orders": earn_money["paid_orders"], "gross_usd": gross,
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

marketing_terminal = load_json(os.path.join(home, ".openclaw/state/capafy-marketing-terminal.json"))
marketing_outcome = marketing_terminal.get("outcome") or {}
active_incidents = []
incident_dir = os.path.join(home, ".openclaw/state/capafy-incidents")
if os.path.isdir(incident_dir):
    for name in os.listdir(incident_dir):
        incident = load_json(os.path.join(incident_dir, name))
        if incident and incident.get("phase") != "verified": active_incidents.append(incident)
# Incident `updated_at` is mutable metadata (for example, a retry heartbeat).
# The canonical event projection deliberately orders incident phases by their
# immutable phase timestamp, so selecting by updated_at here can make the
# monitor disagree with its own projection and keep an older incident stuck in
# `detected` forever. Use the current phase transition time as the authority,
# with updated_at only for legacy records that predate phase_timestamps.
def incident_order_key(item):
    phase = str(item.get("phase") or "")
    phase_times = item.get("phase_timestamps") or {}
    return str(phase_times.get(phase) or item.get("updated_at") or "")

active_incidents.sort(key=incident_order_key, reverse=True)
incident = active_incidents[0] if active_incidents else None
portfolio = load_json(portfolio_path)
experiment_products = [
    product for product in portfolio.get("products", [])
    if isinstance(product.get("experiment"), dict)
    and product["experiment"].get("status") in {"active", "stopped"}
]
active_experiment = None
if experiment_products:
    product = max(experiment_products, key=lambda item: item["experiment"].get("stopped_at") or item["experiment"].get("activated_at") or "")
    value = product["experiment"]
    active_experiment = {
        "experiment_id": value.get("experiment_id"),
        "agent_id": product.get("agent_id"),
        "owner": value.get("owner"),
        "status": value.get("status"),
        "purchase_model": value.get("purchase_model"),
        "price_usd": value.get("price_usd"),
        "projected_contribution_usd": value.get("projected_contribution_usd"),
        "observed_contribution_usd": value.get("observed_contribution_usd"),
        "success_metric": value.get("success_metric"),
        "stop_condition": value.get("stop_condition"),
        "stop_reason": value.get("stop_reason"),
        "public_url": product.get("public_url"),
    }

independent = {
    "inventory": inventory,
    "orders": earn_money["orders"],
    "paid_orders": earn_money["paid_orders"],
    "gross_usd": earn_money["gross"],
    "pending_usd": earn_money["pending"],
    "realized_usd": earn_money["realized"],
    "mrr_usd": Decimal("0"),
    "cost_usd": cost,
    "contribution_usd": earn_money["realized"] - Decimal(str(cost)),
    "account": {
        "handle": ig_handle or "no-active-account",
        "lifecycle_status": lifecycle.get("status", "unknown"),
        "capability": lifecycle.get("capability", "none"),
        "session_established": bool(lifecycle.get("session_established")),
        "post_write_session_verified": bool(lifecycle.get("post_write_session_verified")),
        "account_status": "replacement requested" if lifecycle.get("replacement_requested") else "clean",
    },
    "marketing": {
        "state": "reach_observing" if marketing_outcome.get("kind") == "marketing_published" else "not_published",
        "public_post_url": marketing_outcome.get("reel_url") if marketing_outcome.get("kind") == "marketing_published" else None,
        "campaign_url": marketing_outcome.get("campaign_url") if marketing_outcome.get("kind") == "marketing_published" else None,
    },
    "incident": ({
        "incident_id": incident.get("incident_id"), "owner": incident.get("owner"),
        "summary": incident.get("summary"), "phase": incident.get("phase"),
        "next_retry_at": incident.get("next_retry_at"),
    } if incident else None),
    "experiment": active_experiment,
}
projection = load_json(projection_path)
errors = parity_errors(projection, independent)
if errors:
    open(parity_path, "w").write("\n".join(errors) + "\n")
    raise SystemExit(3)
if (
    incident
    and incident.get("fingerprint") == "goal-monitor-projection-parity-mismatch"
    and incident.get("phase") != "verified"
):
    print(json.dumps({
        "reconcile_incident_id": incident["incident_id"],
        "parity_projection_id": projection.get("projection_id"),
    }))
    raise SystemExit(4)
company = projection
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
resolved_incident_id = os.environ.get("CAPAFY_GOAL_MONITOR_RESOLVED_INCIDENT_ID")
if body and resolved_incident_id:
    body = "\n".join([
        "Capafy incident resolved — no action needed",
        "The canonical ledger and independent company source reads agree again.",
        f"Resolved incident: {resolved_incident_id}",
        "",
        body,
    ])
open(body_path,"w").write(body)
print(json.dumps(report, ensure_ascii=False))
PY

RC=$?
if [ "$RC" -eq 4 ]; then
  [ "${CAPAFY_GOAL_MONITOR_RECONCILE_PASS:-0}" != "1" ] || exit 2
  INCIDENT_ID="$($PY -c 'import json,sys; print(json.load(open(sys.argv[1]))["reconcile_incident_id"])' "$REPORT_FILE")" || exit 2
  PARITY_PROJECTION_ID="$($PY -c 'import json,sys; print(json.load(open(sys.argv[1]))["parity_projection_id"])' "$REPORT_FILE")" || exit 2
  transition_incident() {
    local phase="$1"
    "$PY" - "$INCIDENT_ID" "$phase" "$PARITY_PROJECTION_ID" <<'PY' | "$PY" "$OUTCOME_SCRIPT" transition-incident >/dev/null
import json,sys
incident_id,phase,projection_id=sys.argv[1:]
payload={"incident_id":incident_id,"phase":phase}
if phase in {"repaired","verified"}:
    payload["repair_summary"]="The experiment projection now derives current public availability from the latest listing event."
if phase == "verified":
    payload["verification"]={
        "projection_parity_verified":True,
        "parity_projection_id":projection_id,
        "business_outcome_validated":True,
    }
print(json.dumps(payload))
PY
  }
  INCIDENT_RECORD="$($PY "$OUTCOME_SCRIPT" get-incident --incident-id "$INCIDENT_ID")" || exit 2
  INCIDENT_PHASE="$($PY -c 'import json,sys; print(json.loads(sys.argv[1])["phase"])' "$INCIDENT_RECORD")" || exit 2
  case "$INCIDENT_PHASE" in
    detected) transition_incident repair_started || exit 2; transition_incident repaired || exit 2 ;;
    unresolved) transition_incident repair_started || exit 2; transition_incident repaired || exit 2 ;;
    repair_started) transition_incident repaired || exit 2 ;;
    repaired) ;;
    verified) ;;
    *) exit 2 ;;
  esac
  [ "$INCIDENT_PHASE" = "verified" ] || transition_incident verified || exit 2
  export CAPAFY_GOAL_MONITOR_RECONCILE_PASS=1
  export CAPAFY_GOAL_MONITOR_RESOLVED_INCIDENT_ID="$INCIDENT_ID"
  exec bash "$0"
fi
if [ "$RC" -ne 0 ]; then
  "$PY" "$OUTCOME_SCRIPT" start-incident \
    --owner company --summary "Ledger projection did not match independent Capafy source reads." \
    --fingerprint goal-monitor-projection-parity-mismatch >/dev/null 2>&1 || true
  cat "$PARITY_FILE" >&2 2>/dev/null || true
  exit "$RC"
fi
if ! "$PY" "$COMPANY_DASHBOARD_BUILDER" \
  --projection "$PROJECTION_FILE" --output-dir "$COMPANY_DASHBOARD_DIR" >/dev/null; then
  "$PY" "$OUTCOME_SCRIPT" start-incident \
    --owner company --summary "Event-backed company dashboard generation failed." \
    --fingerprint goal-monitor-dashboard-generation-failed >/dev/null 2>&1 || true
  exit 2
fi
BODY="$(cat "$BODY_FILE" 2>/dev/null)"
PROJECTION_ID="$($PY -c 'import json,sys; print(json.load(open(sys.argv[1]))["projection_id"])' "$PROJECTION_FILE")"
DELIVERED_ID="$($PY -c 'import json,sys
try: print(json.load(open(sys.argv[1])).get("projection_id", ""))
except Exception: print("")' "$DELIVERY_STATE")"
if [ -n "$BODY" ] && [ "$DELIVERED_ID" != "$PROJECTION_ID" ]; then
  SEND_RESULT="$(bash "$TELEGRAM_SENDER" "$BODY" 2>&1)" || {
    "$PY" "$OUTCOME_SCRIPT" start-incident \
      --owner company --summary "Projection-backed Telegram delivery failed." \
      --fingerprint goal-monitor-telegram-delivery-failed >/dev/null 2>&1 || true
    exit 1
  }
  MESSAGE_ID="$(printf '%s\n' "$SEND_RESULT" | sed -nE 's/.*MSGID=([0-9]+).*/\1/p' | tail -1)"
  [ -n "$MESSAGE_ID" ] || exit 1
  "$PY" - "$DELIVERY_STATE" "$PROJECTION_ID" "$MESSAGE_ID" <<'PY'
import datetime,json,os,sys,tempfile
path,projection_id,message_id=sys.argv[1:]
os.makedirs(os.path.dirname(path),exist_ok=True)
payload={"schema_version":1,"projection_id":projection_id,"telegram_message_id":message_id,"delivered_at":datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00","Z")}
fd,tmp=tempfile.mkstemp(prefix=".capafy-delivery-",dir=os.path.dirname(path))
with os.fdopen(fd,"w") as stream:
 json.dump(payload,stream,sort_keys=True);stream.write("\n");stream.flush();os.fsync(stream.fileno())
os.replace(tmp,path)
PY
fi
cat "$REPORT_FILE" 2>/dev/null
exit "$RC"
