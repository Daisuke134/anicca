#!/bin/bash
# PostToolUse hook (Edit|Write): Fabrication catcher.
# 嘘 (= 存在しない import / typo した symbol) を 即 検出 して context に 返す。
# 嘘 を 維持 不能 にする 物理 法則 layer。

FILE_PATH="${CLAUDE_FILE_PATH:-}"
[ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ] && exit 0

cd "$(dirname "$FILE_PATH")" 2>/dev/null || cd /

case "$FILE_PATH" in
  *.ts|*.tsx)
    if command -v npx >/dev/null 2>&1; then
      # 最寄り tsconfig.json を 探す
      DIR="$(dirname "$FILE_PATH")"
      while [ "$DIR" != "/" ] && [ ! -f "$DIR/tsconfig.json" ]; do DIR="$(dirname "$DIR")"; done
      if [ -f "$DIR/tsconfig.json" ]; then
        ( cd "$DIR" && timeout 30 npx -y tsc --noEmit --pretty false 2>&1 | grep -F -e "$(basename -- "$FILE_PATH")" | head -20 ) || true
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
    if command -v cargo >/dev/null 2>&1; then
      DIR="$(dirname "$FILE_PATH")"
      while [ "$DIR" != "/" ] && [ ! -f "$DIR/Cargo.toml" ]; do DIR="$(dirname "$DIR")"; done
      [ -f "$DIR/Cargo.toml" ] && ( cd "$DIR" && timeout 30 cargo check --message-format=short 2>&1 | head -20 ) || true
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
