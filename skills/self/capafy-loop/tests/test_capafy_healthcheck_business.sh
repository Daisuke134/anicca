#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
HEALTH="$ROOT/skills/self/capafy-loop/capafy-loop-healthcheck.sh"
P=0; F=0
ok(){ echo "  ok $1"; P=$((P+1)); }; bad(){ echo "  FAIL $1: $2"; F=$((F+1)); }
eq(){ [ "$2" = "$3" ]&&ok "$1"||bad "$1" "want '$3' got '$2'"; }
has(){ printf '%s' "$2"|grep -qF "$3"&&ok "$1"||bad "$1" "missing '$3'"; }

T="$(mktemp -d)"; CALLS="$T/calls"; FIXER="$T/fixer.sh"; CHECKER="$T/checker.sh"
printf '%s\n' '#!/usr/bin/env bash' 'printf "%s\n" "$* incident=${CAPAFY_INCIDENT_ID:-}" >> "$CALLS"' > "$FIXER"; chmod +x "$FIXER"

printf '%s\n' '#!/usr/bin/env bash' 'printf "{\"status\":\"healthy\"}\n"' 'exit 0' > "$CHECKER"; chmod +x "$CHECKER"
HOME="$T" CAPAFY_BUSINESS_HEALTH_CMD="$CHECKER" CAPAFY_SELF_FIX="$FIXER" CAPAFY_HEALTH_SKIP_SCHEDULER_CHECK=1 CALLS="$CALLS" bash "$HEALTH" >/dev/null 2>&1; rc=$?
eq "healthy business outcome exits zero" "$rc" "0"
call_count=0; [ -f "$CALLS" ] && call_count="$(wc -l < "$CALLS" | tr -d ' ')"
eq "healthy business outcome does not self-fix" "$call_count" "0"

printf '%s\n' '#!/usr/bin/env bash' 'printf "{\"status\":\"unhealthy\",\"reason\":\"repair_sla_expired\",\"incident_id\":\"capafy-builder-test\"}\n"' 'exit 1' > "$CHECKER"; chmod +x "$CHECKER"
HOME="$T" CAPAFY_BUSINESS_HEALTH_CMD="$CHECKER" CAPAFY_SELF_FIX="$FIXER" CAPAFY_HEALTH_SKIP_SCHEDULER_CHECK=1 CALLS="$CALLS" bash "$HEALTH" >/dev/null 2>&1; rc=$?
[ "$rc" -ne 0 ]&&ok "expired repair SLA exits nonzero"||bad "expired repair SLA exits nonzero" "rc=$rc"
call="$(cat "$CALLS")"
has "expired SLA preserves incident id" "$call" "incident=capafy-builder-test"
has "expired SLA invokes Capafy fixer" "$call" "capafy Capafy business-outcome watchdog: repair_sla_expired"

echo "=== capafy business healthcheck: $P passed $F failed ==="; rm -rf "$T"; [ "$F" -eq 0 ] || exit 1
