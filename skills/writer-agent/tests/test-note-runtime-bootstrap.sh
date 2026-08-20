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
[[ "$(cat "$UV_CALL_LOG")" == "sync --locked" ]]

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

echo "PASS: note runtime bootstraps once and fails closed"
