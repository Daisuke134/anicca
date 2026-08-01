#!/bin/bash
set -euo pipefail

LABELS=(
  "ai.anicca.connector-fill-gaps"
  "ai.anicca.connector-daily-report"
)
LAUNCH_AGENTS_DIR="${LM_LAUNCH_AGENTS_DIR:-$HOME/Library/LaunchAgents}"
ARCHIVE_DIR="${LM_RETIRED_LAUNCHD_DIR:-$HOME/.local/state/life-manager/retired-launchd/o1b10}"
LAUNCHCTL_BIN="${LM_LAUNCHCTL_BIN:-/bin/launchctl}"
LAUNCH_DOMAIN="${LM_LAUNCH_DOMAIN:-gui/$(id -u)}"
FALLBACK_DIR="${LM_LEGACY_CONNECTOR_PLIST_FALLBACK_DIR:-$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)/legacy-launchd-archive}"

safe_absolute_dir() {
  case "$1" in
    /*) ;;
    *) return 1 ;;
  esac
  [ "$1" != "/" ] && [ "$1" != "$HOME" ]
}

safe_absolute_dir "$LAUNCH_AGENTS_DIR" || {
  printf '%s\n' 'Legacy Connector retirement path invalid' >&2
  exit 2
}
safe_absolute_dir "$ARCHIVE_DIR" || {
  printf '%s\n' 'Legacy Connector retirement path invalid' >&2
  exit 2
}
[ "$LAUNCH_AGENTS_DIR" != "$ARCHIVE_DIR" ] || {
  printf '%s\n' 'Legacy Connector retirement path invalid' >&2
  exit 2
}
[ -x "$LAUNCHCTL_BIN" ] || {
  printf '%s\n' 'launchctl unavailable' >&2
  exit 2
}

install -d -m 700 "$ARCHIVE_DIR"
moved=0

# Secure a rollback artifact for every target before changing launchd state.
for label in "${LABELS[@]}"; do
  source_plist="$LAUNCH_AGENTS_DIR/$label.plist"
  archive_plist="$ARCHIVE_DIR/$label.plist"
  if [ -f "$source_plist" ]; then
    if [ -e "$archive_plist" ]; then
      source_sha="$(shasum -a 256 "$source_plist" | awk '{print $1}')"
      archive_sha="$(shasum -a 256 "$archive_plist" | awk '{print $1}')"
      if [ "$source_sha" != "$archive_sha" ]; then
        printf '%s\n' "Legacy Connector archive conflict: $label" >&2
        exit 3
      fi
      duplicate="$ARCHIVE_DIR/$label.reappeared.$(date -u +%Y%m%dT%H%M%SZ).plist"
      mv "$source_plist" "$duplicate"
      chmod 600 "$duplicate"
    else
      chmod 600 "$source_plist"
      mv "$source_plist" "$archive_plist"
      chmod 600 "$archive_plist"
    fi
    moved=1
  elif [ ! -f "$archive_plist" ]; then
    fallback="$FALLBACK_DIR/$label.plist"
    [ -f "$fallback" ] || {
      printf '%s\n' "Legacy Connector plist unavailable: $label" >&2
      exit 3
    }
    plutil -lint "$fallback" >/dev/null
    cp "$fallback" "$archive_plist"
    chmod 600 "$archive_plist"
    moved=1
  fi
done

for label in "${LABELS[@]}"; do
  service="$LAUNCH_DOMAIN/$label"
  if "$LAUNCHCTL_BIN" print "$service" >/dev/null 2>&1; then
    "$LAUNCHCTL_BIN" bootout "$service" >/dev/null
  fi
  "$LAUNCHCTL_BIN" disable "$service" >/dev/null
done

first_sha="$(shasum -a 256 "$ARCHIVE_DIR/${LABELS[0]}.plist" | awk '{print $1}')"
second_sha="$(shasum -a 256 "$ARCHIVE_DIR/${LABELS[1]}.plist" | awk '{print $1}')"
status="already_retired"
[ "$moved" -eq 1 ] && status="retired"

jq -n \
  --arg status "$status" \
  --arg domain "$LAUNCH_DOMAIN" \
  --arg archive_dir "$ARCHIVE_DIR" \
  --arg label_one "${LABELS[0]}" \
  --arg label_two "${LABELS[1]}" \
  --arg sha_one "$first_sha" \
  --arg sha_two "$second_sha" \
  '{
    schema_version: "life-manager.connector.legacy-launchd-retirement.v1",
    status: $status,
    launch_domain: $domain,
    archive_dir: $archive_dir,
    labels: [
      {label: $label_one, sha256: $sha_one, disabled: true},
      {label: $label_two, sha256: $sha_two, disabled: true}
    ],
    rollback: "Restore each archived plist to ~/Library/LaunchAgents, then run launchctl enable <domain>/<label> and launchctl bootstrap <domain> <plist>."
  }' | tee "$ARCHIVE_DIR/manifest.json"
chmod 600 "$ARCHIVE_DIR/manifest.json"
