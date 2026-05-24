#!/usr/bin/env bash
# coordination_wall.sh — federal-election-law coordination wall enforcement.
#
# A Super PAC making independent expenditures CANNOT coordinate with a
# candidate's campaign committee or its agents. (See {{profile.lateness.stakeholders.senderType}}/super-pac-spec.md
# for the full SpeechNow/11 C.F.R. § 109.21 cite.)
#
# The wall is enforced at the data layer:
#   1. data/coordination_blacklist.json holds (a) blacklisted legislator IDs
#      who have declared candidacies in the active cycle, (b) blacklisted
#      staffer {{profile.lateness.stakeholders.channel}}s who work for those campaigns, and (c) blacklisted
#      domains for campaign committees.
#   2. Every outreach script and every PAC contribution script MUST call
#      coord_check_recipient BEFORE the side-effecting call ({{profile.lateness.stakeholders.channel}} send,
#      Stripe transfer, etc.).
#   3. A failed check logs a Slack 🚨 alert and returns non-zero.
#      The caller is responsible for treating non-zero as "skip this
#      recipient" rather than "crash the entire run."
#
# Schema (data/coordination_blacklist.json):
# {
#   "version": 1,
#   "active_through": "2026-11-04",
#   "blacklisted_legislators": [
#     {"id": "us-senate-MN", "reason": "Klobuchar declared candidacy 2026"}
#   ],
#   "blacklisted_staffer_{{profile.lateness.stakeholders.channel}}s": ["staff@klobucharforsenate.com"],
#   "blocked_domains": ["*.electioncommittee.example", "*.forcongress.example"],
#   "blacklisted_handles": ["@KlobucharCampaign"]
# }

# ── env load ─────────────────────────────────────────────────────────────────
_cw_loaded=0
_cw_load_env() {
  [[ "$_cw_loaded" == "1" ]] && return 0
  local envf="${OPENCLAW_ENV:-$HOME/.openclaw/.env}"
  [[ -f "$envf" ]] && { set -a; source "$envf"; set +a; }
  _cw_loaded=1
}

_cw_blacklist_path() {
  printf '%s\n' "${COORDINATION_BLACKLIST:-${SKILL:-$(cd "$(dirname "$0")/.." && pwd)}/data/coordination_blacklist.json}"
}

# Slack alert on coordination violation attempt.
# Tries SLACK_BOT_TOKEN webhook to channel:{{profile.channels.reportChannel}} ; falls back to stderr.
_cw_alert() {
  local msg="$1"
  _cw_load_env
  printf '🚨 [coordination-wall] %s\n' "$msg" >&2
  if [[ -n "${SLACK_BOT_TOKEN:-}" && "${POLITICIAN_DRY_RUN:-true}" != "true" ]]; then
    curl -sS -X POST 'https://slack.com/api/chat.postMessage' \
      -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
      -H 'Content-Type: application/json; charset=utf-8' \
      --data "$(jq -n --arg ch "${POLITICIAN_SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
                       --arg t "🚨 Coordination wall: $msg" \
                       '{channel:$ch, text:$t}')" \
      >/dev/null 2>&1 || true
  fi
}

# ── public API ───────────────────────────────────────────────────────────────

# coord_check_recipient <legislator_id> [staffer_{{profile.lateness.stakeholders.channel}}]
#   Returns 0 if recipient is CLEARED. Returns 1 if BLACKLISTED.
#   On blacklist hit, posts a Slack 🚨 and prints reason on stderr.
#   Caller MUST treat non-zero as "skip this recipient", not "fatal."
coord_check_recipient() {
  local legid="${1:-}" {{profile.lateness.stakeholders.channel}}="${2:-}"
  local blf; blf="$(_cw_blacklist_path)"
  if [[ ! -f "$blf" ]]; then
    # No blacklist file = nothing blacklisted. Allow, but log once.
    [[ -z "${_CW_NOFILE_LOGGED:-}" ]] && {
      printf '[coord-wall] no blacklist file at %s — allowing all\n' "$blf" >&2
      export _CW_NOFILE_LOGGED=1
    }
    return 0
  fi

  # 1. legislator-id match
  if [[ -n "$legid" ]] && jq -e --arg id "$legid" \
       '(.blacklisted_legislators // [])[] | select(.id == $id)' "$blf" >/dev/null 2>&1; then
    local reason
    reason=$(jq -r --arg id "$legid" '(.blacklisted_legislators // [])[] | select(.id == $id) | .reason' "$blf" 2>/dev/null)
    _cw_alert "BLOCK legislator_id=$legid reason=\"$reason\""
    return 1
  fi

  # 2. staffer-{{profile.lateness.stakeholders.channel}} exact match
  if [[ -n "${{profile.lateness.stakeholders.channel}}" ]] && jq -e --arg e "${{profile.lateness.stakeholders.channel}}" \
       '(.blacklisted_staffer_{{profile.lateness.stakeholders.channel}}s // []) | index($e)' "$blf" >/dev/null 2>&1; then
    _cw_alert "BLOCK staffer_{{profile.lateness.stakeholders.channel}}=${{profile.lateness.stakeholders.channel}} reason=\"on-blacklisted_staffer_{{profile.lateness.stakeholders.channel}}s\""
    return 1
  fi

  # 3. domain glob match (e.g. *.forcongress.example)
  if [[ -n "${{profile.lateness.stakeholders.channel}}" ]]; then
    local dom="${{{profile.lateness.stakeholders.channel}}#*@}"
    while IFS= read -r pat; do
      [[ -z "$pat" || "$pat" == null ]] && continue
      # turn glob *.forcongress.example into regex \..*\.forcongress\.example$
      local reg; reg=$(printf '%s' "$pat" | sed -e 's/\./\\./g' -e 's/\*/.*/g')
      if [[ "$dom" =~ ^${reg}$ ]]; then
        _cw_alert "BLOCK staffer_{{profile.lateness.stakeholders.channel}}=${{profile.lateness.stakeholders.channel}} matched_domain_pattern=$pat"
        return 1
      fi
    done < <(jq -r '(.blocked_domains // [])[]?' "$blf" 2>/dev/null)
  fi

  return 0
}

# coord_check_active_cycle
#   Returns 0 if the wall is still active (today <= active_through).
#   Returns 1 if the active_through date has passed (post-election).
#   Useful for short-circuiting wall checks after the election ends.
coord_check_active_cycle() {
  local blf; blf="$(_cw_blacklist_path)"
  [[ ! -f "$blf" ]] && return 0
  local th; th=$(jq -r '.active_through // empty' "$blf" 2>/dev/null)
  [[ -z "$th" ]] && return 0
  local today; today=$(date -u +%Y-%m-%d)
  [[ "$today" > "$th" ]] && return 1
  return 0
}

# coord_summary  →  one-line "n_legislators=X n_{{profile.lateness.stakeholders.channel}}s=Y active_through=…"
# Caller can include in slack_post fields for visibility.
coord_summary() {
  local blf; blf="$(_cw_blacklist_path)"
  if [[ ! -f "$blf" ]]; then
    printf 'blacklist=missing\n'; return 0
  fi
  jq -r '"n_legislators=\((.blacklisted_legislators // []) | length) n_{{profile.lateness.stakeholders.channel}}s=\((.blacklisted_staffer_{{profile.lateness.stakeholders.channel}}s // []) | length) n_domains=\((.blocked_domains // []) | length) active_through=\(.active_through // "n/a")"' \
    "$blf" 2>/dev/null
}
