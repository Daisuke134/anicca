#!/usr/bin/env bash
# Top-level dispatcher for the unified naist skill (v1.5).
# Usage: MODE=<mode> bash scripts/run.sh
# Modes:
#   pull, morning-rollup, friday-rollup, deadline-ical, confirm,
#   papers-suggest, funds-apply, edu-portal-check, course-register,
#   homework-fetch, homework-auto-draft, homework-submit, gcal-sync,
#   research-proposal-gen
# Optional: DRY_RUN=true
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS="$SKILL_DIR/scripts"
WORKSPACE="${HOME}/.openclaw/workspace/naist"
STATE_ROOT="${HOME}/.openclaw/state/naist"
mkdir -p "$WORKSPACE/drafts" "$WORKSPACE/sent" "$WORKSPACE/homework" "$WORKSPACE/inbox"

MODE="${MODE:-pull}"
DRY_RUN="${DRY_RUN:-false}"
TODAY="$(date -u +%Y-%m-%d)"

[ -f "${HOME}/.openclaw/.env" ] && set -a && source "${HOME}/.openclaw/.env" && set +a

log() { printf '[naist:%s] %s\n' "$MODE" "$*"; }

if [ ! -d "$STATE_ROOT" ]; then
  log "no users onboarded — STATE_ROOT=$STATE_ROOT missing. exit 0."
  exit 0
fi
slugs=()
while IFS= read -r d; do slugs+=("$(basename "$d")"); done < <(find "$STATE_ROOT" -mindepth 1 -maxdepth 1 -type d 2>/dev/null)
if [ "${#slugs[@]}" -eq 0 ]; then
  log "no slugs in $STATE_ROOT — exit 0."; exit 0
fi

run_per_slug() {
  local script="$1"; shift
  for slug in "${slugs[@]}"; do
    log "slug=$slug — $script $*"
    DRY_RUN="$DRY_RUN" SLUG="$slug" python3 "$SCRIPTS/$script" "$@"
  done
}

case "$MODE" in
  pull)
    run_per_slug triage.py
    run_per_slug draft-homework.py --plan-only  # NO send-as per Dais 2026-05-08
    ;;
  morning-rollup)       run_per_slug triage.py --rollup=24h ;;
  friday-rollup)        run_per_slug triage.py --rollup=7d --audit-deadlines ;;
  deadline-ical)        run_per_slug deadline-watch.py ;;
  papers-suggest)       run_per_slug papers-suggest.py ;;
  funds-apply)          run_per_slug funds-apply.py ;;
  edu-portal-check)     run_per_slug edu-portal-check.py ;;
  course-register)      run_per_slug course-register.py ;;
  homework-fetch)       run_per_slug homework-fetch.py ;;
  homework-auto-draft)  run_per_slug homework-auto-draft.py ;;
  homework-submit)      run_per_slug homework-submit.py ;;
  gcal-sync)            run_per_slug gcal-sync.py ;;
  research-proposal-gen) run_per_slug research-proposal-gen.py ;;
  confirm)
    : "${THREAD_TS:?THREAD_TS required for confirm mode}"
    : "${REACTION:?REACTION (+1|x) required}"
    log "confirm: thread=$THREAD_TS reaction=$REACTION"
    DRY_RUN="$DRY_RUN" THREAD_TS="$THREAD_TS" REACTION="$REACTION" python3 "$SCRIPTS/send-as.py"
    ;;
  *)
    log "unknown MODE=$MODE"; exit 64
    ;;
esac

log "done."
