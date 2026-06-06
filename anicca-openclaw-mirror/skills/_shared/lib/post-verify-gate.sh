#!/usr/bin/env bash
# Anicca v3.2 post-verify-gate — fail-closed verification AFTER any social post.
#
# pvg_verify --platform <X|TikTok|YouTube> \
#            --post-id <id> \
#            --expected-caption-head <string-of-~40-chars> \
#            --expected-language <2-letter> \
#            --timeout <seconds, default 300> \
#            --max-retries <int, default 2>
#
# Exit codes:
#   0 verified live
#   6 caption mismatch
#   7 lang mismatch
#   8 account mismatch (reserved; verifier dispatch covers)
#   9 asset integrity
#  10 timeout / not-found
#
# On failure, attempts Slack URGENT via SLACK_BOT_TOKEN. Does NOT throw if
# Slack is unavailable — the non-zero exit IS the alert; Slack is best-effort.

source "$(dirname "${BASH_SOURCE[0]}")/verify-tiktok.sh"
source "$(dirname "${BASH_SOURCE[0]}")/verify-x.sh"

pvg_verify() {
  local platform="" post_id="" head="" lang=""
  local timeout=300 max_retries=2

  while [ $# -gt 0 ]; do
    case "$1" in
      --platform)              platform="$2"; shift 2;;
      --post-id)               post_id="$2"; shift 2;;
      --expected-caption-head) head="$2"; shift 2;;
      --expected-language)     lang="$2"; shift 2;;
      --timeout)               timeout="$2"; shift 2;;
      --max-retries)           max_retries="$2"; shift 2;;
      *) echo "pvg_verify: unknown flag $1" >&2; return 99;;
    esac
  done

  for need in platform post_id head lang; do
    if [ -z "${!need}" ]; then
      echo "pvg_verify: missing required --$need" >&2
      return 99
    fi
  done

  local attempt=0 rc=10
  local backoff=30
  while [ "$attempt" -le "$max_retries" ]; do
    case "$platform" in
      X|x|twitter)
        vx_check "$post_id" "$head" "$lang"
        rc=$?
        ;;
      TikTok|tiktok)
        vt_check "$post_id" "$head" "$lang"
        rc=$?
        ;;
      *)
        echo "pvg_verify: unsupported platform $platform" >&2
        return 99
        ;;
    esac

    if [ "$rc" -eq 0 ]; then
      return 0
    fi

    # Hard failures: caption / lang / account / asset — do NOT retry
    case "$rc" in
      6|7|8|9) _pvg_alert "$platform" "$post_id" "$rc" "hard-fail"; return "$rc";;
    esac

    # rc=10 timeout/not-found — retry
    attempt=$((attempt + 1))
    if [ "$attempt" -le "$max_retries" ]; then
      sleep "$backoff"
      backoff=$((backoff * 2))
    fi
  done

  _pvg_alert "$platform" "$post_id" "$rc" "retry-exhausted"
  return "$rc"
}

_pvg_alert() {
  local platform="$1" post_id="$2" rc="$3" tag="$4"
  local chan="${SLACK_METRICS_CHANNEL:-C091G3PKHL2}"
  local msg=":rotating_light: pvg_verify $tag platform=$platform post_id=$post_id exit=$rc"
  echo "$msg" >&2
  if [ -n "${SLACK_BOT_TOKEN:-}" ]; then
    local payload
    payload="$(jq -nc --arg c "$chan" --arg t "$msg" '{channel:$c,text:$t}')"
    curl -sS -X POST -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
      -H 'Content-Type: application/json; charset=utf-8' \
      --data "$payload" \
      https://slack.com/api/chat.postMessage >/dev/null 2>&1 || true
  fi
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  pvg_verify "$@"
  exit $?
fi
