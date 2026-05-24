#!/usr/bin/env bash
# content-7day-rollup — aggregate the last 7 days of per-account JSON, compute top/bottom 5,
# write top-performers.json, post (or print if DRY_RUN) the leaderboard.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/report.sh
source "$SKILL_DIR/lib/report.sh"

PORTFOLIO="${PORTFOLIO:-$HOME/.openclaw/state/postiz-integrations.json}"
OUT_ROOT="${OUT_ROOT:-$HOME/.openclaw/workspace/content-metrics}"
STATE_DIR="${STATE_DIR:-$HOME/.openclaw/state/content-metrics}"
DRY_RUN="${CONTENT_METRICS_DRY_RUN:-false}"
LOOKBACK_DAYS="${ROLLUP_LOOKBACK:-7}"

mkdir -p "$STATE_DIR"
ROLLUP_FILE="$STATE_DIR/top-performers.json"

python3 - "$PORTFOLIO" "$OUT_ROOT" "$LOOKBACK_DAYS" "$ROLLUP_FILE" "$DRY_RUN" <<'PY'
import sys, os, json, datetime as dt
portfolio_p, out_root, lookback, rollup_f, dry_run = sys.argv[1:]
lookback = int(lookback)

with open(portfolio_p) as f: portfolio = json.load(f)
today = dt.datetime.now().date()
period_end = today.isoformat()
period_start = (today - dt.timedelta(days=lookback - 1)).isoformat()

agg = {}
for integ in portfolio.get("integrations", []):
    if not integ.get("active"): continue
    handle = integ["handle"]; platform = integ["platform"]; iid = integ["id"]
    safe_h = "".join(c if c.isalnum() or c in "_-" else "_" for c in handle)
    rec = {"integration_id": iid, "handle": handle, "platform": platform,
           "owner_skill": integ.get("owner_skill"), "language": integ.get("language"),
           "posts": 0, "total_views": 0, "total_likes": 0}
    for i in range(lookback):
        d = (today - dt.timedelta(days=i)).isoformat()
        path = os.path.join(out_root, d, f"{platform}-{safe_h}.json")
        if not os.path.exists(path): continue
        try:
            obj = json.load(open(path))
        except Exception:
            continue
        rec["posts"] += int(obj.get("posts", 0))
        rec["total_views"] += int(obj.get("total_views", 0))
        rec["total_likes"] += int(obj.get("total_likes", 0))
    rec["engagement_rate"] = round(
        (rec["total_likes"] / rec["total_views"] * 100) if rec["total_views"] else 0.0, 2
    )
    agg[iid] = rec

ranked = sorted(agg.values(), key=lambda r: -r["total_views"])
out = {
    "period_start": period_start,
    "period_end": period_end,
    "generated_at": dt.datetime.now().isoformat(),
    "dry_run": dry_run == "true",
    "top5": ranked[:5],
    "bottom5": ranked[-5:][::-1] if len(ranked) >= 5 else ranked[::-1],
    "all": ranked,
}
with open(rollup_f, "w") as f: json.dump(out, f, indent=2)
PY

echo "[content-7day-rollup] wrote $ROLLUP_FILE  dry_run=$DRY_RUN"
echo

if [[ "$DRY_RUN" == "true" ]]; then
  echo "----- DRY_RUN — would post to #metrics ({{profile.channels.reportChannel}}) -----"
  format_rollup_leaderboard < "$ROLLUP_FILE"
  echo "----- end DRY_RUN -----"
else
  format_rollup_leaderboard < "$ROLLUP_FILE"
fi
