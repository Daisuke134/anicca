#!/usr/bin/env bash
# anicca-oss install — bootstraps the personal-life-leader stack into
# ~/.openclaw on the user's machine. Idempotent: safe to re-run.
#
# What this script does:
#   1. Verify required system deps (python3, gog, jq, git)
#   2. Detect or scaffold ~/.openclaw runtime root + ~/.openclaw/.env
#   3. Copy template profile + .env if missing (= NEVER overwrite user data)
#   4. Sync the life-manager skill bundle into ~/.openclaw/skills/
#   5. Register the 7 cron entries via openclaw cron CLI
#   6. Print "what to do next" so the user can finish on Telegram
#
# What this script does NOT do:
#   - Ask for API keys (that is the external coding-agent's job per spec §10.E)
#   - Start the Telegram bot (the user runs /start themselves)
#   - Touch any data outside ~/.openclaw and ~/Library/LaunchAgents

set -euo pipefail
trap 'echo "[install] ❌ failed on line $LINENO. nothing destructive, re-run safe."' ERR

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
SKILLS_TO_INSTALL=(
  anicca-life-manager
  anicca-travel-fill
  anicca-gcal-heal
  anicca-report
  anicca-fuel-broker
  anicca-schedule-template
)

cyan(){ printf "\033[36m%s\033[0m\n" "$*"; }
green(){ printf "\033[32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[33m%s\033[0m\n" "$*"; }
red(){ printf "\033[31m%s\033[0m\n" "$*"; }

cyan "================================================================"
cyan "  Anicca OSS install — personal life-leader mode"
cyan "  Repo root  : $REPO_ROOT"
cyan "  Runtime    : $ANICCA_HOME"
cyan "================================================================"
echo

# ─── 1. system deps ────────────────────────────────────────────────────
cyan "[1/6] checking system deps…"
for bin in python3 git jq; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    red "  ✗ $bin missing — install it first then re-run."
    exit 2
  fi
  green "  ✓ $bin"
done
if ! command -v openclaw >/dev/null 2>&1; then
  yellow "  ⚠ openclaw CLI not in PATH — cron registration will be skipped."
  yellow "    Install: npm install -g openclaw   (or brew install openclaw)"
  HAS_OPENCLAW=0
else
  green "  ✓ openclaw"
  HAS_OPENCLAW=1
fi
if ! command -v gog >/dev/null 2>&1; then
  yellow "  ⚠ gog CLI not in PATH — Google Calendar / Gmail will not work."
  yellow "    Install: see github.com/Daisuke134/gog"
fi
echo

# ─── 2. runtime root ───────────────────────────────────────────────────
cyan "[2/6] preparing runtime root…"
mkdir -p "$ANICCA_HOME"/{skills,state/location,identity,logs}
green "  ✓ $ANICCA_HOME"

if [ ! -f "$ANICCA_HOME/.env" ]; then
  if [ -f "$REPO_ROOT/.env.example" ]; then
    cp "$REPO_ROOT/.env.example" "$ANICCA_HOME/.env"
    chmod 600 "$ANICCA_HOME/.env"
    yellow "  ✎ created $ANICCA_HOME/.env from template — fill it in."
  else
    touch "$ANICCA_HOME/.env"
    chmod 600 "$ANICCA_HOME/.env"
    yellow "  ✎ created empty $ANICCA_HOME/.env — add your keys."
  fi
else
  green "  ✓ $ANICCA_HOME/.env  (preserved)"
fi

if [ ! -f "$ANICCA_HOME/identity/profile.json" ]; then
  if [ -f "$REPO_ROOT/identity/profile.example.json" ]; then
    cp "$REPO_ROOT/identity/profile.example.json" "$ANICCA_HOME/identity/profile.json"
    yellow "  ✎ created $ANICCA_HOME/identity/profile.json from template — fill it in."
  fi
else
  green "  ✓ $ANICCA_HOME/identity/profile.json  (preserved)"
fi
echo

# ─── 3. shared lib ─────────────────────────────────────────────────────
cyan "[3/6] syncing _shared lib…"
if [ -d "$REPO_ROOT/skills/_shared" ]; then
  mkdir -p "$ANICCA_HOME/skills/_shared"
  rsync -a --delete \
    --exclude='state/' --exclude='__pycache__/' \
    "$REPO_ROOT/skills/_shared/" "$ANICCA_HOME/skills/_shared/"
  green "  ✓ _shared synced"
else
  yellow "  ⚠ $REPO_ROOT/skills/_shared not in repo — skipping (legacy clone?)"
fi
echo

# ─── 4. skill bundle ───────────────────────────────────────────────────
cyan "[4/6] syncing life-manager skill bundle…"
for skill in "${SKILLS_TO_INSTALL[@]}"; do
  src="$REPO_ROOT/skills/$skill"
  if [ ! -d "$src" ]; then
    yellow "  ⚠ $skill not in repo — skip"
    continue
  fi
  dst="$ANICCA_HOME/skills/$skill"
  mkdir -p "$dst"
  rsync -a --delete \
    --exclude='state/' --exclude='__pycache__/' \
    "$src/" "$dst/"
  mkdir -p "$dst/state"
  green "  ✓ $skill"
done
echo

# ─── 5. cron registration ──────────────────────────────────────────────
cyan "[5/6] registering openclaw cron entries…"
if [ "$HAS_OPENCLAW" -eq 0 ]; then
  yellow "  ⚠ skipped (= openclaw CLI absent)"
else
  declare -a CRONS=(
    "anicca-life-manager|*/5 * * * *|bash ~/.openclaw/skills/anicca-life-manager/scripts/run.sh"
    "anicca-gcal-heal|*/15 * * * *|bash ~/.openclaw/skills/anicca-gcal-heal/scripts/run.sh"
    "anicca-travel-fill|0 */3 * * *|bash ~/.openclaw/skills/anicca-travel-fill/scripts/run.sh"
    "anicca-fuel-broker|17 * * * *|bash ~/.openclaw/skills/anicca-fuel-broker/scripts/run.sh"
    "anicca-report-daily|0 18 * * *|bash ~/.openclaw/skills/anicca-report/scripts/run.sh"
    "anicca-report-weekly|0 9 * * 1|bash ~/.openclaw/skills/anicca-report/scripts/run.sh --weekly"
    "anicca-schedule-template|0 4 * * *|bash ~/.openclaw/skills/anicca-schedule-template/scripts/run.sh"
  )
  EXISTING=$(openclaw cron list 2>/dev/null | awk '{print $2}' | sort -u || true)
  for line in "${CRONS[@]}"; do
    NAME=$(echo "$line" | cut -d'|' -f1)
    SCHED=$(echo "$line" | cut -d'|' -f2)
    CMD=$(echo "$line" | cut -d'|' -f3)
    if echo "$EXISTING" | grep -qx "$NAME"; then
      green "  ✓ $NAME already registered"
      continue
    fi
    if openclaw cron create --name "$NAME" --cron "$SCHED" \
         --message "exec で次を実行: $CMD" >/dev/null 2>&1; then
      green "  ✎ created $NAME ($SCHED)"
    else
      yellow "  ⚠ $NAME create failed — please add manually"
    fi
  done
fi
echo

# ─── 6. summary ────────────────────────────────────────────────────────
cyan "[6/6] done."
echo
green "What's next:"
cat <<'EOM'
  1. Verify your ~/.openclaw/.env has every key from the README table:
       TELEGRAM_BOT_TOKEN   GOOGLE_API_KEY   GEMINI_API_KEY
       TWILIO_ACCOUNT_SID   TWILIO_AUTH_TOKEN   TWILIO_PHONE_NUMBER
       GOG_ACCOUNT          GOG_KEYRING_PASSWORD
       1 FUEL (= ANTHROPIC_API_KEY | OPENAI_API_KEY | DEEPSEEK_API_KEY | KIMI_API_KEY | WALLET_ADDR)

  2. Verify your ~/.openclaw/identity/profile.json has at least:
       identity.name, identity.homeAddress, identity.phone
       alarm.wakeTime (default 07:00), alarm.quietHoursStart/End

  3. Start the Telegram Live-Location bot:
       launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.anicca.tg-loc-bot.plist
     If the plist doesn't exist yet, see docs/INSTALL_BOOTSTRAP.md.

  4. Open Telegram on your iPhone → your bot → /start. Share Live
     Location. Anicca takes over from there.

  5. Next morning around your wake time, you should get a phone call.
     If not, tail ~/.openclaw/skills/anicca-life-manager/state/run.log

  Repo: https://github.com/Daisuke134/anicca-oss
EOM
echo
green "anicca-oss install complete."
