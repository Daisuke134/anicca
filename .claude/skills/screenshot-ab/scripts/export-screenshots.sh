#!/bin/bash
# export-screenshots.sh — Playwright ヘッドレス PNG エクスポート
# ParthJadhav の page.tsx をヘッドレスブラウザでレンダリング → PNG エクスポート
set -euo pipefail

SKILL_DIR="$HOME/.openclaw/skills/screenshot-ab"
GENERATOR="$SKILL_DIR/workspace/screenshot-generator"
EXPORT_DIR="$SKILL_DIR/workspace/export"

if [ ! -d "$GENERATOR" ] || [ ! -f "$GENERATOR/package.json" ]; then
  echo "❌ screenshot-generator が見つかりません。ParthJadhav でスキャフォールドしてください。"
  exit 1
fi

# 依存インストール
cd "$GENERATOR"
if [ -f "bun.lockb" ] || command -v bun &>/dev/null; then
  bun install 2>/dev/null || npm install
else
  npm install
fi

# dev server 起動（バックグラウンド）
echo "📸 Starting dev server..."
PORT=3847
npx next dev -p $PORT &
DEV_PID=$!

# サーバー起動待ち
for i in $(seq 1 30); do
  if curl -s "http://localhost:$PORT" >/dev/null 2>&1; then
    echo "✅ Dev server ready on port $PORT"
    break
  fi
  sleep 1
done

# エクスポートディレクトリ準備
mkdir -p "$EXPORT_DIR/en" "$EXPORT_DIR/ja"

# Playwright でスクリーンショット取得
# ParthJadhav の page.tsx はスライドごとにクリックしてエクスポートする設計
# ここでは各スライド × 各ロケールの URL パターンに従う
echo "📸 Exporting screenshots..."

LOCALES=("en" "ja")
SCREENS=(1 2 3 4)

for locale in "${LOCALES[@]}"; do
  for screen in "${SCREENS[@]}"; do
    OUTPUT="$EXPORT_DIR/$locale/screen${screen}.png"
    echo "  Exporting $locale/screen${screen}..."

    # ParthJadhav の URL パターン: ?locale=xx&slide=N&export=true
    # もしくはページ内のエクスポートボタンを Playwright で押す
    npx playwright screenshot \
      "http://localhost:$PORT?locale=$locale&slide=$screen" \
      --viewport-size "1284,2778" \
      --full-page \
      "$OUTPUT" 2>/dev/null || {
        echo "  ⚠️  Playwright screenshot failed for $locale/screen${screen}"
        echo "  Trying alternative: full page capture..."
        npx playwright screenshot \
          "http://localhost:$PORT" \
          --viewport-size "1284,2778" \
          "$OUTPUT" 2>/dev/null || true
      }
  done
done

# dev server 停止
kill $DEV_PID 2>/dev/null || true

echo ""
echo "✅ Export complete:"
ls -la "$EXPORT_DIR/en/" 2>/dev/null
ls -la "$EXPORT_DIR/ja/" 2>/dev/null
