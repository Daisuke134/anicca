#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HELPER="$ROOT/scripts/ensure-note-mcp-runtime.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PROJECT="$TMP/note-mcp"
BIN="$TMP/bin"
mkdir -p "$PROJECT" "$BIN"
touch "$PROJECT/pyproject.toml" "$PROJECT/uv.lock"

cat >"$BIN/uv" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"${UV_CALL_LOG:?}"
mkdir -p .venv/bin
printf '#!/usr/bin/env bash\nexit 0\n' >.venv/bin/python
chmod +x .venv/bin/python
SH
chmod +x "$BIN/uv"

export UV_CALL_LOG="$TMP/uv-calls.log"
UV_BIN="$BIN/uv" bash "$HELPER" "$PROJECT"
[[ -x "$PROJECT/.venv/bin/python" ]]
[[ "$(cat "$UV_CALL_LOG")" == "sync --locked --no-dev" ]]

: >"$UV_CALL_LOG"
UV_BIN="$BIN/uv" bash "$HELPER" "$PROJECT"
[[ ! -s "$UV_CALL_LOG" ]]

rm "$PROJECT/.venv/bin/python"
cat >"$BIN/uv-fail" <<'SH'
#!/usr/bin/env bash
exit 42
SH
chmod +x "$BIN/uv-fail"
if UV_BIN="$BIN/uv-fail" bash "$HELPER" "$PROJECT"; then
  echo "expected bootstrap failure to propagate" >&2
  exit 1
fi

# A failed uv sync may leave .venv/bin/python as a symlink into uv's shared
# interpreter cache. The fallback must unlink only the project link, never
# overwrite the cache target.
PROJECT2="$TMP/note-mcp-symlink"
mkdir -p "$PROJECT2/.venv/bin" "$PROJECT2/src" "$TMP/fallback-site"
touch "$PROJECT2/pyproject.toml" "$PROJECT2/uv.lock"
printf 'cache-sentinel\n' >"$TMP/cache-target"
ln -s "$TMP/cache-target" "$PROJECT2/.venv/bin/python"
cat >"$BIN/fallback-python" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-c" ]]; then
  if [[ "$2" == *"site.getsitepackages"* ]]; then
    printf '%s\n' "${FALLBACK_SITE:?}"
  fi
  exit 0
fi
exit 0
SH
chmod +x "$BIN/fallback-python"
FALLBACK_SITE="$TMP/fallback-site" \
  UV_BIN="$BIN/uv-fail" \
  NOTE_MCP_FALLBACK_PYTHON="$BIN/fallback-python" \
  bash "$HELPER" "$PROJECT2"
[[ "$(cat "$TMP/cache-target")" == "cache-sentinel" ]]
[[ ! -L "$PROJECT2/.venv/bin/python" ]]

echo "PASS: note runtime bootstraps once and fails closed"
