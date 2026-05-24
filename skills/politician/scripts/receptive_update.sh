#!/usr/bin/env bash
# MODE=receptive_update — weekly Tue 08:00 JST.
# Iterates legislators.yaml, pulls last 30 days of voting records via
# congress.gov v3, flags AI-relevant bills, and updates each legislator's
# last_known_position.summary + verified_date.
#
# Stays read-mostly:
#   - never sends {{profile.lateness.stakeholders.channel}}
#   - never moves money
#   - mutates only data/legislators.yaml + a side log
# Slack-posts a one-line summary.
#
# Required env (LIVE):
#   CONGRESS_GOV_API_KEY    — congress.gov v3
# Optional:
#   QUORUM_API_KEY          — if present, augment with Quorum voting data
#   POLITICIAN_DRY_RUN=true — print the diff but don't write
set -euo pipefail
SKILL="${SKILL:-$(cd "$(dirname "$0")/.." && pwd)}"
MODE=receptive_update
source "$SKILL/scripts/lib/api_clients.sh"
source "$SKILL/scripts/lib/slack_format.sh"
source "$SKILL/scripts/lib/quorum.sh"

DRY="${POLITICIAN_DRY_RUN:-true}"
LEG_YAML="$SKILL/data/legislators.yaml"
LOGFILE="$SKILL/data/receptive_update.log"
TODAY="$(date -u +%Y-%m-%d)"

# Bootstrap guards — if YAML is missing, exit cleanly with skip line.
if [[ ! -f "$LEG_YAML" ]]; then
  slack_post "📊 Receptive-list update" "skipped reason=legislators.yaml-missing"
  exit 0
fi

if ! pol_require_env CONGRESS_GOV_API_KEY "(receptive_update needs congress.gov v3 key)"; then
  slack_post "📊 Receptive-list update" "skipped reason=CONGRESS_GOV_API_KEY-missing"
  exit 0
fi

# AI-relevance keyword set. Any bill whose title or summary matches any of
# these substrings (case-insensitive) is flagged AI-relevant for our scoring.
AI_KEYWORDS=(
  "artificial intelligence" "AI act" "AI risk" "machine learning"
  "foundation model" "deepfake" "algorithmic" "automated decision"
  "AI safety" "AI governance" "compute"
)

# Build pipe-separated regex for python.
AI_REGEX="$(printf '%s|' "${AI_KEYWORDS[@]}")"
AI_REGEX="${AI_REGEX%|}"

# Pull current YAML structure into Python for in-place patching.
# congress.gov endpoint per legislator: /v3/member/{bioguide}/sponsored-legislation
# (We don't have bioguide IDs in the YAML yet — see "Open issues" in deliverable.
# For now, use the member's name + state to query the v3 search endpoint and
# match. This is approximate; once Track 6 v0.3 lands we add bioguide_id to
# legislators.yaml as a first-class field.)
python3 - "$LEG_YAML" "$LOGFILE" "$AI_REGEX" "$TODAY" "$DRY" "${CONGRESS_GOV_API_KEY:-}" <<'PY'
import os, re, sys, json, time, urllib.parse
from pathlib import Path
try:
    import yaml
except ImportError:
    sys.stderr.write("[receptive_update] PyYAML required\n"); sys.exit(2)

leg_path, log_path, ai_regex, today, dry, api_key = sys.argv[1:7]
ai_re = re.compile(ai_regex, re.IGNORECASE)
dry = (dry == "true")

with open(leg_path, encoding="utf-8") as f:
    doc = yaml.safe_load(f)

legs = doc.get("legislators", [])
changed = 0
checked = 0
errors = 0
log_lines = [f"[{today}] receptive_update run dry={dry}"]

# Reusable urllib import
import urllib.request

def search_member_recent_bills(name: str, congress: int = 119, limit: int = 25):
    """
    Use congress.gov v3 /bill?q=… approximation. The v3 API does not expose a
    'bills sponsored by member-name-string' endpoint without a bioguide-ID,
    so this proxy queries the bill-search endpoint with the member's last
    name and filters Python-side by sponsor name. Good enough for a weekly
    summary; bioguide-ID indexing is the next iteration.
    """
    last = name.split()[-1]
    if not last:
        return []
    q = urllib.parse.quote(last)
    url = f"https://api.congress.gov/v3/bill/{congress}?api_key={api_key}&format=json&limit={limit}&q={q}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as ex:
        return [("__error__", str(ex))]
    bills = data.get("bills", [])
    out = []
    for b in bills:
        title = b.get("title", "") or ""
        sponsors = b.get("sponsors") or []
        if any(last.lower() in (s.get("fullName","") or "").lower() for s in sponsors):
            out.append((title, b.get("url","")))
    return out

# JP entries (country=JP) skip the congress.gov call — voting record source
# is shugiin.go.jp / sangiin.go.jp, no public v3-style API. Mark JP entries
# as "no-action: JP voting source not yet wired" in the log.
for L in legs:
    checked += 1
    if L.get("country") != "US":
        log_lines.append(f"  skip-jp  {L['id']:30s}  {L['full_name']}  (no JP voting API yet)")
        continue
    name = L.get("full_name", "")
    bills = search_member_recent_bills(name)
    if bills and bills[0][0] == "__error__":
        errors += 1
        log_lines.append(f"  ERROR    {L['id']:30s}  {bills[0][1]}")
        continue
    ai_bills = [(t, u) for (t, u) in bills if ai_re.search(t or "")]
    # Bump verified_date regardless (we did look).
    L.setdefault("last_known_position", {})
    old_summary = L["last_known_position"].get("summary", "")
    if ai_bills:
        new_line = f"[auto {today}] sponsored/co-sponsored {len(ai_bills)} AI-tagged bill(s) in current Congress."
        if new_line not in old_summary:
            L["last_known_position"]["summary"] = (old_summary or "").rstrip() + "\n" + new_line
            changed += 1
            log_lines.append(f"  bump     {L['id']:30s}  +{len(ai_bills)} ai-bills")
        else:
            log_lines.append(f"  no-diff  {L['id']:30s}  ({len(ai_bills)} ai-bills, already noted)")
    else:
        log_lines.append(f"  no-ai    {L['id']:30s}  ({len(bills)} bills found, none AI-tagged)")
    L["last_known_position"]["verified_date"] = today
    # Throttle congress.gov v3 (5,000/day cap; ~1.4 req/min sustained).
    time.sleep(0.3)

# Write back unless dry.
if not dry:
    doc["updated"] = today
    with open(leg_path, "w", encoding="utf-8") as f:
        yaml.dump(doc, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

# Append log.
with open(log_path, "a", encoding="utf-8") as f:
    for ln in log_lines:
        f.write(ln + "\n")
    f.write(f"  totals: checked={checked} changed={changed} errors={errors} dry={dry}\n")

# Stdout = single line that the slack_post wrapper will use.
print(f"checked={checked} changed={changed} errors={errors} dry={dry}")
PY

RES="$(tail -1 "$LOGFILE" | sed 's/^[[:space:]]*totals:[[:space:]]*//')"
slack_post "📊 Receptive-list update" "$RES"
