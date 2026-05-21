#!/usr/bin/env bash
set -euo pipefail

# Seeds an APNs-style problem delivery via internal endpoint and opens it via deep link.
#
# Required env:
#   INTERNAL_API_TOKEN
#
# Optional env:
#   ANICCA_API_BASE (default: https://anicca-proxy-staging.up.railway.app/api)
#   DEVICE_ID (default: UI_TEST_DEVICE_ID)
#   PROBLEM_TYPE (default: anxiety)
#   SCHEDULED_TIME (default: 12:15)

API_BASE="${ANICCA_API_BASE:-https://anicca-proxy-staging.up.railway.app/api}"
DEVICE_ID="${DEVICE_ID:-UI_TEST_DEVICE_ID}"
PROBLEM_TYPE="${PROBLEM_TYPE:-anxiety}"
SCHEDULED_TIME="${SCHEDULED_TIME:-12:15}"

if [[ -z "${INTERNAL_API_TOKEN:-}" ]]; then
  echo "INTERNAL_API_TOKEN is required" >&2
  exit 1
fi

json="$(curl -sS -X POST "${API_BASE}/admin/test/nudge-delivery" \
  -H "Authorization: Bearer ${INTERNAL_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "{\"deviceId\":\"${DEVICE_ID}\",\"problemType\":\"${PROBLEM_TYPE}\",\"scheduledTime\":\"${SCHEDULED_TIME}\"}")"

id="$(echo "$json" | jq -r '.id // empty')"
if [[ -z "$id" ]]; then
  echo "Failed to seed delivery. Response:" >&2
  echo "$json" >&2
  exit 2
fi

echo "Seeded delivery id=${id}"
xcrun simctl openurl booted "anicca://debug/pushTap?messageId=${id}"

