#!/usr/bin/env bash
# OpenClaw workspace 19 項目検証（VPS 上で実行する）
# 使い方: VPS に SSH して bash verify-vps-workspace.sh
# または: scp scripts/openclaw-vps/verify-vps-workspace.sh anicca@46.225.70.241:~ && ssh anicca@46.225.70.241 'bash ~/verify-vps-workspace.sh'

# set -e は使わない（各項目で FAIL しても残りを検証する）
BASE="${OPENCLAW_HOME:-/home/anicca/.openclaw}"
WS="$BASE/workspace"
CRON_JOBS="$BASE/cron/jobs.json"
SKILLS="$BASE/skills"
ENV_FILE="$BASE/.env"

pass() { echo "PASS"; }
fail() { echo "FAIL: $*"; }

echo "=== OpenClaw workspace 19 項目検証 (BASE=$BASE) ==="
echo ""

# #13 workspace/ops/ 作成・初期化
echo -n "#13 workspace/ops/ + completed/ + 3 files: "
if [ -f "$WS/ops/steps.json" ] && [ -f "$WS/ops/heartbeat_state.json" ] && [ -f "$WS/ops/proposals.json" ] && [ -d "$WS/ops/completed" ]; then
  pass
else
  fail "missing ops/steps.json or heartbeat_state.json or proposals.json or ops/completed/"
fi

# #14 各スキル用フォルダ
echo -n "#14 workspace skill folders (trends,hooks,nudges,suffering,autonomy-check,...): "
FOLDERS="trends hooks nudges suffering autonomy-check hookpost-ttl-cleaner moltbook-monitor moltbook-poster roundtable-standup roundtable-memory-extract roundtable-initiative-generate sto-weekly-refresh"
M=0
for d in $FOLDERS; do
  [ -d "$WS/$d" ] || M=1
done
if [ "$M" -eq 0 ]; then pass; else fail "one or more of $FOLDERS missing"; fi

# #15 SKILL に保存先記載（代表で mission-worker, ops-heartbeat, autonomy-check）
echo -n "#15 SKILLs have workspace save paths: "
if grep -q "workspace/ops/steps.json" "$SKILLS/mission-worker/SKILL.md" 2>/dev/null && \
   grep -q "workspace/ops/heartbeat_state.json" "$SKILLS/ops-heartbeat/SKILL.md" 2>/dev/null && \
   grep -q "workspace/autonomy-check" "$SKILLS/autonomy-check/SKILL.md" 2>/dev/null; then
  pass
else
  fail "check mission-worker, ops-heartbeat, autonomy-check SKILL.md for workspace paths"
fi

# #16 .env に API_BASE_URL
echo -n "#16 .env has API_BASE_URL: "
if [ -f "$ENV_FILE" ] && grep -q "API_BASE_URL" "$ENV_FILE" && [ -n "$(grep API_BASE_URL "$ENV_FILE" | cut -d= -f2)" ]; then
  pass
else
  fail "missing or empty API_BASE_URL in $ENV_FILE"
fi

# #17 mission-worker: jobs.json payload が steps.json 読む・completed に書く・API 使わない
echo -n "#17 mission-worker payload file-only (no step API): "
if [ ! -f "$CRON_JOBS" ]; then
  fail "cron jobs.json not found"
elif grep -q "steps.json" "$CRON_JOBS" && grep -q "completed" "$CRON_JOBS" && grep -q "Do not call any step API" "$CRON_JOBS"; then
  pass
else
  fail "cron jobs.json mission-worker should read steps.json, write completed/, no API"
fi

# #18 ops-heartbeat: jobs.json payload が heartbeat_state / proposals に書く・API 使わない
echo -n "#18 ops-heartbeat payload file-only (no heartbeat API): "
if [ ! -f "$CRON_JOBS" ]; then
  fail "cron jobs.json not found"
elif grep -q "heartbeat_state.json" "$CRON_JOBS" && grep -q "proposals.json" "$CRON_JOBS" && grep -q "Do not call any heartbeat API" "$CRON_JOBS"; then
  pass
else
  fail "cron jobs.json ops-heartbeat should write heartbeat_state.json, proposals.json, no API"
fi

# #19 cron スキル: 直接起動・workspace/<skill>/ に書く・POST しない
echo -n "#19 cron skills write to workspace (no POST): "
if ! [ -f "$CRON_JOBS" ]; then
  fail "cron jobs.json not found"
else
  N_POST=$(grep -c "Do not POST" "$CRON_JOBS" 2>/dev/null || echo 0)
  N_WS=$(grep -c "workspace" "$CRON_JOBS" 2>/dev/null || echo 0)
  # 少なくとも autonomy-check, suffering-detector, moltbook-*, roundtable-*, hookpost-ttl-cleaner, sto-weekly-refresh が workspace + Do not POST を持つ
  if [ "$N_POST" -ge 8 ] && [ "$N_WS" -ge 8 ]; then
    pass
  else
    fail "jobs.json should have many 'Do not POST' and 'workspace' (got POST=$N_POST ws=$N_WS)"
  fi
fi

echo ""
echo "--- #1–#12 は repo 側（ドキュメント・SKILL 編集）。VPS は #13–#19 を上記で確認。---"
echo "--- 全 PASS なら VPS 側の 19 対応は完了。---"
