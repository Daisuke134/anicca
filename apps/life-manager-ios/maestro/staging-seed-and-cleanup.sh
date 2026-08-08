#!/usr/bin/env bash
set -euo pipefail

# The helper is deliberately read-only for `seed`: it verifies a real,
# pre-authorized staging tenant. It never creates a fake Calendar event,
# injects an outbox row, or manufactures a session. `cleanup` is the only
# mutating command and requires an explicit disposable-staging confirmation.

readonly STAGING_HOST="life-call-staging-staging.up.railway.app"
readonly STAGING_SUPABASE_REF="ulhsqqkyejzvqgoyjwte"

fail() {
  echo "staging harness error: $*" >&2
  exit 1
}

require_staging() {
  local api="${LM_STAGING_API_BASE_URL:-}"
  local ref="${LM_STAGING_SUPABASE_REF:-}"
  [[ -n "$api" ]] || fail "LM_STAGING_API_BASE_URL is required"
  [[ -n "$ref" ]] || fail "LM_STAGING_SUPABASE_REF is required"
  [[ "$api" == "https://${STAGING_HOST}/api/mobile/v1" ]] \
    || fail "production configuration is forbidden; API must be the isolated staging mobile endpoint"
  [[ "$ref" == "$STAGING_SUPABASE_REF" ]] \
    || fail "production configuration is forbidden; Supabase ref is not the isolated staging project"
  [[ "$api" != *"life-call-production"* ]] \
    || fail "production configuration is forbidden"
}

require_token() {
  [[ -n "${LM_STAGING_BEARER_TOKEN:-}" ]] \
    || fail "LM_STAGING_BEARER_TOKEN is required only in the calling shell; it is never written to the flow"
}

api_get() {
  local path="$1"
  curl --fail --silent --show-error --retry 2 \
    -H "Accept: application/json" \
    -H "Authorization: Bearer ${LM_STAGING_BEARER_TOKEN}" \
    "${LM_STAGING_API_BASE_URL}${path}"
}

verify_seed() {
  require_staging
  require_token
  command -v jq >/dev/null 2>&1 || fail "jq is required for fail-closed readback"

  local bootstrap messages mode locale route_id
  bootstrap="$(api_get /bootstrap)" || fail "staging bootstrap read failed"
  mode="${LM_STAGING_VERIFY_MODE:-analysis}"
  locale="${LM_STAGING_EXPECTED_LOCALE:-en}"
  [[ "$locale" == "en" || "$locale" == "ja" ]] || fail "expected locale must be en or ja"
  [[ "$mode" == "analysis" || "$mode" == "chat" ]] || fail "verify mode must be analysis or chat"

  jq -e \
    --arg locale "$locale" \
    '.calendar.status == "connected"
      and (.user.name | type == "string" and length > 0)
      and .user.home.status == "ready"
      and .user.phone.status == "missing"
      and .user.productLocale == $locale' \
    <<<"$bootstrap" >/dev/null \
    || fail "staging seed is not a connected, named, home-ready, phone-null tenant in the requested locale"

  if [[ "$mode" == "analysis" ]]; then
    jq -e '.analysis.status == "idle"' <<<"$bootstrap" >/dev/null \
      || fail "staging seed is not waiting for the real next-event analysis"
  else
    route_id="${LM_ROUTE_MESSAGE_ID:-}"
    [[ -n "$route_id" ]] || fail "LM_ROUTE_MESSAGE_ID is required in chat verification mode"
    messages="$(api_get /chat)" || fail "staging chat read failed"
    jq -e --arg route_id "$route_id" \
      '.messages | any(.[]; .id == $route_id and .type == "route" and .route.status == "route_ready")' \
      <<<"$messages" >/dev/null \
      || fail "staging chat has no provider-backed route message with the requested ID"
  fi

  echo "PASS: pre-authorized isolated staging seed verified (mode=${mode}, locale=${locale})"
}

cleanup_seed() {
  require_staging
  require_token
  [[ "${LM_STAGING_CLEANUP_CONFIRM:-}" == "DELETE_STAGING_ONLY" ]] \
    || fail "cleanup requires LM_STAGING_CLEANUP_CONFIRM=DELETE_STAGING_ONLY"
  command -v uuidgen >/dev/null 2>&1 || fail "uuidgen is required for an idempotent cleanup request"

  local response_file status
  response_file="$(mktemp -t life-manager-maestro-cleanup.XXXXXX)"
  trap 'rm -f "$response_file"' EXIT
  status="$(curl --silent --show-error --retry 1 --output "$response_file" --write-out '%{http_code}' \
    -X DELETE \
    -H "Accept: application/json" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${LM_STAGING_BEARER_TOKEN}" \
    -H "Idempotency-Key: $(uuidgen)" \
    --data '{"confirmed":true}' \
    "${LM_STAGING_API_BASE_URL}/account")" \
    || fail "staging account cleanup request failed"
  [[ "$status" == "200" ]] || fail "staging cleanup returned HTTP ${status}"
  echo "PASS: disposable isolated staging account cleanup completed"
}

case "${1:-}" in
  seed|verify-seed) verify_seed ;;
  cleanup) cleanup_seed ;;
  *)
    echo "usage: $0 seed|cleanup" >&2
    exit 2
    ;;
esac
