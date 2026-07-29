#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
SOURCE="$ROOT/skills/gig-work/gig-healthcheck.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/home/.openclaw/state" "$TMP/fake-bin"
printf '%s\n' 'free_gb=4 threshold_gb=11' > "$TMP/home/.openclaw/state/disk-pressure.block"

cat > "$TMP/fake-bin/docker" <<'EOF'
#!/usr/bin/env bash
echo docker-called >> "$CALLS"
exit 1
EOF
cat > "$TMP/fake-bin/colima" <<'EOF'
#!/usr/bin/env bash
echo colima-called >> "$CALLS"
exit 0
EOF
chmod +x "$TMP/fake-bin/docker" "$TMP/fake-bin/colima"

# Source the production function definitions without executing the healthcheck's
# top-level core probe. Replace only its fixed launchd PATH in this isolated copy.
awk '/^docker_selfheal$/ { exit } { print }' "$SOURCE" |
  sed 's#^export PATH=.*#export PATH="$FAKE_BIN:/usr/bin:/bin:/usr/sbin:/sbin"#' > "$TMP/functions.sh"

HOME="$TMP/home" \
FAKE_BIN="$TMP/fake-bin" \
CALLS="$TMP/calls" \
GIG_DOCKER_DISK_PRESSURE_FLAG="$TMP/home/.openclaw/state/disk-pressure.block" \
  bash -c 'source "$1"; docker_selfheal' _ "$TMP/functions.sh"

test ! -e "$TMP/calls"
grep -Fq 'disk pressure active — preserving stopped Docker runtime' \
  "$TMP/home/.openclaw/logs/gig-core-healthcheck.log"

# Moderate pressure must not strand a revenue-critical validator image when
# the already-running daemon can rebuild it without starting a stopped VM.
: > "$TMP/calls"
printf '%s\n' 'free_gb=7 threshold_gb=11' > "$TMP/home/.openclaw/state/disk-pressure.block"
cat > "$TMP/fake-bin/docker" <<'EOF'
#!/usr/bin/env bash
echo "docker $*" >> "$CALLS"
if [ "$1" = info ]; then
  exit 0
fi
if [ "$1" = image ] && [ "$2" = inspect ]; then
  exit 1
fi
if [ "$1" = build ]; then
  cat >/dev/null
  exit 0
fi
exit 2
EOF
chmod +x "$TMP/fake-bin/docker"

HOME="$TMP/home" \
FAKE_BIN="$TMP/fake-bin" \
CALLS="$TMP/calls" \
GIG_DOCKER_DISK_PRESSURE_FLAG="$TMP/home/.openclaw/state/disk-pressure.block" \
  bash -c 'source "$1"; docker_selfheal' _ "$TMP/functions.sh"

grep -Fq 'docker info' "$TMP/calls"
grep -Fq 'docker image inspect openclaw-sandbox:bookworm-slim' "$TMP/calls"
grep -Fq 'docker build -t openclaw-sandbox:bookworm-slim -' "$TMP/calls"
! grep -Fq 'colima' "$TMP/calls"
