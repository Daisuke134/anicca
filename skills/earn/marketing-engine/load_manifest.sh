#!/usr/bin/env bash
# load_manifest.sh — source a marketing loop manifest by name and validate required keys.
# Usage:  . load_manifest.sh ; me_load_manifest capafy   (or a full path to a .manifest.sh)
# After a successful load, MKT_* variables are exported for the shared engine to consume.
# This is how a loop stays "config only": the engine reads MKT_* — never loop-specific literals.

me_load_manifest() {
  local name="$1"
  local dir; dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/manifests"
  local file
  if [ -f "$name" ]; then file="$name"; else file="$dir/${name}.manifest.sh"; fi
  if [ ! -f "$file" ]; then
    echo "me_load_manifest: manifest not found: $file" >&2
    return 1
  fi
  # shellcheck disable=SC1090
  . "$file"
  # Required keys — a manifest missing any of these cannot drive the engine.
  local k missing=""
  for k in MKT_INSTANCE MKT_ACCOUNT_STATE_FILE MKT_HANDLE_PREFIX MKT_PROFILE_PREFIX \
           MKT_GMAIL_PLUS_TAG_PREFIX MKT_BIO_TEXT MKT_CONTENT_ADAPTER; do
    [ -z "${!k:-}" ] && missing="$missing $k"
  done
  if [ -n "$missing" ]; then
    echo "me_load_manifest: $file missing required keys:$missing" >&2
    return 1
  fi
  export MKT_PERSONA MKT_PROBLEM MKT_INSTANCE MKT_PRODUCT_SOURCE MKT_LISTING_URL_FMT \
         MKT_BIO_LINK MKT_LANDING_SITE_ID MKT_CONTENT_ADAPTER MKT_NICHE \
         MKT_ACCOUNT_STATE_FILE MKT_HANDLE_PREFIX MKT_PROFILE_PREFIX \
         MKT_GMAIL_PLUS_TAG_PREFIX MKT_BIO_TEXT MKT_CADENCE_HOUR
  return 0
}
