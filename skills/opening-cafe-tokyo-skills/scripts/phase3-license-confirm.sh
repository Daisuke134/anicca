#!/usr/bin/env bash
# phase3-license-confirm.sh — confirm license route (A: borrow / B: self-apply)
#
# Route A: シェアキッチン (kashispace / theghostrestaurant 等) の許可証を Anicca/Dais 名義で
#          代替書類として使えるか運営に確認 → 借用契約 → license PDF 入手
# Route B: 不採用予定 (時間とコストかかる)。Route A NG 時のみ起動。
set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
CONFIG="$SKILL/data/config.json"
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

# Read chosen kitchen from inquiries
CHOSEN=$(ls -t "$SKILL/data/cafe/inquiries"/*.json 2>/dev/null | head -1)
[ -z "$CHOSEN" ] && { echo "ERR: no inquiry found. Run phase0 first"; exit 1; }
PLATFORM=$(jq -r '.platform' "$CHOSEN")
echo "▶ Phase 3: license confirmation for $PLATFORM"

source "$SKILL/scripts/lib/dais-alert.sh" 2>/dev/null || true

DUE=$(date -u -v "+2d" +%FT%TZ 2>/dev/null || date -u -d "+2 days" +%FT%TZ)
DUE_END=$(date -u -v "+2d" -v "+1H" +%FT%TZ 2>/dev/null || date -u -d "+2 days +1 hour" +%FT%TZ)

INSTRUCTION="営業許可証 借用確認 ($PLATFORM)

Route A (推奨):
  1. シェアキッチン運営に「飲食店営業許可証を Anicca/Dais 名義で代替書類として使えるか」確認
  2. OK なら 許可証 PDF を入手 → ${SKILL/$HOME/~}/data/cafe/license.pdf
  3. ${SKILL/$HOME/~}/data/cafe/license.json の route='A' + license_doc_path を保存
  4. → Phase 4 (Uber merchant signup) に進める

Route A NG なら → Route B:
  - 03-5273-3142 (新宿区保健所) 事前相談 電話
  - city.shinjuku.lg.jp 営業許可申請 form 自動入力 (¥18,000)
  - 施設検査 立会 (Dais 物理) → ~2週で許可番号
  - Phase 2 (食衛責 講習) 必要"

alert_human \
  "🪪 [DAIS] 許可証 借用確認 ($PLATFORM)" \
  "$DUE" "$DUE_END" \
  "シェアキッチン運営とのやり取り" \
  "$INSTRUCTION" >/dev/null || true

mkdir -p "$SKILL/data/cafe"
cat > "$SKILL/data/cafe/license.json" <<EOF
{
  "status": "confirmation_pending",
  "license_route": "TBD",
  "license_doc_path": null,
  "license_number": null,
  "license_type": null,
  "license_expires": null,
  "kitchen_platform": "$PLATFORM",
  "due_at": "$DUE",
  "manual_action_required": true
}
EOF
echo "✓ Phase 3 alert sent"
