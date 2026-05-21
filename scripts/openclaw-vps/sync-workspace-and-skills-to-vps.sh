#!/usr/bin/env bash
# スキル実行ルールと cron 定義を VPS に反映する。
# - repo の openclaw-skills/* を VPS ~/.openclaw/skills/ に rsync（jobs.json 除く）
# - repo の openclaw-skills/jobs.json を VPS ~/.openclaw/cron/jobs.json に scp
# - repo の openclaw/workspace/AGENTS.md を VPS ~/.openclaw/workspace/AGENTS.md に scp
# 使い方: プロジェクトルートで ./scripts/openclaw-vps/sync-workspace-and-skills-to-vps.sh
# 前提: ssh anicca@46.225.70.241 が通ること。

set -e
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VPS_HOST="anicca@46.225.70.241"
SKILLS_SRC="${REPO_ROOT}/openclaw-skills"
JOBS_SRC="${REPO_ROOT}/openclaw-skills/jobs.json"
AGENTS_SRC="${REPO_ROOT}/openclaw/workspace/AGENTS.md"
VPS_SKILLS="/home/anicca/.openclaw/skills"
VPS_CRON="/home/anicca/.openclaw/cron"
VPS_WS="/home/anicca/.openclaw/workspace"

if [[ ! -d "$SKILLS_SRC" ]]; then
  echo "Error: openclaw-skills not found at $SKILLS_SRC"
  exit 1
fi
if [[ ! -f "$AGENTS_SRC" ]]; then
  echo "Error: AGENTS.md not found at $AGENTS_SRC"
  exit 1
fi
if [[ ! -f "$JOBS_SRC" ]]; then
  echo "Error: jobs.json not found at $JOBS_SRC"
  exit 1
fi

echo "Syncing skills (excluding jobs.json) to VPS..."
# x-research, reddit-cli は git clone した完全版。--delete で消さないように exclude
rsync -av --delete \
  --exclude='jobs.json' \
  --exclude='x-research/lib/' \
  --exclude='x-research/.git/' \
  --exclude='x-research/data/' \
  --exclude='x-research/references/' \
  --exclude='x-research/x-search.ts' \
  --exclude='x-research/CHANGELOG.md' \
  --exclude='x-research/.gitignore' \
  --exclude='reddit-cli/' \
  "$SKILLS_SRC/" "$VPS_HOST:$VPS_SKILLS/"

echo "Syncing cron jobs.json to VPS..."
ssh "$VPS_HOST" "mkdir -p $VPS_CRON"
scp "$JOBS_SRC" "$VPS_HOST:$VPS_CRON/jobs.json"

echo "Syncing AGENTS.md (bootstrap) to VPS workspace..."
ssh "$VPS_HOST" "mkdir -p $VPS_WS"
scp "$AGENTS_SRC" "$VPS_HOST:$VPS_WS/AGENTS.md"

echo "Done. Anicca will use updated SKILL.md, cron jobs.json, and AGENTS.md on next session/cron."
echo ""
echo "Note: trend-hunter が動くには x-research, reddit-cli の実行コードが必要。初回は install-full-skills-on-vps.sh を VPS で実行すること。"
echo "To reload immediately, restart gateway: ssh $VPS_HOST 'systemctl --user restart openclaw-gateway.service'"
