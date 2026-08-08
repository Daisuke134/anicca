#!/usr/bin/env bash
set -euo pipefail

# Static contract tests for the real-provider Maestro harness. This script is
# intentionally independent of a simulator, a Google account, and any bearer
# token. It only checks that the executable flows can be run against a
# pre-authorized isolated staging tenant without manufacturing provider truth.

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

for flow in \
  config.yaml \
  preauthorized-bootstrap-chat.yaml \
  english-onboarding-route.yaml \
  japanese-onboarding-route.yaml \
  push-deep-link.yaml \
  staging-seed-and-cleanup.sh; do
  require_file "$flow"
done

for flow in preauthorized-bootstrap-chat.yaml english-onboarding-route.yaml japanese-onboarding-route.yaml push-deep-link.yaml; do
  require_text "$flow" 'appId: ai.anicca.life-manager'
  require_text "$flow" 'STAGING_SESSION_ID'
  if grep -Eq '^[[:space:]]*-[[:space:]]*(wait|clearState|clearKeychain):' "$ROOT_DIR/$flow"; then
    fail "$flow: executable flow uses a static wait or destroys the pre-authorized keychain"
  fi
  if grep -Eq '^[[:space:]]*-[[:space:]]*openLink:[[:space:]]*\$\{STAGING_CALLBACK_URL\}' "$ROOT_DIR/$flow"; then
    fail "$flow: executable flow crosses the external Google consent boundary"
  fi
  if grep -Eiq 'accessToken|refreshToken|authorization:[[:space:]]*bearer|bearer[[:space:]]+[A-Za-z0-9._-]{12,}' "$ROOT_DIR/$flow"; then
    fail "$flow: bearer/session secret appears in flow"
  fi
done

for id in chat.list chat.refresh; do
  require_text preauthorized-bootstrap-chat.yaml "id: \"$id\""
done

for flow in english-onboarding-route.yaml japanese-onboarding-route.yaml; do
  for id in phone.skip analysis.phase route.showDetails route.detail.close chat.upgrade paywall.continueFree chat.settings; do
    require_text "$flow" "id: \"$id\""
  done
  require_text "$flow" 'ROUTE_MESSAGE_ID'
  require_text "$flow" 'assertNotVisible:'
done

require_text push-deep-link.yaml 'PUSH_MESSAGE_ID'
# shellcheck disable=SC2016 # the literal is the Maestro runtime interpolation
require_text push-deep-link.yaml 'chat.message.${PUSH_MESSAGE_ID}'
require_text push-deep-link.yaml 'chat.refresh'

require_text staging-seed-and-cleanup.sh 'life-call-staging-staging.up.railway.app'
require_text staging-seed-and-cleanup.sh 'ulhsqqkyejzvqgoyjwte'
require_text staging-seed-and-cleanup.sh 'production configuration is forbidden'
require_text staging-seed-and-cleanup.sh 'LM_STAGING_CLEANUP_CONFIRM'

if command -v maestro >/dev/null 2>&1; then
  for flow in \
    preauthorized-bootstrap-chat.yaml \
    english-onboarding-route.yaml \
    japanese-onboarding-route.yaml \
    push-deep-link.yaml; do
    maestro check-syntax "$ROOT_DIR/$flow" >/dev/null
  done
fi

echo "PASS: real-provider Maestro harness static contracts"
