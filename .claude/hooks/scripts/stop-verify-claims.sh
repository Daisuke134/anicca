#!/bin/bash
# Stop hook: 「テスト pass」「build 通った」 系 の 嘘 を 出口 で 検査。
# 該当 dir で 直近 編集 された file の type-check を 1 発 走らせて 結果 を 出す。
# 結果 = context 返却 → Claude が 嘘 を 維持 不能。

ROOT="$(git -C "$(pwd)" rev-parse --show-toplevel 2>/dev/null || pwd)"

# 直近 5 分 で 編集された コード file を 検出
CHANGED=$(find "$ROOT" -type f \
  \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.py" -o -name "*.swift" \) \
  -mmin -5 \
  -not -path "*/node_modules/*" \
  -not -path "*/.next/*" \
  -not -path "*/dist/*" \
  -not -path "*/build/*" \
  -not -path "*/.worktrees/*" \
  -not -path "*-mirror/*" \
  2>/dev/null | head -3)

[ -z "$CHANGED" ] && exit 0

echo "=== Stop verify (= 嘘の出口検査): 直近編集 file syntax check ==="
while IFS= read -r f; do
  [ -z "$f" ] && continue
  case "$f" in
    *.ts|*.tsx)
      DIR="$(dirname "$f")"
      while [ "$DIR" != "/" ] && [ ! -f "$DIR/tsconfig.json" ]; do DIR="$(dirname "$DIR")"; done
      if [ -f "$DIR/tsconfig.json" ] && command -v npx >/dev/null 2>&1; then
        OUT=$( cd "$DIR" && timeout 20 npx -y tsc --noEmit --pretty false 2>&1 | grep -E "$(basename "$f"):" | head -5 )
        [ -n "$OUT" ] && echo "[$f] $OUT"
      fi
      ;;
    *.js|*.jsx|*.mjs|*.cjs)
      OUT=$(timeout 5 node --check "$f" 2>&1 | head -5)
      [ -n "$OUT" ] && echo "[$f] $OUT"
      ;;
    *.py)
      if command -v ruff >/dev/null 2>&1; then
        OUT=$(timeout 5 ruff check --quiet "$f" 2>&1 | head -5)
        [ -n "$OUT" ] && echo "[$f] $OUT"
      fi
      ;;
    *.swift)
      if command -v swiftc >/dev/null 2>&1; then
        OUT=$(timeout 10 swiftc -parse "$f" 2>&1 | head -5)
        [ -n "$OUT" ] && echo "[$f] $OUT"
      fi
      ;;
  esac
done <<< "$CHANGED"

exit 0
