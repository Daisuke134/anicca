#!/usr/bin/env bash
set -euo pipefail

# Static contract tests for the real-provider Maestro harness. This script is
# intentionally independent of a simulator, a Google account, and any bearer
# token. It checks the executable onboarding boundary and the pre-authorized
# isolated staging flows without manufacturing provider truth.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fail() {
  echo "FAIL: $*" >&2
  exit 1
}

require_file() {
  [[ -f "$ROOT_DIR/$1" ]] || fail "missing harness file: $1"
}

require_text() {
  local file="$1"
  local needle="$2"
  grep -Fq -- "$needle" "$ROOT_DIR/$file" || fail "$file: missing: $needle"
}

# Maestro IDs are nested under executable commands, but the contract must not
# be satisfiable by a comment that merely mentions an ID. Strip YAML inline
# comments before requiring command text; values used by this harness contain
# no literal hash, so a whitespace-delimited comment marker is unambiguous.
active_lines_from_path() {
  sed -E 's/[[:space:]]+#.*$//' "$1" | awk '
    !/^[[:space:]]*#/ && NF
  '
}

active_lines() {
  active_lines_from_path "$ROOT_DIR/$1"
}

require_active_text() {
  local file="$1"
  local needle="$2"
  active_lines "$file" | grep -F -- "$needle" >/dev/null \
    || fail "$file: missing executable command text: $needle"
}

require_absent_active_text() {
  local file="$1"
  local needle="$2"
  if active_lines "$file" | grep -F -- "$needle" >/dev/null; then
    fail "$file: forbidden executable command text: $needle"
  fi
}

require_active_id() {
  local file="$1"
  local identifier="$2"
  require_active_text "$file" "id: \"$identifier\""
}

for flow in \
  config.yaml \
  preauthorized-bootstrap-chat.yaml \
  preauthorized-travel-failure.yaml \
  english-onboarding-route.yaml \
  japanese-onboarding-route.yaml \
  push-deep-link.yaml \
  staging-seed-and-cleanup.sh \
  harness-inline-comment-bypass.txt; do
  require_file "$flow"
done

for flow in preauthorized-bootstrap-chat.yaml preauthorized-travel-failure.yaml english-onboarding-route.yaml japanese-onboarding-route.yaml push-deep-link.yaml; do
  require_active_text "$flow" 'appId: ai.anicca.life-manager'
  if grep -Eiq 'accessToken|refreshToken|authorization:[[:space:]]*bearer|bearer[[:space:]]+[A-Za-z0-9._-]{12,}' "$ROOT_DIR/$flow"; then
    fail "$flow: bearer/session secret appears in flow"
  fi
done

# The bootstrap and push flows run after the one-time external consent
# boundary. They must use a real isolated staging session and keep its
# keychain intact.
for flow in preauthorized-bootstrap-chat.yaml preauthorized-travel-failure.yaml push-deep-link.yaml; do
  require_active_text "$flow" 'STAGING_SESSION_ID'
  require_absent_active_text "$flow" 'clearState:'
  require_absent_active_text "$flow" 'clearKeychain:'
  require_absent_active_text "$flow" 'openLink: ${STAGING_CALLBACK_URL}'
done

for id in chat.list chat.refresh; do
  require_active_id preauthorized-bootstrap-chat.yaml "$id"
done
require_active_text preauthorized-bootstrap-chat.yaml 'TRAVEL_RECEIPT_MESSAGE_ID'
require_active_id preauthorized-bootstrap-chat.yaml 'calendar.travelBlock.confirmed.${TRAVEL_RECEIPT_MESSAGE_ID}'
require_active_text preauthorized-travel-failure.yaml 'TRAVEL_FAILURE_MESSAGE_ID'
require_active_id preauthorized-travel-failure.yaml 'calendar.travelBlock.notAdded.${TRAVEL_FAILURE_MESSAGE_ID}'

for flow in english-onboarding-route.yaml japanese-onboarding-route.yaml; do
  require_active_text "$flow" 'STAGING_CALLBACK_URL'
  require_active_text "$flow" 'PROFILE_NAME'
  require_active_text "$flow" 'PROFILE_HOME'
  require_active_text "$flow" 'clearState: true'
  require_active_text "$flow" 'clearKeychain: true'
  require_active_text "$flow" 'openLink: ${STAGING_CALLBACK_URL}'
  for id in welcome.connectCalendar profile.name profile.home profile.continue phone.skip analysis.phase route.showDetails route.detail.close chat.upgrade paywall.continueFree chat.settings; do
    require_active_id "$flow" "$id"
  done
  require_active_text "$flow" 'assertNotVisible:'
done

require_active_text push-deep-link.yaml 'PUSH_MESSAGE_ID'
# shellcheck disable=SC2016 # the literal is the Maestro runtime interpolation
require_active_text push-deep-link.yaml 'chat.message.${PUSH_MESSAGE_ID}'
require_active_id push-deep-link.yaml 'chat.refresh'

require_text staging-seed-and-cleanup.sh 'life-call-staging-staging.up.railway.app'
require_text staging-seed-and-cleanup.sh 'ulhsqqkyejzvqgoyjwte'
require_text staging-seed-and-cleanup.sh 'production configuration is forbidden'
require_text staging-seed-and-cleanup.sh 'LM_STAGING_DB_SERVICE_ROLE_KEY'
require_text staging-seed-and-cleanup.sh 'LM_STAGING_SUPABASE_URL'
require_text staging-seed-and-cleanup.sh 'LM_STAGING_COMPOSIO_API_KEY'
require_text staging-seed-and-cleanup.sh 'LM_STAGING_CONNECTED_ACCOUNT_ID'
require_text staging-seed-and-cleanup.sh 'LM_TRAVEL_RECEIPT_MESSAGE_ID'
require_text staging-seed-and-cleanup.sh 'LM_TRAVEL_PROVIDER_EVENT_ID'
require_text staging-seed-and-cleanup.sh 'chat.travel_block_confirmed'
require_text staging-seed-and-cleanup.sh 'LM_TRAVEL_FAILURE_MESSAGE_ID'
require_text staging-seed-and-cleanup.sh 'chat.travel_block_not_added'
require_text staging-seed-and-cleanup.sh 'provider_proxy_request DELETE'
require_text staging-seed-and-cleanup.sh '.status == 404'
require_absent_active_text staging-seed-and-cleanup.sh '/account'
require_text staging-seed-and-cleanup.sh 'LM_STAGING_CLEANUP_CONFIRM'
require_absent_active_text harness-inline-comment-bypass.txt 'BYPASS_ONLY_MARKER'

if command -v maestro >/dev/null 2>&1; then
  for flow in \
    preauthorized-bootstrap-chat.yaml \
    preauthorized-travel-failure.yaml \
    english-onboarding-route.yaml \
    japanese-onboarding-route.yaml \
    push-deep-link.yaml; do
    maestro check-syntax "$ROOT_DIR/$flow" >/dev/null
  done
fi

echo "PASS: real-provider Maestro harness static contracts"
