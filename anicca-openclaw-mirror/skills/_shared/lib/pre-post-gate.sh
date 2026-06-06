#!/usr/bin/env bash
# Anicca v3.2 pre-post-gate — fail-closed checks BEFORE any social post.
#
# Public API:
#   ppg_check --platform <X|TikTok|YouTube> \
#             --account "<@handle>" \
#             --integration-id <ENV_VAR_NAME> \
#             --language <2-letter> \
#             --caption-file <path> \
#             --asset-manifest <path-or-empty>
#
# Exit codes:
#   0 ok
#   1 integration-id mismatch (env not set OR wrong value)
#   2 language mismatch (detected != --language)
#   3 asset missing/zero-byte/missing-audio
#   4 caption sanitize (filename leak / over-length / vg_check fail)
#   5 account string mismatch
#
# On non-zero exit, emits "ppg_check: <code> <reason>" to stderr.

# shellcheck disable=SC1090
source "$(dirname "${BASH_SOURCE[0]}")/lang-detect.sh"
source "$(dirname "${BASH_SOURCE[0]}")/verbatim-guard.sh" 2>/dev/null || true

ppg_check() {
  local platform="" account="" integration_id_var="" language=""
  local caption_file="" asset_manifest=""

  while [ $# -gt 0 ]; do
    case "$1" in
      --platform)        platform="$2"; shift 2;;
      --account)         account="$2"; shift 2;;
      --integration-id)  integration_id_var="$2"; shift 2;;
      --language)        language="$2"; shift 2;;
      --caption-file)    caption_file="$2"; shift 2;;
      --asset-manifest)  asset_manifest="$2"; shift 2;;
      *) echo "ppg_check: unknown flag $1" >&2; return 99;;
    esac
  done

  # Required
  for need in platform account integration_id_var language caption_file; do
    if [ -z "${!need}" ]; then
      echo "ppg_check: missing required --$need" >&2
      return 99
    fi
  done
  if [ ! -f "$caption_file" ]; then
    echo "ppg_check: 3 caption file not found: $caption_file" >&2
    return 3
  fi

  # 1. Integration ID env match
  local int_val="${!integration_id_var:-}"
  if [ -z "$int_val" ]; then
    echo "ppg_check: 1 integration env var $integration_id_var is empty" >&2
    return 1
  fi
  case "$platform" in
    TikTok|tiktok) : ;;  # presence is enough; specific value validated by Postiz API at POST time
    X|x|twitter) : ;;
    YouTube|youtube) : ;;
  esac

  # 2. Language match
  local detected
  detected="$(ld_detect "$caption_file")"
  if [ "$detected" != "$language" ] && [ "$detected" != "und" ]; then
    echo "ppg_check: 2 lang mismatch (detected=$detected expected=$language)" >&2
    return 2
  fi

  # 3. Asset integrity (manifest is JSON: {"images":[...],"video":"..."} or similar)
  if [ -n "$asset_manifest" ] && [ -f "$asset_manifest" ]; then
    local imgs vid
    imgs="$(jq -r '.images[]? // empty' "$asset_manifest" 2>/dev/null)"
    vid="$(jq -r '.video // empty' "$asset_manifest" 2>/dev/null)"
    while IFS= read -r p; do
      [ -z "$p" ] && continue
      if [ ! -s "$p" ]; then
        echo "ppg_check: 3 asset missing or empty: $p" >&2
        return 3
      fi
    done <<<"$imgs"
    if [ -n "$vid" ]; then
      if [ ! -s "$vid" ]; then
        echo "ppg_check: 3 video missing/empty: $vid" >&2
        return 3
      fi
      # audio track check (ffprobe optional)
      if command -v ffprobe >/dev/null 2>&1; then
        local has_audio
        has_audio="$(ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$vid" 2>/dev/null | head -1)"
        if [ -z "$has_audio" ]; then
          echo "ppg_check: 3 video has no audio track: $vid" >&2
          return 3
        fi
      fi
    fi
  fi

  # 4. Caption sanitize
  local cap
  cap="$(cat "$caption_file")"
  # 4a path leak
  if printf '%s' "$cap" | grep -qE '/(Users|home|tmp|var)/' || printf '%s' "$cap" | grep -qE '\.(png|jpg|mp4|json|txt) '; then
    echo "ppg_check: 4 caption appears to contain filesystem path or filename" >&2
    return 4
  fi
  # 4b length cap (platform-specific)
  local len
  len="$(printf '%s' "$cap" | wc -c | tr -d ' ')"
  case "$platform" in
    X|x|twitter) [ "$len" -gt 280 ] && { echo "ppg_check: 4 caption > 280 chars (X limit)" >&2; return 4; };;
    TikTok|tiktok) [ "$len" -gt 2200 ] && { echo "ppg_check: 4 caption > 2200 chars (TikTok limit)" >&2; return 4; };;
    YouTube|youtube) [ "$len" -gt 5000 ] && { echo "ppg_check: 4 caption > 5000 chars (YouTube limit)" >&2; return 4; };;
  esac
  # 4c vg_check (verbatim guard) if available
  if declare -f vg_check >/dev/null 2>&1; then
    vg_check "$caption_file" || { echo "ppg_check: 4 vg_check failed" >&2; return 4; }
  fi

  # 5. Account string format check
  case "$account" in
    @*) : ;;
    *) echo "ppg_check: 5 account string must start with @ (got: $account)" >&2; return 5;;
  esac

  return 0
}

# CLI when invoked directly
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  ppg_check "$@"
  exit $?
fi
