#!/usr/bin/env bash
# Restore note-mcp's locked project environment when a fresh clone has no .venv.
set -euo pipefail

NOTE_MCP_DIR="${1:?usage: ensure-note-mcp-runtime.sh NOTE_MCP_DIR}"
PY_VENV="$NOTE_MCP_DIR/.venv/bin/python"
[[ -x "$PY_VENV" ]] && exit 0

[[ -f "$NOTE_MCP_DIR/pyproject.toml" ]] || {
  echo "FATAL: note-mcp pyproject.toml missing at $NOTE_MCP_DIR" >&2
  exit 2
}
[[ -f "$NOTE_MCP_DIR/uv.lock" ]] || {
  echo "FATAL: note-mcp uv.lock missing at $NOTE_MCP_DIR" >&2
  exit 2
}

UV_BIN="${UV_BIN:-$(command -v uv || true)}"
[[ -x "$UV_BIN" ]] || {
  echo "FATAL: uv is required to restore note-mcp runtime" >&2
  exit 6
}

echo "note-mcp runtime missing; restoring from uv.lock" >&2
(
  cd "$NOTE_MCP_DIR"
  "$UV_BIN" sync --locked
)

[[ -x "$PY_VENV" ]] || {
  echo "FATAL: uv sync completed without creating $PY_VENV" >&2
  exit 6
}
