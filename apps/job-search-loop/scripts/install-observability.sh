#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"
DATA_ROOT="${JOB_SEARCH_DATA_ROOT:-${XDG_DATA_HOME:-$HOME/.local/share}/anicca/job-search}"
JOB_SEARCH_UV="${JOB_SEARCH_UV:-$HOME/.local/bin/uv}"

VERSION="0.158.0"
ARCHIVE="otelcol-contrib_0.158.0_darwin_arm64.tar.gz"
EXPECTED_SHA="e2b68ae0eeb165795c1c9aecc29d24fe91790dd6ec7d200dd7e5a8b226a2f636"
URL="https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v$VERSION/$ARCHIVE"
INSTALL_ROOT="$HOME/.local/libexec/anicca/job-search-observability/$VERSION"
BINARY="$INSTALL_ROOT/otelcol-contrib"
CONFIG="$DATA_ROOT/current/apps/job-search-loop/config/otel-collector.v1.yaml"
TRACE_ROOT="$DATA_ROOT/observability"
TRACE_PATH="$TRACE_ROOT/traces.jsonl"
SDK_LOCK="$JOB_SEARCH_APP_ROOT/config/upstreams/opentelemetry-1.44.0-macos-arm64-py312.lock"
PLIST="$JOB_SEARCH_LAUNCH_AGENT_DIR/ai.anicca.job-search-observability.plist"
LABEL="ai.anicca.job-search-observability"
TEMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEMP_ROOT"' EXIT

curl --fail --location --silent --show-error "$URL" --output "$TEMP_ROOT/$ARCHIVE"
ACTUAL_SHA="$(shasum -a 256 "$TEMP_ROOT/$ARCHIVE" | awk '{print $1}')"
[[ "$ACTUAL_SHA" == "$EXPECTED_SHA" ]] || { print -u2 "collector checksum mismatch"; exit 65; }
tar -xzf "$TEMP_ROOT/$ARCHIVE" -C "$TEMP_ROOT"
mkdir -p "$INSTALL_ROOT" "$TRACE_ROOT" "$JOB_SEARCH_STATE_ROOT/logs" "$JOB_SEARCH_LAUNCH_AGENT_DIR"
chmod 700 "$INSTALL_ROOT" "$TRACE_ROOT" "$JOB_SEARCH_STATE_ROOT/logs"
touch "$TRACE_PATH"
chmod 600 "$TRACE_PATH"
install -m 500 "$TEMP_ROOT/otelcol-contrib" "$BINARY"
"$JOB_SEARCH_UV" pip install --python "$JOB_SEARCH_PYTHON" --require-hashes \
  --requirement "$SDK_LOCK"

"$JOB_SEARCH_PYTHON" - "$JOB_SEARCH_APP_ROOT/launchd/$LABEL.plist" "$PLIST" \
  "$BINARY" "$CONFIG" "$TRACE_PATH" "$JOB_SEARCH_STATE_ROOT/logs/observability.out.log" \
  "$JOB_SEARCH_STATE_ROOT/logs/observability.err.log" <<'PY'
import os, plistlib, sys
from pathlib import Path
template, output, binary, config, trace, stdout, stderr = map(Path, sys.argv[1:])
value = plistlib.loads(template.read_bytes())
value["ProgramArguments"] = [str(binary), f"--config={config}"]
value["EnvironmentVariables"] = {"JOB_HUNTER_TRACE_PATH": str(trace)}
value["StandardOutPath"], value["StandardErrorPath"] = str(stdout), str(stderr)
temporary = output.with_suffix(".tmp")
temporary.write_bytes(plistlib.dumps(value, sort_keys=False))
os.chmod(temporary, 0o600)
temporary.replace(output)
PY
"$JOB_SEARCH_PLUTIL" -lint "$PLIST" >/dev/null

UID_VALUE="$(id -u)"
"$JOB_SEARCH_LAUNCHCTL" bootout "gui/$UID_VALUE/$LABEL" 2>/dev/null || true
for attempt in {1..10}; do
  "$JOB_SEARCH_LAUNCHCTL" print "gui/$UID_VALUE/$LABEL" >/dev/null 2>&1 || break
  sleep 0.2
done
LOADED=0
for attempt in {1..10}; do
  if "$JOB_SEARCH_LAUNCHCTL" bootstrap "gui/$UID_VALUE" "$PLIST"; then
    LOADED=1
    break
  fi
  sleep 0.5
done
[[ "$LOADED" == "1" ]] || { print -u2 "collector bootstrap failed"; exit 70; }
"$JOB_SEARCH_LAUNCHCTL" kickstart -k "gui/$UID_VALUE/$LABEL"
