#!/bin/bash
# setup-workspace.sh — 初回ワークスペースセットアップ
set -euo pipefail

SKILL_DIR="$HOME/.openclaw/skills/screenshot-ab"
WORKSPACE="$SKILL_DIR/workspace"

echo "📸 screenshot-ab workspace セットアップ開始"

# ディレクトリ作成
mkdir -p "$WORKSPACE/export/en"
mkdir -p "$WORKSPACE/export/ja"
mkdir -p "$WORKSPACE/screenshot-generator"

# experiments.json 初期化（存在しない場合のみ）
if [ ! -f "$WORKSPACE/experiments.json" ]; then
  cp "$SKILL_DIR/assets/experiments-template.json" "$WORKSPACE/experiments.json"
  echo "✅ experiments.json 初期化完了"
else
  echo "⏭️  experiments.json は既に存在"
fi

# 依存ツール確認
echo ""
echo "=== 依存ツール確認 ==="
echo -n "ASC CLI: " && asc --version 2>/dev/null || echo "❌ NOT FOUND (brew install asc)"
echo -n "Node.js: " && node --version 2>/dev/null || echo "❌ NOT FOUND"
echo -n "Playwright: " && npx playwright --version 2>/dev/null || echo "⚠️  NOT FOUND (npx playwright install chromium)"

# ParthJadhav スキル確認
if [ -f "$HOME/.agents/skills/app-store-screenshots/SKILL.md" ] || \
   [ -f "/Users/anicca/anicca-project/.agents/skills/app-store-screenshots/SKILL.md" ]; then
  echo "ParthJadhav skill: ✅ installed"
else
  echo "ParthJadhav skill: ❌ NOT FOUND (npx skills add ParthJadhav/app-store-screenshots)"
fi

echo ""
echo "✅ Workspace ready: $WORKSPACE"
