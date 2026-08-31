#!/usr/bin/env bash
# anicca-oss uninstall — completely removes the mr-bot stack and
# all Anicca runtime state from this machine. Asks for explicit Y at the
# destructive step.
#
# What this script does:
#   1. unload all anicca-related launchd plists
#   2. disable/delete openclaw cron entries we registered
#   3. delete the 6 mr-bot skill bundles from ~/.openclaw/skills/
#   4. optionally (with --hard) delete the entire ~/.openclaw runtime root
#   5. print final notes about Telegram bot + Google OAuth (= user action)
#
# Safe defaults: never deletes ~/.openclaw/identity/ or ~/.openclaw/.env
# unless --hard is passed AND the user confirms.

set -uo pipefail
ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
HARD=0
if [ "${1:-}" = "--hard" ]; then HARD=1; fi

cyan(){ printf "\033[36m%s\033[0m\n" "$*"; }
green(){ printf "\033[32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[33m%s\033[0m\n" "$*"; }
red(){ printf "\033[31m%s\033[0m\n" "$*"; }

SKILLS=(
  anicca-mr-bot
  anicca-travel-fill
  anicca-gcal-heal
  anicca-report
  anicca-fuel-broker
  anicca-schedule-template
)
CRON_NAMES=(
  anicca-mr-bot
  anicca-gcal-heal
  anicca-travel-fill
  anicca-fuel-broker
  anicca-report-daily
  anicca-report-weekly
  anicca-schedule-template
)
PLISTS=(
  ai.anicca.tg-loc-bot
  ai.anicca.pipecat-phone
  ai.anicca.heartbeat
  ai.anicca.watchdog
)

cyan "================================================================"
cyan "  Anicca OSS uninstall"
cyan "  Runtime : $ANICCA_HOME"
cyan "  Hard    : $([ $HARD -eq 1 ] && echo YES || echo NO)"
cyan "================================================================"
echo

# ─── 1. launchd plists ────────────────────────────────────────────────
cyan "[1/5] unloading launchd plists…"
for label in "${PLISTS[@]}"; do
  p="$HOME/Library/LaunchAgents/${label}.plist"
  if [ -f "$p" ]; then
    if launchctl bootout "gui/$(id -u)/${label}" >/dev/null 2>&1; then
      green "  ✎ booted out $label"
    fi
    mv "$p" "${p}.disabled.$(date +%Y%m%d_%H%M%S)" 2>/dev/null \
      && yellow "  ✎ disabled $p" \
      || yellow "  ⚠ could not rename $p"
  else
    green "  ✓ $label not present"
  fi
done
echo

# ─── 2. openclaw crons ────────────────────────────────────────────────
cyan "[2/5] removing openclaw cron entries…"
if command -v openclaw >/dev/null 2>&1; then
  for n in "${CRON_NAMES[@]}"; do
    id=$(openclaw cron list 2>/dev/null | awk -v name="$n" '$2==name {print $1}' | head -1 || true)
    if [ -n "$id" ]; then
      if openclaw cron disable "$id" >/dev/null 2>&1; then
        green "  ✎ disabled $n ($id)"
      else
        yellow "  ⚠ disable $n failed"
      fi
    else
      green "  ✓ $n not registered"
    fi
  done
else
  yellow "  ⚠ openclaw CLI not in PATH — skip"
fi
echo

# ─── 3. mr-bot skills ───────────────────────────────────────────
cyan "[3/5] removing mr-bot skill bundles…"
for skill in "${SKILLS[@]}"; do
  d="$ANICCA_HOME/skills/$skill"
  if [ -d "$d" ]; then
    rm -rf "$d"
    green "  ✎ removed $skill"
  else
    green "  ✓ $skill not installed"
  fi
done
echo

# ─── 4. optional hard delete ──────────────────────────────────────────
if [ $HARD -eq 1 ]; then
  cyan "[4/5] HARD delete: removing entire runtime root…"
  red "  This will permanently delete:"
  red "    $ANICCA_HOME/.env       (= your secrets)"
  red "    $ANICCA_HOME/identity/  (= your profile)"
  red "    $ANICCA_HOME/state/     (= all runtime data)"
  red "    + everything else in $ANICCA_HOME"
  echo
  printf "Type EXACTLY 'delete' to confirm: "
  read -r confirm
  if [ "$confirm" = "delete" ]; then
    rm -rf "$ANICCA_HOME"
    green "  ✎ removed $ANICCA_HOME"
  else
    yellow "  ⚠ aborted — runtime root preserved"
  fi
else
  cyan "[4/5] preserving runtime root (= no --hard flag)…"
  green "  ✓ $ANICCA_HOME/.env       preserved"
  green "  ✓ $ANICCA_HOME/identity/  preserved"
  green "  ✓ $ANICCA_HOME/state/     preserved"
fi
echo

# ─── 5. user action notes ─────────────────────────────────────────────
cyan "[5/5] final notes (= you action required)…"
echo
green "Telegram bot:"
yellow "  → @BotFather → /mybots → pick your Anicca bot → Bot Settings → Delete bot"
yellow "    (Anicca won't be able to read your bot data after this.)"
echo
green "Google OAuth:"
yellow "  → https://myaccount.google.com/permissions"
yellow "    → revoke 'gog' or 'anicca-oss' app authorisation"
echo
green "Twilio number:"
yellow "  → twilio.com → Numbers → Release if you no longer need it"
echo
green "anicca-oss uninstall complete."
