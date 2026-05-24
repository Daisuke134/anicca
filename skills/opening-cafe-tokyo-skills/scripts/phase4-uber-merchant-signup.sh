#!/usr/bin/env bash
# phase4-uber-merchant-signup.sh — Uber Eats Japan merchant signup (skill-ified 5/8 v2)
#
# Pipeline:
#   1. lib/uber-eats-merchant.sh prepare    → prefill JSON 生成
#   2. lib/uber-eats-merchant.sh submit     → camofox で full automation
#   3. status save + Slack 報告
#
# Idempotent: lib/uber-eats-merchant.sh submit が既存 state を check して skip
# Entity-agnostic: data/config.json から brand/operator/product を pull
#
# Prerequisites (検証は lib/uber-eats-merchant.sh submit 内で実施):
#   - Phase 1 完了 (operator_id.json) — Anicca 5/8 受付完了
#   - Phase 3 完了 (license.json) — kitchen 契約日に PDF 受領後
#   - camofox running (:9377) — `bash ~/.openclaw/skills/camofox-{{profile.lateness.stakeholders.channel}}/scripts/start.sh`
#
# stdout final line:
#   ✅ phase4-uber: <result>
#   ❌ phase4-uber FAILED: <reason>

set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills

# 1. prepare
bash "$SKILL/scripts/lib/uber-eats-merchant.sh" prepare >/dev/null

# 2. submit (idempotent inside)
RESULT=$(bash "$SKILL/scripts/lib/uber-eats-merchant.sh" submit 2>&1) || {
  echo "❌ phase4-uber FAILED: $(echo "$RESULT" | tail -1)"
  exit 1
}
echo "$RESULT" | tail -1
