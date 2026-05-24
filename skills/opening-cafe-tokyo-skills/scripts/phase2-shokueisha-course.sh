#!/usr/bin/env bash
# phase2-shokueisha-course.sh — 食品衛生責任者 養成講習 申込 (toshokuken.or.jp)
# Only run if Phase 3 = Route B (自前許可申請). Skip if Route A (シェアキッチン許可借用).
# Output: data/cafe/food_safety.json
set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
CONFIG="$SKILL/data/config.json"
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

# Check Phase 3 route
ROUTE=$(jq -r '.license_route // "TBD"' "$SKILL/data/cafe/license.json" 2>/dev/null || echo "TBD")
if [ "$ROUTE" = "A" ] || [ "$ROUTE" = "a" ]; then
  echo "▶ Phase 3 Route A (借用) → Phase 2 不要、skip"
  exit 0
fi

source "$SKILL/scripts/lib/dais-alert.sh" 2>/dev/null || true

# 講習会日程 取得 (要 {{profile.lateness.stakeholders.channel}}-harness 動作確認、ここでは alert で Dais に依頼)
DUE=$(date -u -v "+5d" +%FT%TZ 2>/dev/null || date -u -d "+5 days" +%FT%TZ)
DUE_END=$(date -u -v "+5d" -v "+9H" +%FT%TZ 2>/dev/null || date -u -d "+5 days +9 hours" +%FT%TZ)

INSTRUCTION="食品衛生責任者 養成講習 申込 + 出席 (Phase 3 Route B 自前申請の場合のみ)

1. https://www.toshokuken.or.jp/ → 「東京都」→ 講習会日程
2. 直近 1 ヶ月以内の枠を選択
3. 申込 form 自動入力 (氏名・住所・連絡先) — TODO: skill が {{profile.lateness.stakeholders.channel}}-harness で実装
4. ¥10,000 振込
5. 講習日 1 日出席 (Dais 物理参加必須)
6. 修了証 PDF を ${SKILL/$HOME/~}/data/cafe/food_safety_cert.pdf に保存
7. ${SKILL/$HOME/~}/data/cafe/food_safety.json の cert_id を Dais 手動入力"

alert_human \
  "🍱 [DAIS] 食衛責 講習 申込 + 出席" \
  "$DUE" "$DUE_END" \
  "東京都内 (toshokuken 指定会場)" \
  "$INSTRUCTION" >/dev/null || true

mkdir -p "$SKILL/data/cafe"
cat > "$SKILL/data/cafe/food_safety.json" <<EOF
{
  "status": "course_signup_alerted",
  "due_at": "$DUE",
  "cert_id": null,
  "course_date": null,
  "fee_jpy": 10000,
  "manual_action_required": true,
  "note": "Phase 3 Route B (自前許可申請) 時のみ実施。Route A (借用) なら skip"
}
EOF
echo "✓ Phase 2 alert sent (Dais 講習出席必要)"
