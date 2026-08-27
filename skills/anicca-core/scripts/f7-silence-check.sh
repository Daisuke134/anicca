#!/usr/bin/env bash
# f7-silence-check.sh — F7: a loop that exits 0 and produces nothing.
#
# Every other failure class needs the process to die. F2 missing dependency, F3
# missing binary, F5 log bloat, F6 provider outage -- all crash classes. The way loops
# actually died here was quieter: gig ran 4.5 days exiting 0, with a fully green test
# suite, while its ledgers stood still. capafy, clipping and larry show "Status 0" in
# launchctl today and have produced nothing for days. openclaw cron cannot see it
# either: "Exit code 0 records the run ok", and a NO_REPLY is suppressed by design.
#
# So F7 refuses to ask "did it run". It asks "did anything come out". Each loop
# declares the ledger that grows when it does real work and how long silence is
# tolerable; a loop whose every declared ledger has been still for longer than that is
# reported through the same record_action path as every other class, which gives it
# the same escalation, cooldown and Telegram delivery for free.
#
# Deliberately NOT self-repairing. A silent loop can be silent for a dozen reasons --
# no work available, an expired login, a broken prompt -- and restarting it blindly is
# how tier1 killed a healthy gig worker on 2026-07-27. F7 reports; a human or a
# class-specific remedy decides.
set -uo pipefail

ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
MANIFEST="${F7_MANIFEST:-$ANICCA_HOME/state/f7-loop-manifest.json}"
# shellcheck source=/dev/null
. "${F7_LIB:-$HOME/.openclaw/skills/_shared/scripts/self-heal-lib.sh}"

[ -f "$MANIFEST" ] || { echo '{"status":"skipped","reason":"no_manifest"}'; exit 0; }

# One python pass does the measuring: freshest mtime per loop, in hours. Emitting a
# flat TSV keeps the decision in shell where record_action lives.
FINDINGS=$(python3 - "$MANIFEST" <<'PYEOF'
import json, os, sys, time

try:
    manifest = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as error:
    print(f"__error__\t{type(error).__name__}\t0\t0")
    raise SystemExit(0)

now = time.time()
for loop in manifest.get("loops", []):
    label = str(loop.get("label") or "").strip()
    ledgers = loop.get("ledgers") or []
    limit = float(loop.get("max_silence_hours") or 0)
    if not label or not ledgers or limit <= 0:
        continue
    # Freshest wins: a loop with several outputs is working if ANY of them grew.
    ages, present = [], 0
    for path in ledgers:
        expanded = os.path.expanduser(str(path))
        if os.path.exists(expanded):
            present += 1
            ages.append((now - os.path.getmtime(expanded)) / 3600.0)
    if present == 0:
        print(f"{label}\tno_ledger\t0\t{limit:.1f}")
        continue
    quietest = min(ages)
    if quietest > limit:
        print(f"{label}\tsilent\t{quietest:.1f}\t{limit:.1f}")
PYEOF
)

while IFS=$'\t' read -r label kind hours limit; do
  [ -n "$label" ] || continue
  if [ "$label" = "__error__" ]; then
    record_action "F7_silent_barren" "🚨 F7 manifest unreadable ($kind) — no loop is being watched for silence" \
      "manifest=$MANIFEST error=$kind" "none (manifest must be fixed)" "manifest_unreadable" \
      "F7_manifest"
    continue
  fi
  if [ "$kind" = "no_ledger" ]; then
    record_action "F7_silent_barren" "🚨 $label declares an output ledger that does not exist — its productivity cannot be judged at all" \
      "label=$label declared_ledgers_present=0 limit_h=$limit" "none (report only)" "no_ledger" \
      "F7_silent_barren_${label}"
  else
    record_action "F7_silent_barren" "🚨 $label has produced nothing for ${hours}h (allowed ${limit}h) — the job may be exiting 0 while doing no work" \
      "label=$label silent_hours=$hours limit_h=$limit" "none (report only; blind restarts killed a healthy worker on 2026-07-27)" "silent" \
      "F7_silent_barren_${label}"
  fi
done <<< "$FINDINGS"

finish_and_escalate "F7: every declared loop produced something within its window" >/dev/null 2>&1 || true
echo '{"status":"ok"}'
