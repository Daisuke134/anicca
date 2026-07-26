#!/usr/bin/env bash
# One bounded Life Manager SELF-BUILD pass (spec §10 row 10f, §9.3 DEV loop).
#
# This is the launchd entrypoint for `ai.anicca.life-manager-dev`. It does exactly one thing per
# day: hand the oldest eligible loop-authored fix PR to the 10e merge guard, then report what
# actually happened. It decides nothing about merging — every gate lives in the guard.
#
# It mirrors life-manager-daily.sh: PATH first, recursion guard, env sourcing, one log file, one
# honest Telegram report at the end. Differences are deliberate:
#   * the report is sent whatever the outcome, INCLUDING a no-op day, because 10f's done condition
#     is seven distinct days each carrying an honest outcome — a silent day looks like a dead loop;
#   * the report is built from the ledger row the pass just wrote, never from a claim.
#
# This script never loads, unloads or edits its own launchd job — a loop that can schedule itself
# can also un-pause itself. Enabling the schedule is a separate, explicit operator step:
#   apps/life-manager/scripts/enable-self-build-launchd.sh
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
set -uo pipefail
umask 077

if [ "${LM_SELFBUILD_ACTIVE:-0}" = "1" ]; then
  printf 'self-build-daily: recursive invocation blocked\n' >&2
  exit 73
fi
export LM_SELFBUILD_ACTIVE=1

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${LM_SELFBUILD_REPO:-$(cd "$HERE/../.." && pwd)}"
APP_DIR="$REPO_ROOT/apps/life-manager"
NODE_BIN="${NODE_BIN:-$(command -v node || echo /opt/homebrew/bin/node)}"
DAILY_CLI="$APP_DIR/scripts/self-build-daily.js"
LOG="${LM_SELFBUILD_LOG:-$HOME/.openclaw/logs/life-manager-self-build.log}"
TG_TARGET="${LM_SELFBUILD_TELEGRAM_TARGET:-8547730585}"
mkdir -p "$(dirname "$LOG")"
printf '=== life-manager self-build run %s ===\n' "$(date '+%F %T %Z')" >>"$LOG"

# Credentials for gh / railway / the reviewer CLI live here. `set +u` because a launchd environment
# is not an interactive one and a dotenv file is allowed to reference unset variables.
if [ -f "$HOME/.openclaw/.env" ]; then
  set +u
  set -a
  # shellcheck disable=SC1091
  . "$HOME/.openclaw/.env"
  set +a
  set -u
fi

if [ ! -d "$APP_DIR/node_modules/pg" ]; then
  (cd "$APP_DIR" && npm ci --silent) >>"$LOG" 2>&1 || printf 'dependency install failed\n' >>"$LOG"
fi

# LM_SELFBUILD_DRY_RUN=1 exercises this whole path — env sourcing, the pass, the report render, the
# Telegram send — with the guard stubbed out, so the entrypoint can be verified without promoting
# anything. launchd never sets it. This is not a merge switch: the guard, not this flag, decides
# every gate, and skills/** is on the guard's DENY list so no unattended PR can touch this file.
DAILY_ARGS=()
[ "${LM_SELFBUILD_DRY_RUN:-0}" = "1" ] && DAILY_ARGS+=(--dry-run)

RESULT="$("$NODE_BIN" "$DAILY_CLI" "${DAILY_ARGS[@]+"${DAILY_ARGS[@]}"}" 2>>"$LOG")"
RC=$?
printf '%s\n' "$RESULT" >>"$LOG"

# The report is rendered from the ledger row itself. If the row cannot be parsed, that IS the
# report — a pass that cannot describe its own outcome must not go out looking like a success.
# shellcheck disable=SC2016  # the ${...} below are JS template literals, deliberately unexpanded
REPORT="$(RESULT="$RESULT" RC="$RC" "$NODE_BIN" -e '
const raw = String(process.env.RESULT || "").trim().split("\n").pop() || "";
let row = null;
try { row = JSON.parse(raw); } catch {}
if (!row || typeof row !== "object") {
  process.stdout.write(
    `⚠️ Life Manager self-build: the daily pass produced no readable ledger row `
    + `(exit ${process.env.RC}). Nothing was merged. Check ~/.openclaw/logs/life-manager-self-build.log.`,
  );
} else {
  const streak = row.streak || {};
  const target = row.pr ? `PR #${row.pr}` : "no PR";
  const why = row.no_op_reason ? ` (${row.no_op_reason})` : "";
  const guard = row.guard_run_ref ? `\nguard run: ${row.guard_run_ref}` : "";
  const err = row.error ? `\nerror: ${row.error}` : "";
  const stale = row.recovered_stale_lock ? "\nrecovered a stale guard lock (>30min)" : "";
  const skipped = Array.isArray(row.skipped) && row.skipped.length
    ? `\nskipped: ${row.skipped.map((s) => `#${s.pr} [${s.reasons.join(",")}]`).join(" ")}`
    : "";
  process.stdout.write(
    `🤖 Life Manager self-build ${row.day}\n`
    + `${target} -> ${row.verdict}${why}${guard}${stale}${err}${skipped}\n`
    + `day ${streak.distinctDays || 0}/${streak.required || 7}`
    + (streak.ready ? " — seven-day condition MET" : ` (${streak.remaining ?? "?"} to go)`),
  );
}
')"

printf '%s\n' "$REPORT" >>"$LOG"
openclaw message send --channel telegram --target "$TG_TARGET" \
  --message "$REPORT" --json >>"$LOG" 2>&1 || printf 'Telegram report failed\n' >>"$LOG"

printf '=== life-manager self-build done rc=%s %s ===\n' "$RC" "$(date '+%F %T %Z')" >>"$LOG"
if [ "$RC" -eq 0 ]; then
  mkdir -p "$HOME/.openclaw/state"
  touch "$HOME/.openclaw/state/.life-manager-self-build-last-pass"
fi
exit "$RC"
