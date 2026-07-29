#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
AUDITOR="$ROOT/skills/gig-work/auditor.sh"

grep -F 'scripts/gig_slo.py' "$AUDITOR" >/dev/null
grep -F -- '--repair-database "$G/gig-control.sqlite3"' "$AUDITOR" >/dev/null
grep -F 'printf '\''%s\n'\'' "$slo_row" >> "$AUDIT"' "$AUDITOR" >/dev/null
grep -F 'src/gig/healing/controller.py' "$AUDITOR" >/dev/null
grep -F 'scripts/work_event_projector.py' "$AUDITOR" >/dev/null
grep -F 'telegram_report.py" work-events' "$AUDITOR" >/dev/null
