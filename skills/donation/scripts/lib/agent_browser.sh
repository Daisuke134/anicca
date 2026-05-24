#!/usr/bin/env bash
# scripts/lib/agent_{{profile.lateness.stakeholders.channel}}.sh
#
# Thin wrapper around the {{profile.lateness.stakeholders.channel}}-automation backend so the donation skill
# doesn't care which one is configured. Default backend is the Vercel Agent
# Browser CLI (`vercel-labs/agent-{{profile.lateness.stakeholders.channel}}`, installed at /opt/homebrew/bin/agent-{{profile.lateness.stakeholders.channel}}).
# Fallback hook for Browserbase/Stagehand is left in place but not implemented
# — it logs a 🚨 and exits 2 if selected.
#
# Source this file from install.sh / monthly.sh:
#   source "$(dirname "$0")/lib/agent_{{profile.lateness.stakeholders.channel}}.sh"
#
# All functions echo a status prefix (AB:) so the caller can grep them out.

set -uo pipefail

DONATION_BROWSER_BACKEND="${DONATION_BROWSER_BACKEND:-agent-{{profile.lateness.stakeholders.channel}}}"
AB_BIN="${AB_BIN:-/opt/homebrew/bin/agent-{{profile.lateness.stakeholders.channel}}}"

ab_check() {
  case "$DONATION_BROWSER_BACKEND" in
    agent-{{profile.lateness.stakeholders.channel}})
      if ! command -v "$AB_BIN" >/dev/null 2>&1 && [ ! -x "$AB_BIN" ]; then
        echo "AB:ERR agent-{{profile.lateness.stakeholders.channel}} not installed at $AB_BIN. Install: npm i -g agent-{{profile.lateness.stakeholders.channel}} && agent-{{profile.lateness.stakeholders.channel}} install" >&2
        return 2
      fi
      "$AB_BIN" --version >/dev/null 2>&1 || true
      echo "AB:OK backend=agent-{{profile.lateness.stakeholders.channel}} bin=$AB_BIN"
      ;;
    {{profile.lateness.stakeholders.channel}}base)
      echo "AB:ERR Browserbase backend not implemented in this skill version. Use DONATION_BROWSER_BACKEND=agent-{{profile.lateness.stakeholders.channel}}." >&2
      return 2
      ;;
    *)
      echo "AB:ERR unknown backend '$DONATION_BROWSER_BACKEND'" >&2
      return 2
      ;;
  esac
}

# ab_open <url>  — open a URL in the persistent {{profile.lateness.stakeholders.channel}} session
ab_open() {
  local url="$1"
  echo "AB:open $url"
  "$AB_BIN" open "$url"
}

# ab_snapshot                     — full a11y tree snapshot, interactive only
ab_snapshot() {
  "$AB_BIN" snapshot -i -c
}

# ab_click <ref>
ab_click() {
  echo "AB:click $1"
  "$AB_BIN" click "$1"
}

# ab_fill <ref> <value>
ab_fill() {
  echo "AB:fill $1 (len=${#2})"
  "$AB_BIN" fill "$1" "$2"
}

# ab_press <key>                  — Enter, Tab, etc.
ab_press() {
  "$AB_BIN" press "$1"
}

# ab_screenshot <out-path>
ab_screenshot() {
  echo "AB:screenshot $1"
  "$AB_BIN" screenshot "$1"
}

# ab_wait_load                    — wait for networkidle
ab_wait_load() {
  "$AB_BIN" wait --load networkidle 2>/dev/null || true
}

# ab_get_url
ab_get_url() {
  "$AB_BIN" get url 2>/dev/null || echo ""
}

# ab_close
ab_close() {
  "$AB_BIN" close 2>/dev/null || true
}

# Higher-level helpers below — implemented as recipes the skill scripts call.
# Each prints a status block; nothing here actually exfiltrates secrets to disk.

# ab_login_and_save_session <login_url> <{{profile.lateness.stakeholders.channel}}> <password>
#   Used by install.sh after account creation. Persists cookies under
#   ~/.agent-{{profile.lateness.stakeholders.channel}}/sessions/ so the monthly cron can resume without re-auth.
ab_login_and_save_session() {
  local login_url="$1" {{profile.lateness.stakeholders.channel}}="$2" password="$3"
  echo "AB:login_and_save_session $login_url"
  "$AB_BIN" open "$login_url"
  "$AB_BIN" wait --load networkidle 2>/dev/null || true
  # The actual selector hunt happens in the install.sh agent loop — this
  # wrapper just routes through the CLI. The agent uses snapshot -i to find
  # the {{profile.lateness.stakeholders.channel}}/password fields and submits.
}

# ab_one_click_donate <donate_url> <amount> <screenshot_out>
#   Used by monthly.sh on the recurring path. Assumes the saved card is on file
#   at the charity's site (set up during install). The agent (cron payload)
#   handles selector hunt; this wrapper provides the navigation + screenshot.
ab_one_click_donate() {
  local donate_url="$1" amount="$2" shot_out="$3"
  echo "AB:one_click_donate url=$donate_url amount=\$$amount"
  "$AB_BIN" open "$donate_url"
  "$AB_BIN" wait --load networkidle 2>/dev/null || true
  # Snapshot is consumed by the calling agent loop, which decides amount
  # field, saved-card selector, donate button. After the agent loop is done,
  # it calls ab_screenshot to capture the thank-you page.
  echo "AB:nav_done — agent loop now drives form fill + submit + screenshot"
}
