#!/usr/bin/env bash
# anicca-cafe-license-applier — print full state + suggest next step
set -uo pipefail
SKILL=~/.openclaw/skills/anicca-cafe-license-applier
STATE="$SKILL/data/license/cafe-shinjuku.json"
[ ! -f "$STATE" ] && { echo "no state. Run pre-step.sh first"; exit 1; }

echo "▶ cafe-license status"
jq . "$STATE"

CUR=$(jq -r .status "$STATE")
echo ""
case "$CUR" in
  preparing)              NEXT="bash scripts/pre-step.sh (Phase 1)" ;;
  food_safety_in_progress)NEXT="食品衛生責任者 講習出席 → 修了証 ID 入力 → freee 開業届け確認" ;;
  kojin_filed)            NEXT="キッチンスペース契約完了後 → bash scripts/application.sh" ;;
  kitchen_contracted)     NEXT="bash scripts/application.sh (Phase 2)" ;;
  application_submitted)  NEXT="保健所 施設検査立会 → status='approved' に手動 flip OR Gmail watch" ;;
  approved)               NEXT="bash scripts/uber-onboard.sh (Phase 3)" ;;
  uber_pending)           NEXT="Uber 契約面談待ち" ;;
  live)                   NEXT="anicca-cafe-factory (§14) に引継済" ;;
  *)                      NEXT="?" ;;
esac
echo "▶ next: $NEXT"
