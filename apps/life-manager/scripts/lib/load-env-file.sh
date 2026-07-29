#!/usr/bin/env bash
# Shared guarded env-file loader for the launchd boot scripts.
#
# lm_load_env_file <path>
#   - Refuses loudly (exit 1) when the path points beneath a legacy runtime
#     root. The segment list mirrors LEGACY_SEGMENT in lib/runtime-paths.js:
#     whole path segments, case-insensitive.
#   - Warns to stderr but keeps booting when the file does not exist (live
#     jobs may legitimately run without an env file).
#   - Sources the file with allexport when it exists.

LM_LEGACY_ENV_SEGMENT_PATTERN='(^|/)(\.openclaw|profitable-claude|life-manager-v0)(/|$)'

lm_load_env_file() {
  env_file="$1"
  lowered="$(printf '%s' "$env_file" | tr '[:upper:]' '[:lower:]')"
  if printf '%s\n' "$lowered" | grep -Eq "$LM_LEGACY_ENV_SEGMENT_PATTERN"; then
    printf 'refusing to load env file beneath a legacy runtime root: %s\n' "$env_file" >&2
    return 1
  fi
  if [ -f "$env_file" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$env_file"
    set +a
  else
    printf 'warning: env file not found: %s (continuing without it)\n' "$env_file" >&2
  fi
  return 0
}
