#!/usr/bin/env bash
set -euo pipefail

# The helper is deliberately read-only for `seed`: it verifies a real,
# pre-authorized staging tenant. It never creates a fake Calendar event,
# injects an outbox row, or manufactures a session. `cleanup` is the only
# mutating command and requires an explicit disposable-staging confirmation.

readonly STAGING_HOST="life-call-staging-staging.up.railway.app"
readonly STAGING_SUPABASE_REF="ulhsqqkyejzvqgoyjwte"
readonly STAGING_SUPABASE_URL="https://${STAGING_SUPABASE_REF}.supabase.co"

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

require_db_cleanup_inputs() {
  [[ -n "${LM_STAGING_BEARER_TOKEN:-}" ]] \
    || fail "LM_STAGING_BEARER_TOKEN is required for the exact receipt readback"
  [[ -n "${LM_STAGING_DB_SERVICE_ROLE_KEY:-}" ]] \
    || fail "LM_STAGING_DB_SERVICE_ROLE_KEY is required only in the cleanup shell; it is never written to the flow"
  [[ -n "${LM_STAGING_UID:-}" ]] \
    || fail "LM_STAGING_UID is required to scope database-only cleanup"
  [[ -n "${LM_TRAVEL_RECEIPT_MESSAGE_ID:-}" ]] \
    || fail "LM_TRAVEL_RECEIPT_MESSAGE_ID is required to bind cleanup to one confirmed receipt"
  [[ -n "${LM_TRAVEL_PROVIDER_EVENT_ID:-}" ]] \
    || fail "LM_TRAVEL_PROVIDER_EVENT_ID is required from the confirmed receipt readback"
  [[ "${LM_TRAVEL_PROVIDER_EVENT_ID}" =~ ^[a-v0-9]{5,1024}$ ]] \
    || fail "LM_TRAVEL_PROVIDER_EVENT_ID is not a valid opaque Google event ID"
  [[ -n "${LM_STAGING_COMPOSIO_API_KEY:-}" ]] \
    || fail "LM_STAGING_COMPOSIO_API_KEY is required only in the cleanup shell"
  [[ -n "${LM_STAGING_CONNECTED_ACCOUNT_ID:-}" ]] \
    || fail "LM_STAGING_CONNECTED_ACCOUNT_ID is required to target the exact connected account"
  [[ "${LM_STAGING_SUPABASE_URL:-}" == "$STAGING_SUPABASE_URL" ]] \
    || fail "database cleanup must target the isolated staging Supabase URL"
  [[ "${LM_STAGING_UID}" =~ ^[A-Za-z0-9_-]+$ ]] \
    || fail "LM_STAGING_UID contains characters outside the opaque staging UID format"
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

  local bootstrap messages mode locale route_id receipt_id failure_id
  bootstrap="$(api_get /bootstrap)" || fail "staging bootstrap read failed"
  mode="${LM_STAGING_VERIFY_MODE:-analysis}"
  locale="${LM_STAGING_EXPECTED_LOCALE:-en}"
  [[ "$locale" == "en" || "$locale" == "ja" ]] || fail "expected locale must be en or ja"
  [[ "$mode" == "analysis" || "$mode" == "chat" || "$mode" == "failure" ]] \
    || fail "verify mode must be analysis, chat, or failure"

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
  elif [[ "$mode" == "chat" ]]; then
    route_id="${LM_ROUTE_MESSAGE_ID:-}"
    [[ -n "$route_id" ]] || fail "LM_ROUTE_MESSAGE_ID is required in chat verification mode"
    receipt_id="${LM_TRAVEL_RECEIPT_MESSAGE_ID:-}"
    [[ -n "$receipt_id" ]] || fail "LM_TRAVEL_RECEIPT_MESSAGE_ID is required in chat verification mode"
    messages="$(api_get /chat)" || fail "staging chat read failed"
    jq -e --arg route_id "$route_id" --arg receipt_id "$receipt_id" \
      '.messages
        | any(.[]; .id == $route_id and .type == "route" and .route.status == "route_ready")
        and any(.[]; .id == $receipt_id and .semanticKey == "chat.travel_block_confirmed")' \
      <<<"$messages" >/dev/null \
      || fail "staging chat has no provider-backed route and confirmed travel receipt with the requested IDs"
  else
    failure_id="${LM_TRAVEL_FAILURE_MESSAGE_ID:-}"
    [[ -n "$failure_id" ]] || fail "LM_TRAVEL_FAILURE_MESSAGE_ID is required in failure verification mode"
    messages="$(api_get /chat)" || fail "staging chat read failed"
    jq -e --arg failure_id "$failure_id" \
      '.messages | any(.[]; .id == $failure_id and .semanticKey == "chat.travel_block_not_added")' \
      <<<"$messages" >/dev/null \
      || fail "staging chat has no provider-backed not-added travel receipt with the requested ID"
  fi

  echo "PASS: pre-authorized isolated staging seed verified (mode=${mode}, locale=${locale})"
}

provider_proxy_request() {
  local method="$1"
  local endpoint="$2"
  local output_file="$3"
  local payload
  payload="$(jq -cn \
    --arg account "$LM_STAGING_CONNECTED_ACCOUNT_ID" \
    --arg endpoint "$endpoint" \
    --arg method "$method" \
    '{connected_account_id: $account, endpoint: $endpoint, method: $method}')"
  curl --silent --show-error --retry 1 \
    --output "$output_file" \
    --write-out '%{http_code}' \
    -X POST \
    -H "Accept: application/json" \
    -H "Content-Type: application/json" \
    -H "x-api-key: ${LM_STAGING_COMPOSIO_API_KEY}" \
    --data "$payload" \
    "https://backend.composio.dev/api/v3.1/tools/execute/proxy"
}

verify_receipt_for_cleanup() {
  local messages
  messages="$(api_get /chat)" || fail "staging chat read failed before provider cleanup"
  jq -e \
    --arg receipt_id "$LM_TRAVEL_RECEIPT_MESSAGE_ID" \
    --arg provider_event_id "$LM_TRAVEL_PROVIDER_EVENT_ID" \
    '.messages | any(.[];
      .id == $receipt_id
      and .semanticKey == "chat.travel_block_confirmed"
      and ((.args.providerEventId // .args.provider_event_id) == $provider_event_id)
    )' \
    <<<"$messages" >/dev/null \
    || fail "cleanup receipt does not prove the exact requested provider event ID"
}

delete_exact_provider_event() {
  local endpoint="/calendar/v3/calendars/primary/events/${LM_TRAVEL_PROVIDER_EVENT_ID}"
  local delete_response readback_response delete_http readback_http
  delete_response="$(mktemp -t life-manager-travel-delete.XXXXXX)"
  readback_response="$(mktemp -t life-manager-travel-readback.XXXXXX)"
  trap 'rm -f "$delete_response" "$readback_response"' RETURN

  delete_http="$(provider_proxy_request DELETE "$endpoint" "$delete_response")" \
    || fail "provider event cleanup request failed"
  [[ "$delete_http" == "200" ]] \
    || fail "provider event cleanup proxy returned HTTP ${delete_http}"
  jq -e '.status == 204' "$delete_response" >/dev/null \
    || fail "provider cleanup did not confirm a 204 deletion for the exact event ID"

  readback_http="$(provider_proxy_request GET "$endpoint" "$readback_response")" \
    || fail "provider event readback failed after cleanup"
  [[ "$readback_http" == "200" ]] \
    || fail "provider event readback proxy returned HTTP ${readback_http}"
  jq -e '.status == 404 and (.data == null or .data == {})' "$readback_response" >/dev/null \
    || fail "provider event cleanup readback did not prove the exact event is absent"
  rm -f "$delete_response" "$readback_response"
  trap - RETURN
}

cleanup_seed() {
  require_staging
  require_db_cleanup_inputs
  command -v jq >/dev/null 2>&1 || fail "jq is required for exact provider cleanup"
  [[ "${LM_STAGING_CLEANUP_CONFIRM:-}" == "DELETE_STAGING_ONLY" ]] \
    || fail "cleanup requires LM_STAGING_CLEANUP_CONFIRM=DELETE_STAGING_ONLY"

  # Bind cleanup to the exact provider event named by the confirmed receipt,
  # delete only that event, and prove a narrow 404 readback before touching DB rows.
  verify_receipt_for_cleanup
  delete_exact_provider_event

  # DB cleanup is deliberately explicit. It removes mobile rows for the
  # supplied staging UID and never calls the mobile account-deletion route or a
  # provider disconnect/revoke operation on the shared pre-authorized account.
  local table status
  for table in \
    lm_mobile_deletion_receipts \
    lm_mobile_idempotency \
    lm_mobile_oauth_states \
    lm_mobile_calendar_connections \
    lm_mobile_sessions \
    lm_mobile_analysis_states \
    lm_mobile_outbox \
    lm_mobile_questions \
    lm_mobile_call_attempts \
    lm_mobile_devices \
    lm_route_cache \
    lm_travel_log \
    lm_users; do
    status="$(curl --silent --show-error --retry 1 --output /dev/null --write-out '%{http_code}' \
      -X DELETE \
      -H "Accept: application/json" \
      -H "Authorization: Bearer ${LM_STAGING_DB_SERVICE_ROLE_KEY}" \
      -H "apikey: ${LM_STAGING_DB_SERVICE_ROLE_KEY}" \
      -H "Prefer: return=minimal" \
      "${LM_STAGING_SUPABASE_URL}/rest/v1/${table}?uid=eq.${LM_STAGING_UID}")" \
      || fail "staging database cleanup request failed for ${table}"
    [[ "$status" == "200" || "$status" == "204" ]] \
      || fail "staging database cleanup returned HTTP ${status} for ${table}"
  done
  echo "PASS: exact travel provider event was deleted and mobile rows for the isolated staging UID were deleted; provider connection was untouched"
}

case "${1:-}" in
  seed|verify-seed) verify_seed ;;
  cleanup) cleanup_seed ;;
  *)
    echo "usage: $0 seed|cleanup" >&2
    exit 2
    ;;
esac
