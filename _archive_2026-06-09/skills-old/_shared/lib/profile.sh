#!/usr/bin/env bash
# profile.sh — the ONE documented way for skills to read per-user data.
#
# Contract (see anicca-oss/identity/README.md):
#   - SECRETS  → env vars from $ANICCA_HOME/.env   (e.g. $POSTIZ_API_KEY)
#   - PERSONAL → $ANICCA_HOME/identity/profile.json (this helper)
#   Never hardcode personal/specific values in a skill. Read them here.
#
# Usage:
#   source ~/.openclaw/skills/_shared/lib/profile.sh
#   WORK_EMAIL="$(profile '.{{profile.lateness.stakeholders.toField}}')"
#   REPORT_CH="$(profile_or_env '.channels.reportChannel' ANICCA_REPORT_CHANNEL)"
#   TT_FOCUS="$(profile '.social.tiktok[] | select(.purpose|test("FOCUS")) | .postizIntegrationId')"

ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
_ANICCA_PROFILE="${ANICCA_PROFILE:-$ANICCA_HOME/identity/profile.json}"

# profile <jq-filter> -> prints value (empty if absent/no file)
profile() {
  [ -f "$_ANICCA_PROFILE" ] || { return 0; }
  jq -r "${1} // empty" "$_ANICCA_PROFILE" 2>/dev/null
}

# profile_or_env <jq-filter> <ENV_NAME> -> profile value, else env var (fallback)
profile_or_env() {
  local v; v="$(profile "$1")"
  if [ -n "$v" ]; then printf '%s' "$v"; else printf '%s' "${!2:-}"; fi
}
