#!/usr/bin/env bash
# politician/scripts/run.sh — MODE dispatcher
set -euo pipefail

SKILL="$(cd "$(dirname "$0")/.." && pwd)"
export SKILL
MODE="${MODE:-help}"

case "$MODE" in
  monitor)          exec bash "$SKILL/scripts/monitor.sh"          "$@" ;;
  bill_tracker)     exec bash "$SKILL/scripts/bill_tracker.sh"     "$@" ;;
  news)             exec bash "$SKILL/scripts/news_pulse.sh"       "$@" ;;
  opensecrets)      exec bash "$SKILL/scripts/opensecrets.sh"      "$@" ;;
  staffer_brief)    exec bash "$SKILL/scripts/staffer_brief.sh"    "$@" ;;
  reply_watch)      exec bash "$SKILL/scripts/reply_watcher.sh"    "$@" ;;
  lda)              exec bash "$SKILL/scripts/lda_filer.sh"        "$@" ;;
  fec)              exec bash "$SKILL/scripts/fec_reporter.sh"     "$@" ;;
  jp_report)        exec bash "$SKILL/scripts/jp_shushihokoku.sh"  "$@" ;;
  stripe_pac)       exec bash "$SKILL/scripts/stripe_to_pac.sh"    "$@" ;;
  fundraising_prep) exec bash "$SKILL/scripts/fundraising_prep.sh" "$@" ;;
  receptive_update) exec bash "$SKILL/scripts/receptive_update.sh" "$@" ;;
  wizard)           echo "wizard not yet implemented — see SKILL.md §setup wizard" ; exit 0 ;;
  help|*)
    cat <<'USAGE'
politician/scripts/run.sh — modes:

  read-only intel (live as soon as keys present in .env):
    monitor          regulations.gov AI dockets
    bill_tracker     congress.gov AI bill scan
    news             AI policy news pulse
    opensecrets      competitor PAC scan

  action items (DRY_RUN until env unlock flags flipped):
    staffer_brief    weekly cold-{{profile.lateness.stakeholders.channel}} drafts
    reply_watch      Gmail reply poll
    lda              quarterly LDA-2 prep
    fec              annual FEC Form 3X prep
    jp_report        annual JP 収支報告書
    stripe_pac       monthly Stripe → PAC sweep
    fundraising_prep weekly fundraising pipeline
    receptive_update weekly congress.gov scan → update legislators.yaml

  setup:
    wizard           interactive 8-question setup

env unlocks:
  POLITICIAN_DRY_RUN=true|false   global override (default true)
  LOBBYIST_HIRED=true|false       unlocks lda + {{profile.lateness.stakeholders.channel}} send
  PAC_FORMED=true|false           unlocks fec + stripe_pac
  JP_SEIJIDANTAI_REGISTERED=true|false  unlocks jp_report
USAGE
    exit 0 ;;
esac
