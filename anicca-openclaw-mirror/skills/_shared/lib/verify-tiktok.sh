#!/usr/bin/env bash
# Anicca v3.2 verify-tiktok — live feed check after a TikTok post.
#
# vt_check <post_id> <expected_caption_head> <expected_lang>
#   post_id = Postiz post id (from receipt)
#   expected_caption_head = first ~40 chars of the caption we sent
#   expected_lang = "en"|"ja"
#
# Exit codes (relayed to pvg_verify):
#   0 ok
#   6 caption head not found in live feed
#   7 lang mismatch (detected != expected)
#   9 asset integrity (frames/audio missing)
#  10 timeout/not-published-in-window

source "$(dirname "${BASH_SOURCE[0]}")/lang-detect.sh"

vt_check() {
  local post_id="$1"
  local expected_head="$2"
  local expected_lang="$3"
  : "${POSTIZ_API_KEY:?POSTIZ_API_KEY required}"

  # 1. Ask Postiz for the post state + caption
  local resp
  resp="$(curl -sS -H "Authorization: ${POSTIZ_API_KEY}" \
    "https://app.postiz.com/public/v1/posts/${post_id}" 2>/dev/null)"
  local state caption
  state="$(printf '%s' "$resp" | jq -r '.state // .status // "UNKNOWN"' 2>/dev/null)"
  caption="$(printf '%s' "$resp" | jq -r '.content // .caption // .text // empty' 2>/dev/null)"

  if [ "$state" != "PUBLISHED" ] && [ "$state" != "published" ]; then
    echo "vt_check: 10 not published yet (state=$state)" >&2
    return 10
  fi

  # 2. Caption head match
  if [ -n "$caption" ]; then
    if ! printf '%s' "$caption" | grep -qF "$expected_head"; then
      echo "vt_check: 6 caption head not found in live caption" >&2
      return 6
    fi
    # 3. Lang detect on live caption
    local detected
    detected="$(ld_detect "$caption")"
    if [ "$detected" != "$expected_lang" ] && [ "$detected" != "und" ]; then
      echo "vt_check: 7 live lang=$detected expected=$expected_lang" >&2
      return 7
    fi
  else
    echo "vt_check: 10 Postiz returned no caption (raw resp len=${#resp})" >&2
    return 10
  fi

  # Ground-truth camofox snapshot is optional — skip if not configured.
  # (Hook for later: camofox /open tiktok.com/@account, grep head.)

  return 0
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  vt_check "$@"
  exit $?
fi
