#!/usr/bin/env bash
# content-zero-view-watcher — read last N days of per-account totals, count consecutive
# days <100 views per integration, flag streak>=3 as DYING.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/report.sh
source "$SKILL_DIR/lib/report.sh"

PORTFOLIO="${PORTFOLIO:-$HOME/.openclaw/state/postiz-integrations.json}"
OUT_ROOT="${OUT_ROOT:-$HOME/.openclaw/workspace/content-metrics}"
STATE_DIR="${STATE_DIR:-$HOME/.openclaw/state/content-metrics}"
DRY_RUN="${CONTENT_METRICS_DRY_RUN:-false}"
THRESHOLD_VIEWS="${ZERO_VIEW_THRESHOLD:-100}"
STREAK_DAYS="${ZERO_VIEW_STREAK:-3}"
LOOKBACK_DAYS="${ZERO_VIEW_LOOKBACK:-7}"

mkdir -p "$STATE_DIR"
STATE_FILE="$STATE_DIR/zero-view-streaks.json"

ROWS_FILE="$(mktemp)"
python3 - "$PORTFOLIO" "$OUT_ROOT" "$THRESHOLD_VIEWS" "$STREAK_DAYS" "$LOOKBACK_DAYS" "$STATE_FILE" "$DRY_RUN" >"$ROWS_FILE" <<'PY'
import sys, os, json, datetime as dt
portfolio_p, out_root, thr, streak_n, lookback, state_f, dry_run = sys.argv[1:]
thr = int(thr); streak_n = int(streak_n); lookback = int(lookback)

with open(portfolio_p) as f: portfolio = json.load(f)

today = dt.datetime.now().date()
days = [(today - dt.timedelta(days=i)).isoformat() for i in range(lookback)]

state = {"updated_at": dt.datetime.now().isoformat(), "threshold_views": thr,
         "streak_days_required": streak_n, "lookback_days": lookback, "accounts": []}

for integ in portfolio.get("integrations", []):
    if not integ.get("active"): continue
    handle = integ["handle"]; platform = integ["platform"]; iid = integ["id"]
    safe_h = "".join(c if c.isalnum() or c in "_-" else "_" for c in handle)
    streak = 0
    for d in days:
        path = os.path.join(out_root, d, f"{platform}-{safe_h}.json")
        if not os.path.exists(path):
            break
        try:
            obj = json.load(open(path))
            v = int(obj.get("total_views", 0))
        except Exception:
            v = 0
        if v < thr:
            streak += 1
        else:
            break
    rec = {"handle": handle, "platform": platform, "integration_id": iid,
           "streak": streak, "threshold_views": thr}
    state["accounts"].append(rec)
    print(json.dumps(rec))

# Persist state file always (cheap, useful)
state["dry_run"] = (dry_run == "true")
with open(state_f, "w") as f: json.dump(state, f, indent=2)
PY

echo "[content-zero-view-watcher] state file: $STATE_FILE  dry_run=$DRY_RUN"
echo

if [[ "$DRY_RUN" == "true" ]]; then
  echo "----- DRY_RUN — would post to #metrics ({{profile.channels.reportChannel}}) -----"
  format_zero_view_alert < "$ROWS_FILE"
  echo "----- end DRY_RUN -----"
  echo "[dry_run] would NOT mutate ~/anicca-monk-factory/accounts/burn/burned.jsonl"
else
  format_zero_view_alert < "$ROWS_FILE"
fi

rm -f "$ROWS_FILE"
