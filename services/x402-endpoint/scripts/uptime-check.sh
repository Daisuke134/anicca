#!/bin/bash
# anicca-x402-uptime-check — hourly liveness probe for the x402 endpoint.
# If localhost:8403/health does not return 200 within 10s, kickstart both the
# server and tunnel plists so the service self-heals.
#
# Invoked by ~/.openclaw/cron/jobs.json → name="anicca-x402-uptime-check".
# Output is captured by the openclaw gateway and announced into Slack #metrics.

set -u

LOCAL_HEALTH="http://localhost:8403/health"
URL_FILE="${HOME}/.openclaw/state/anicca_x402_url.txt"
STATE_LOG="${HOME}/.openclaw/state/anicca_x402_uptime.jsonl"
UID_VAL="$(id -u)"
SERVER_LABEL="ai.anicca.x402-endpoint"
TUNNEL_LABEL="ai.anicca.x402-tunnel"

mkdir -p "$(dirname "${STATE_LOG}")"

stamp="$(date -u +%FT%TZ)"
http_local=$(/usr/bin/curl -sS -m 10 -o /dev/null -w '%{http_code}' "${LOCAL_HEALTH}" 2>/dev/null || echo "000")

public_url=""
http_public="000"
if [ -s "${URL_FILE}" ]; then
  public_url="$(cat "${URL_FILE}")"
  http_public=$(/usr/bin/curl -sS -m 10 -o /dev/null -w '%{http_code}' "${public_url}/health" 2>/dev/null || echo "000")
fi

action="none"
if [ "${http_local}" != "200" ]; then
  /bin/launchctl kickstart -k "gui/${UID_VAL}/${SERVER_LABEL}" >/dev/null 2>&1
  action="server_kicked"
fi
if [ "${http_public}" != "200" ] && [ -n "${public_url}" ]; then
  /bin/launchctl kickstart -k "gui/${UID_VAL}/${TUNNEL_LABEL}" >/dev/null 2>&1
  if [ "${action}" = "none" ]; then action="tunnel_kicked"; else action="${action}+tunnel_kicked"; fi
fi

line="{\"ts\":\"${stamp}\",\"local\":${http_local},\"public\":${http_public},\"url\":\"${public_url}\",\"action\":\"${action}\"}"
printf '%s\n' "${line}" >>"${STATE_LOG}"
printf '%s\n' "${line}"

# Exit 0 even if we kicked — the kickstart is the remediation, not a failure.
exit 0
