#!/usr/bin/env bash
# MID lane の token 予算を、usage 集計が配線されるまで elapsed time と attempt 数で保守的に代理判定する。
# stdout: {"verdict":"CONTINUE|STOP_SPENDING",...}; exit 0=CONTINUE, exit 1=STOP_SPENDING。
set -uo pipefail

STARTED_AT=""
NOW="$(date +%s)"
REVISE_ATTEMPTS=0
READER_ATTEMPTS=0
MAX_ELAPSED_SECONDS=14400
MAX_REVISE_ATTEMPTS=6
MAX_READER_ATTEMPTS=6
BUDGET_USD=4

while [ $# -gt 0 ]; do case "$1" in
  --started-at) STARTED_AT="$2"; shift 2;;
  --now) NOW="$2"; shift 2;;
  --revise-attempts) REVISE_ATTEMPTS="$2"; shift 2;;
  --reader-attempts) READER_ATTEMPTS="$2"; shift 2;;
  *) echo "FATAL: unknown arg: $1" >&2; exit 2;;
esac; done

is_nonnegative_integer() { [[ "$1" =~ ^[0-9]+$ ]]; }
is_positive_number() { [[ "$1" =~ ^[0-9]+([.][0-9]+)?$ ]] && python3 -c 'import sys; raise SystemExit(0 if float(sys.argv[1]) > 0 else 1)' "$1"; }

is_nonnegative_integer "$STARTED_AT" || { echo "FATAL: --started-at must be a Unix epoch" >&2; exit 2; }
is_nonnegative_integer "$NOW" || { echo "FATAL: --now must be a Unix epoch" >&2; exit 2; }
is_nonnegative_integer "$REVISE_ATTEMPTS" || { echo "FATAL: --revise-attempts must be non-negative" >&2; exit 2; }
is_nonnegative_integer "$READER_ATTEMPTS" || { echo "FATAL: --reader-attempts must be non-negative" >&2; exit 2; }
is_nonnegative_integer "$MAX_ELAPSED_SECONDS" || { echo "FATAL: max elapsed must be non-negative" >&2; exit 2; }
is_nonnegative_integer "$MAX_REVISE_ATTEMPTS" || { echo "FATAL: max revise attempts must be non-negative" >&2; exit 2; }
is_nonnegative_integer "$MAX_READER_ATTEMPTS" || { echo "FATAL: max reader attempts must be non-negative" >&2; exit 2; }
is_positive_number "$BUDGET_USD" || { echo "FATAL: budget must be positive" >&2; exit 2; }
[ "$NOW" -ge "$STARTED_AT" ] || { echo "FATAL: --now precedes --started-at" >&2; exit 2; }

ELAPSED_SECONDS=$((NOW - STARTED_AT))
REASONS=()
[ "$ELAPSED_SECONDS" -lt "$MAX_ELAPSED_SECONDS" ] || REASONS+=("elapsed_seconds reached $MAX_ELAPSED_SECONDS")
[ "$REVISE_ATTEMPTS" -le "$MAX_REVISE_ATTEMPTS" ] || REASONS+=("revise_attempts exceeded $MAX_REVISE_ATTEMPTS")
[ "$READER_ATTEMPTS" -le "$MAX_READER_ATTEMPTS" ] || REASONS+=("reader_attempts exceeded $MAX_READER_ATTEMPTS")

if [ "${#REASONS[@]}" -eq 0 ]; then
  VERDICT="CONTINUE"
else
  VERDICT="STOP_SPENDING"
fi

# macOS 標準 Bash 3.2 は空配列の ${array[@]} を nounset で unbound 扱いする。
set +u
JSON=$(python3 - "$VERDICT" "$BUDGET_USD" "$ELAPSED_SECONDS" "$REVISE_ATTEMPTS" "$READER_ATTEMPTS" \
  "$MAX_ELAPSED_SECONDS" "$MAX_REVISE_ATTEMPTS" "$MAX_READER_ATTEMPTS" "${REASONS[@]}" <<'PY'
import json, sys
verdict, budget, elapsed, revise, reader, max_elapsed, max_revise, max_reader, *reasons = sys.argv[1:]
print(json.dumps({
    "verdict": verdict,
    "token_budget_usd": float(budget),
    "measurement": "elapsed-and-attempt-proxy",
    "elapsed_seconds": int(elapsed),
    "revise_attempts": int(revise),
    "reader_attempts": int(reader),
    "limits": {
        "elapsed_seconds": int(max_elapsed),
        "revise_attempts": int(max_revise),
        "reader_attempts": int(max_reader),
    },
    "reasons": reasons,
}, separators=(",", ":"), ensure_ascii=False))
PY
)
set -u
printf '%s\n' "$JSON"
[ "$VERDICT" = "CONTINUE" ]
