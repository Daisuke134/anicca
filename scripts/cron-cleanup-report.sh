#!/usr/bin/env bash
# cron-cleanup-report.sh — audit OpenClaw cron fleet, triage status=error jobs,
# emit ~/.hermes/state/cron-triage.jsonl, and print a category breakdown.
#
# Categorization uses the gateway's inline state.lastDiagnostics.summary
# (already captures the last fire's stderr / model-router result), so no
# per-cron `openclaw cron logs` round-trip is needed in the common case.
#
# Disabling is NOT done here — it's a deliberate, log-reviewed action gated by
# $HOME/.local/state/life-manager/state/cron-protect.txt. This script only reports.
#
# Usage:  bash scripts/cron-cleanup-report.sh
set -euo pipefail

OUT="${CRON_TRIAGE_OUT:-$HOME/.hermes/state/cron-triage.jsonl}"
mkdir -p "$(dirname "$OUT")"

TMP="$(mktemp -t cron_p12.XXXXXX.json)"
trap 'rm -f "$TMP"' EXIT

# Page 0 (200 jobs) is the working set; the fleet is ~210. The bound is fine for
# this pass — the task caps triage at the first batch.
openclaw cron list --all --json >"$TMP" 2>/dev/null

PROTECT="$HOME/.local/state/life-manager/state/cron-protect.txt"

CRON_TRIAGE_OUT="$OUT" PROTECT_FILE="$PROTECT" python3 - "$TMP" <<'PY'
import json, os, re, sys
from datetime import datetime, timezone

src = sys.argv[1]
out = os.environ["CRON_TRIAGE_OUT"]
protect_file = os.environ["PROTECT_FILE"]

protect = []
if os.path.exists(protect_file):
    for line in open(protect_file):
        line = line.strip()
        if line and not line.startswith("#"):
            protect.append(line)

def is_protected(name):
    return any(p in (name or "") for p in protect)

d = json.load(open(src))
jobs = d["jobs"]
err = [c for c in jobs if (c.get("state") or {}).get("lastStatus") == "error"]

def categorize(summary):
    s = (summary or "").lower()
    if re.search(r"module not found|no such file|skill removed|not executable|cannot find|enoent|command not found", s):
        return "dead"
    if re.search(r"rate.?limit|429|quota|cooldown|usage limit|suspending lanes", s):
        return "rate_limit"
    if re.search(r"schema|validation|columnnotfound|invalid request body|invalid body|unexpected field", s):
        return "schema_drift"
    if re.search(r"credential|env not set|missing key|unauthorized|api key|401|403|not configured", s):
        return "infra"
    return "unknown"

now = datetime.now(timezone.utc).isoformat()
rows = []
for c in err:
    st = c.get("state") or {}
    diag = st.get("lastDiagnostics") or {}
    summary = diag.get("summary") or st.get("lastDiagnosticSummary") or st.get("lastErrorReason") or st.get("lastError") or ""
    cat = categorize(summary)
    name = c.get("name")
    decision = "disable" if (cat == "dead" and not is_protected(name)) else "leave"
    rows.append({
        "id": c.get("id"),
        "name": name,
        "enabled": c.get("enabled"),
        "category": cat,
        "protected": is_protected(name),
        "consecutiveErrors": st.get("consecutiveErrors"),
        "first_error": summary[:300],
        "decision": decision,
        "ts": now,
    })

with open(out, "w") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

from collections import Counter
cats = Counter(r["category"] for r in rows)
print(f"error crons: {len(rows)}")
for k in ("dead", "schema_drift", "infra", "rate_limit", "unknown"):
    print(f"  {k}: {cats.get(k,0)}")
dead = [r for r in rows if r["decision"] == "disable"]
print(f"disable candidates (dead, unprotected): {len(dead)}")
for r in dead:
    print(f"    {r['id']}  {r['name']}")
print(f"triage written: {out}")
PY
