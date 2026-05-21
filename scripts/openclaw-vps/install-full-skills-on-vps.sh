#!/usr/bin/env bash
# VPS 上で実行: 実行コードが必要なスキル（x-research, reddit-cli）を完全インストールする。
# 使い方: VPS に SSH して bash install-full-skills-on-vps.sh
# または: scp scripts/openclaw-vps/install-full-skills-on-vps.sh anicca@VPS:~ && ssh anicca@VPS 'bash ~/install-full-skills-on-vps.sh'
#
# 前提: 先に sync-workspace-and-skills-to-vps.sh を一度実行して SKILL.md 類を反映しておくこと。
# このスクリプト実行後、必要なら再度 sync して Anicca 用 SKILL.md を上書きできる（x-search.ts 等は残る）。

set -e
BASE="${HOME}/.openclaw"
SKILLS="${BASE}/skills"

echo "=== Anicca 完全版スキル インストール（VPS） ==="

# --- 1. x-research（trend-hunter が ~/.openclaw/skills/x-research を参照）---
echo ""
echo "[1/2] x-research: rohunvora/x-research-skill を clone + bun install"
if ! command -v bun &>/dev/null; then
  echo "  Bun が未インストール。インストールします..."
  curl -fsSL https://bun.sh/install | bash
  export BUN_INSTALL="$HOME/.bun" && export PATH="$BUN_INSTALL/bin:$PATH"
fi

mkdir -p "$SKILLS"
cd "$SKILLS"
if [ -d x-research ]; then
  echo " 既存の x-research を削除して再 clone..."
  rm -rf x-research
fi
git clone https://github.com/rohunvora/x-research-skill.git x-research
cd x-research && bun install && cd ..
echo "  x-research: OK"
echo "  ★ X_BEARER_TOKEN を ~/.openclaw/.env に設定済みか確認してください。"

# --- 2. reddit-cli（trend-hunter が ~/.openclaw/skills/reddit-cli を参照）---
echo ""
echo "[2/2] reddit-cli: ClawHub でインストール"
if ! command -v clawhub &>/dev/null; then
  echo "  clawhub が未インストール。npm でインストールします..."
  npm install -g clawhub
fi
clawhub install reddit-cli --workdir "$BASE" --dir skills --no-input 2>/dev/null || \
  clawhub install reddit-cli --workdir "$BASE" --dir skills
echo "  reddit-cli: OK"
echo "  ★ REDDIT_SESSION を ~/.openclaw/.env に設定済みか確認してください。"

echo ""
echo "=== 完了 ==="
echo "次: ローカルで sync-workspace-and-skills-to-vps.sh を実行し、Anicca 用 SKILL.md を上書きできます。"
echo "    Gateway 再起動: systemctl --user restart openclaw-gateway.service"
