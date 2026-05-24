#!/usr/bin/env bash
# phone2action.sh — wrapper for Phone2Action (now part of Quorum) advocacy API.
#
# Phone2Action: legislative-tracker subscriptions, action alerts, advocacy-
# network management. As of 2026-05 the product is bundled with Quorum's
# stack but retains its own API surface at app.phone2action.com.
#
# Docs: https://app.phone2action.com/api/v3/docs (account login required).
#
# Pricing reality (2026-05): Phone2Action Lite begins at $1k/mo; full
# advocacy stack typically $3k-$8k/mo depending on contact volume.
# Until we sign up, every function in this file is STUB-ONLY:
# it prints what it WOULD do and exits 0. No real HTTP calls.

# ── env load ─────────────────────────────────────────────────────────────────
_p2a_loaded=0
_p2a_load_env() {
  [[ "$_p2a_loaded" == "1" ]] && return 0
  local envf="${OPENCLAW_ENV:-$HOME/.openclaw/.env}"
  if [[ -f "$envf" ]]; then
    set -a; source "$envf"; set +a
  fi
  _p2a_loaded=1
}

# ── stub gate ────────────────────────────────────────────────────────────────
# Returns 0 if we're in stub mode (no real call should be made), 1 if LIVE.
_p2a_stub_mode() {
  _p2a_load_env
  if [[ -z "${PHONE2ACTION_API_KEY:-}" ]]; then
    return 0  # stub
  fi
  if [[ "${POLITICIAN_DRY_RUN:-true}" == "true" ]]; then
    return 0  # stub
  fi
  return 1  # LIVE
}

_p2a_stub_announce() {
  local fn="$1"; shift
  printf '[p2a-stub] %s' "$fn"
  for arg in "$@"; do printf ' %q' "$arg"; done
  printf '  reason='
  if [[ -z "${PHONE2ACTION_API_KEY:-}" ]]; then
    printf 'PHONE2ACTION_API_KEY-missing'
  else
    printf 'POLITICIAN_DRY_RUN=true'
  fi
  printf '\n'
}

# ── shared HTTP helper (only used in LIVE mode) ──────────────────────────────
_P2A_BASE="${PHONE2ACTION_API_BASE:-https://app.phone2action.com/api/v3}"
_p2a_curl() {
  local method="$1" path="$2"; shift 2
  curl -sS -X "$method" \
    -H "Authorization: Bearer ${PHONE2ACTION_API_KEY}" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    "${_P2A_BASE}${path}" "$@"
}

# ── public API ───────────────────────────────────────────────────────────────

# p2a_track_bill <bill_id>
#   Subscribe to legislative-tracker updates for a bill (push to webhook on status change).
#   bill_id format: "us-119-hr-1234" or congress.gov canonical bill id.
p2a_track_bill() {
  local bill_id="${1:-}"
  if [[ -z "$bill_id" ]]; then
    echo "[p2a_track_bill] ERROR: bill_id required" >&2
    return 2
  fi
  if _p2a_stub_mode; then
    _p2a_stub_announce "p2a_track_bill" "$bill_id"
    return 0
  fi
  _p2a_curl POST "/bills/track" --data "$(jq -n --arg id "$bill_id" '{bill_id:$id}')"
}

# p2a_send_alert <legislator_id> <message_template_path>
#   Send a constituent action alert to a legislator's office on behalf of
#   our advocacy network. message_template_path is a local file.
p2a_send_alert() {
  local legislator_id="${1:-}" template_path="${2:-}"
  if [[ -z "$legislator_id" || -z "$template_path" ]]; then
    echo "[p2a_send_alert] ERROR: legislator_id + template_path required" >&2
    return 2
  fi
  if [[ ! -f "$template_path" ]]; then
    echo "[p2a_send_alert] ERROR: template not found: $template_path" >&2
    return 2
  fi
  if _p2a_stub_mode; then
    _p2a_stub_announce "p2a_send_alert" "$legislator_id" "$template_path"
    echo "  template_preview: $(head -c 80 "$template_path" | tr '\n' ' ')..."
    return 0
  fi
  local body
  body="$(jq -Rs --arg lid "$legislator_id" '{legislator_id:$lid, message:.}' < "$template_path")"
  _p2a_curl POST "/alerts/send" --data "$body"
}

# p2a_pull_action_history [since_iso8601]
#   Pull our advocacy-network's action history (constituent {{profile.lateness.stakeholders.channel}}s sent,
#   calls made, etc.) since the given timestamp (default: 7 days ago).
p2a_pull_action_history() {
  local since="${1:-$(date -u -d '7 days ago' +%Y-%m-%dT00:00:00Z 2>/dev/null || date -u -v-7d +%Y-%m-%dT00:00:00Z)}"
  if _p2a_stub_mode; then
    _p2a_stub_announce "p2a_pull_action_history" "$since"
    return 0
  fi
  _p2a_curl GET "/actions?since=$(printf '%s' "$since" | jq -sRr @uri)"
}

# Quick health check for the wrapper itself (always works, never calls API).
p2a_self_check() {
  _p2a_load_env
  printf 'phone2action.sh wrapper health:\n'
  printf '  PHONE2ACTION_API_KEY: %s\n' \
    "$([[ -n "${PHONE2ACTION_API_KEY:-}" ]] && echo set || echo unset)"
  printf '  POLITICIAN_DRY_RUN:   %s\n' "${POLITICIAN_DRY_RUN:-true}"
  printf '  effective mode:       %s\n' "$(_p2a_stub_mode && echo STUB || echo LIVE)"
}
