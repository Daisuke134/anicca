#!/bin/sh
set -eu
umask 077

app_dir=$(CDPATH= cd "$(dirname "$0")/.." && pwd)
config_dir="$app_dir/Configs"
mkdir -p "$config_dir"
config_file=$(mktemp "$config_dir/.Production.xcconfig.XXXXXX")
trap 'rm -f "$config_file"' EXIT

if [ -n "${ANICCA_PRODUCTION_XCCONFIG_B64:-}" ]; then
  printf '%s' "$ANICCA_PRODUCTION_XCCONFIG_B64" | /usr/bin/base64 --decode > "$config_file"
elif [ -s "$config_dir/Production.xcconfig.fallback" ]; then
  # The Xcode Cloud secret is not set for this workflow. Fall back to the
  # production configuration committed in this repository so the build does
  # not depend on a setting that only exists in the web console. The
  # committed fallback holds the same client configuration (public API
  # keys, project tokens, and identifiers) that the secret decodes to.
  cat "$config_dir/Production.xcconfig.fallback" > "$config_file"
else
  printf '%s\n' 'Missing Xcode Cloud secret ANICCA_PRODUCTION_XCCONFIG_B64' >&2
  exit 1
fi

if [ ! -s "$config_file" ]; then
  printf '%s\n' 'Decoded production configuration is empty' >&2
  exit 1
fi

chmod 600 "$config_file"
mv -f "$config_file" "$config_dir/Production.xcconfig"
