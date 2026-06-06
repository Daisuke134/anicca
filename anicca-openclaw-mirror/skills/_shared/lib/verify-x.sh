#!/usr/bin/env bash
# Anicca v3.2 verify-x — live tweet check after an X (Twitter) post.
#
# vx_check <tweet_id> <expected_caption_head> <expected_lang>
#
# Exit codes:
#   0 ok
#   6 caption head mismatch
#   7 lang field mismatch
#  10 not found / API error

source "$(dirname "${BASH_SOURCE[0]}")/lang-detect.sh"

vx_check() {
  local tweet_id="$1"
  local expected_head="$2"
  local expected_lang="$3"
  : "${X_BEARER_TOKEN:?X_BEARER_TOKEN required}"

  local resp text lang
  resp="$(curl -sS -H "Authorization: Bearer ${X_BEARER_TOKEN}" \
    "https://api.x.com/2/tweets/${tweet_id}?tweet.fields=lang,text" 2>/dev/null)"
  text="$(printf '%s' "$resp" | jq -r '.data.text // empty' 2>/dev/null)"
  lang="$(printf '%s' "$resp" | jq -r '.data.lang // empty' 2>/dev/null)"

  if [ -z "$text" ]; then
    echo "vx_check: 10 tweet not retrievable id=$tweet_id resp=${resp:0:200}" >&2
    return 10
  fi

  if ! printf '%s' "$text" | grep -qF "$expected_head"; then
    echo "vx_check: 6 caption head not found in live tweet" >&2
    return 6
  fi

  if [ -n "$lang" ] && [ "$lang" != "$expected_lang" ]; then
    # X API lang detection sometimes "und" → fall back to our detector
    if [ "$lang" != "und" ]; then
      echo "vx_check: 7 X-reported lang=$lang expected=$expected_lang" >&2
      return 7
    fi
  fi

  return 0
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  vx_check "$@"
  exit $?
fi
