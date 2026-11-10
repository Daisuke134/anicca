#!/bin/sh
# Live demo against a throwaway Hermes profile. Requires `hermes` on PATH.
# No network calls are made by the plugin. The profile is $HERMES_HOME.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
# Never reuse a real Hermes profile. This script deletes PROFILE on purpose.
PROFILE=${LIFE_MANAGER_DEMO_HOME:-/tmp/life-manager-hermes-demo}
case "$PROFILE" in
  /tmp/*|/private/tmp/*) ;;
  *) echo "Refusing to delete HERMES profile outside /tmp: $PROFILE" >&2; exit 2 ;;
esac
rm -rf "$PROFILE"
mkdir -p "$PROFILE/plugins"
cp -a "$ROOT" "$PROFILE/plugins/life-manager"
find "$PROFILE/plugins/life-manager" -name __pycache__ -type d -prune -exec rm -rf {} +
printf '%s\n' 'plugins:' '  enabled:' '    - life-manager' > "$PROFILE/config.yaml"
export HERMES_HOME="$PROFILE"
echo "HERMES_HOME=$HERMES_HOME"
echo
echo '$ hermes plugins validate hermes-plugin --install-deps'
hermes plugins validate "$ROOT" --install-deps
echo
echo '$ hermes life-manager add "meditate every morning"'
hermes life-manager add "meditate every morning"
echo
echo '$ hermes life-manager status'
hermes life-manager status
echo
echo '$ hermes life-manager done "meditate every morning"'
hermes life-manager done "meditate every morning"
echo
echo '$ hermes life-manager status'
hermes life-manager status
echo
echo '$ hermes life-manager checkin'
hermes life-manager checkin
