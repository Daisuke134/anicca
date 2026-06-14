#!/bin/bash
# PostToolUse hook (Edit|Write): Fabrication catcher.
# 嘘 (= 存在しない import / typo した symbol) を 即 検出 して context に 返す。
# 嘘 を 維持 不能 にする 物理 法則 layer。
#
# SECURITY (2026-06-15 hardening, per commit review):
#  - FILE_PATH must resolve INSIDE the project root ($CLAUDE_PROJECT_DIR / PWD) — never act on
#    /tmp or sibling repos. Defends against confused-deputy: editing an attacker-planted file
#    outside the repo must NOT trigger cargo/npx code execution.
#  - manifest search is CLAMPED to the project root (never walks up to /).
#  - npx runs without `-y` so npm can never silently auto-install a malicious package.

FILE_PATH="${CLAUDE_FILE_PATH:-}"
[ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ] && exit 0

# --- project-root gate: only process files inside the trusted workspace ---
ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
ROOT="$(cd "$ROOT" 2>/dev/null && pwd -P)" || exit 0
RP_DIR="$(cd "$(dirname "$FILE_PATH")" 2>/dev/null && pwd -P)" || exit 0
RP="$RP_DIR/$(basename -- "$FILE_PATH")"
case "$RP" in
  "$ROOT"/*) ;;          # inside project root → OK
  *) exit 0 ;;           # outside → refuse (no code execution on foreign paths)
esac

# find a manifest walking UP from the file dir, but never above ROOT
find_manifest_dir() {
  local d="$RP_DIR" name="$1"
  while :; do
    [ -f "$d/$name" ] && { echo "$d"; return 0; }
    [ "$d" = "$ROOT" ] && return 1   # stop at project root, never go above
    [ "$d" = "/" ] && return 1
    d="$(dirname "$d")"
  done
}

case "$FILE_PATH" in
  *.ts|*.tsx)
    if command -v npx >/dev/null 2>&1; then
      DIR="$(find_manifest_dir tsconfig.json)" || DIR=""
      if [ -n "$DIR" ]; then
        # NOTE: no `-y` — npm must never silently install; uses repo/global tsc only.
        ( cd "$DIR" && timeout 30 npx --no-install tsc --noEmit --pretty false 2>&1 | grep -F -e "$(basename -- "$FILE_PATH")" | head -20 ) || true
      fi
    fi
    ;;
  *.js|*.jsx|*.mjs|*.cjs)
    if command -v node >/dev/null 2>&1; then
      timeout 10 node --check "$FILE_PATH" 2>&1 | head -20 || true
    fi
    ;;
  *.py)
    if command -v ruff >/dev/null 2>&1; then
      timeout 10 ruff check --quiet "$FILE_PATH" 2>&1 | head -20 || true
    elif command -v python3 >/dev/null 2>&1; then
      timeout 10 python3 -c 'import ast,sys; ast.parse(open(sys.argv[1]).read())' "$FILE_PATH" 2>&1 | head -20 || true
    fi
    ;;
  *.swift)
    if command -v swiftc >/dev/null 2>&1; then
      timeout 15 swiftc -parse "$FILE_PATH" 2>&1 | head -20 || true
    fi
    ;;
  *.rs)
    # cargo check runs build.rs + proc-macros (code execution). Only allowed because $DIR is
    # clamped INSIDE the project root above; refuse if no in-root Cargo.toml.
    if command -v cargo >/dev/null 2>&1; then
      DIR="$(find_manifest_dir Cargo.toml)" || DIR=""
      [ -n "$DIR" ] && ( cd "$DIR" && timeout 30 cargo check --message-format=short 2>&1 | head -20 ) || true
    fi
    ;;
  *.json)
    if command -v jq >/dev/null 2>&1; then
      jq empty "$FILE_PATH" 2>&1 | head -10 || true
    fi
    ;;
  *.sh|*.bash)
    bash -n "$FILE_PATH" 2>&1 | head -10 || true
    ;;
esac

exit 0
