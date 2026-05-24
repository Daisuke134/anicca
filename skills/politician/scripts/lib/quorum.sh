#!/usr/bin/env bash
# quorum.sh — wrapper for Quorum legislative-tracker API.
#
# Quorum (https://www.quorum.us/) is the premium legislative-affairs platform.
# Pricing is enterprise-only (typically $30k–$80k/yr, no public price list as
# of 2026-05). It bundles: bill tracking across federal + 50 states + EU,
# full congressional staff directory (the LegiStorm-equivalent that's actually
# searchable by AI/Tech LA), voting record analysis, advocacy automation
# (post the Phone2Action acquisition).
#
# Until a Quorum contract is signed, every function in this file is STUB-ONLY
# and the cheap-equivalent fallbacks are documented inline:
#   - bill search           → use api_clients.sh::pol_congress_search_bills (free)
#   - voting record         → use govtrack.us scraping or congress.gov API
#   - staffer lookup        → no free equivalent; legistorm.com paid ($499/yr)
#                              or plumb manual research

# ── env load ─────────────────────────────────────────────────────────────────
_q_loaded=0
_q_load_env() {
  [[ "$_q_loaded" == "1" ]] && return 0
  local envf="${OPENCLAW_ENV:-$HOME/.openclaw/.env}"
  if [[ -f "$envf" ]]; then
    set -a; source "$envf"; set +a
  fi
  _q_loaded=1
}

_q_stub_mode() {
  _q_load_env
  if [[ -z "${QUORUM_API_KEY:-}" ]]; then
    return 0
  fi
  if [[ "${POLITICIAN_DRY_RUN:-true}" == "true" ]]; then
    return 0
  fi
  return 1
}

_q_stub_announce() {
  local fn="$1"; shift
  printf '[quorum-stub] %s' "$fn"
  for arg in "$@"; do printf ' %q' "$arg"; done
  printf '  reason='
  if [[ -z "${QUORUM_API_KEY:-}" ]]; then
    printf 'QUORUM_API_KEY-missing'
  else
    printf 'POLITICIAN_DRY_RUN=true'
  fi
  printf '\n'
}

# ── shared HTTP helper ───────────────────────────────────────────────────────
_Q_BASE="${QUORUM_API_BASE:-https://www.quorum.us/api/v1}"
_q_curl() {
  local method="$1" path="$2"; shift 2
  curl -sS -X "$method" \
    -H "Api-Key: ${QUORUM_API_KEY}" \
    -H "Content-Type: application/json" \
    "${_Q_BASE}${path}" "$@"
}

# ── public API ───────────────────────────────────────────────────────────────

# quorum_search_bill <keyword>
#   Search bills (federal + state) by keyword.
#   Free fallback: pol_congress_search_bills (federal only).
quorum_search_bill() {
  local keyword="${1:-artificial intelligence}"
  if _q_stub_mode; then
    _q_stub_announce "quorum_search_bill" "$keyword"
    echo "  free-fallback: source $SKILL/scripts/lib/api_clients.sh && pol_congress_search_bills '$keyword'"
    return 0
  fi
  _q_curl GET "/bills/?q=$(printf '%s' "$keyword" | jq -sRr @uri)"
}

# quorum_legislator_voting_record <id>
#   Get voting record for a legislator. id format: Quorum's internal id, OR
#   bioguide id if Quorum has the cross-walk loaded.
#   Free fallback: govtrack.us per-member URL (parse HTML) or
#                  https://api.congress.gov/v3/member/<bioguide>/votes
quorum_legislator_voting_record() {
  local id="${1:-}"
  if [[ -z "$id" ]]; then
    echo "[quorum_legislator_voting_record] ERROR: id required" >&2
    return 2
  fi
  if _q_stub_mode; then
    _q_stub_announce "quorum_legislator_voting_record" "$id"
    echo "  free-fallback: https://www.govtrack.us/congress/members/${id}"
    echo "  api-fallback:  https://api.congress.gov/v3/member/${id}/sponsored-legislation?api_key=\$CONGRESS_GOV_API_KEY"
    return 0
  fi
  _q_curl GET "/people/${id}/votes/"
}

# quorum_lookup_staffer <office>
#   Look up congressional staffer directory for an office.
#   office format: "us-senate-MN" or bioguide id of the member.
#   Free fallback: NONE that's reliable. Legistorm ($499/yr) or manual.
quorum_lookup_staffer() {
  local office="${1:-}"
  if [[ -z "$office" ]]; then
    echo "[quorum_lookup_staffer] ERROR: office required" >&2
    return 2
  fi
  if _q_stub_mode; then
    _q_stub_announce "quorum_lookup_staffer" "$office"
    echo "  no-free-equivalent: closest is legistorm.com (paid \$499/yr)"
    echo "  manual-fallback:    member's official website + LinkedIn search"
    return 0
  fi
  _q_curl GET "/staff/?office=$(printf '%s' "$office" | jq -sRr @uri)"
}

# Health check.
quorum_self_check() {
  _q_load_env
  printf 'quorum.sh wrapper health:\n'
  printf '  QUORUM_API_KEY:     %s\n' \
    "$([[ -n "${QUORUM_API_KEY:-}" ]] && echo set || echo unset)"
  printf '  POLITICIAN_DRY_RUN: %s\n' "${POLITICIAN_DRY_RUN:-true}"
  printf '  effective mode:     %s\n' "$(_q_stub_mode && echo STUB || echo LIVE)"
}
