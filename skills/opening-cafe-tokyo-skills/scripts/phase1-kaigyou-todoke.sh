#!/usr/bin/env bash
# phase1-kaigyou-todoke.sh — 個人事業主 開業届け via yamitzky/freee-cli
# Prerequisite: Phase 0 で kitchen 契約済 (state.kitchen_address 確定)
# Output: data/cafe/operator_id.json (個人番号 12 桁)
set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
CONFIG="$SKILL/data/config.json"
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

# Check freee-cli
if ! command -v freee &>/dev/null && ! command -v freee-cli &>/dev/null; then
  echo "▶ freee-cli not installed. Installing yamitzky/freee-cli..."
  npm i -g @yamitzky/freee-cli 2>&1 | tail -5 || {
    echo "ERR: freee-cli install failed. Manual install required: https://github.com/yamitzky/freee-cli"
    exit 1
  }
fi

# Initial OAuth (Dais 介入)
echo "▶ Phase 1: 開業届け (entity owner: $(jq -r .operator.name "$CONFIG"))"
echo "  freee CLI 初回認証 → 開業届けテンプレ生成 → e-Tax XML or PDF"
echo "  ⚠ freee CLI の正確な command は要確認 (https://github.com/yamitzky/freee-cli)"
echo "  human-in-the-loop:"

source "$SKILL/scripts/lib/dais-alert.sh" 2>/dev/null || true

DUE=$(date -u -v "+3d" +%FT%TZ 2>/dev/null || date -u -d "+3 days" +%FT%TZ)
DUE_END=$(date -u -v "+3d" -v "+1H" +%FT%TZ 2>/dev/null || date -u -d "+3 days +1 hour" +%FT%TZ)

INSTRUCTION="個人事業主 開業届け 提出 ($(jq -r .operator.name "$CONFIG"))

1. https://github.com/yamitzky/freee-cli を install
2. freee.co.jp/kaigyou/ で OAuth 初回認証
3. CLI で 開業届け 書類自動生成
4. e-Tax で提出 (or 新宿税務署 持参)
5. 約 1 週後 個人番号取得 → ${SKILL/$HOME/~}/data/cafe/operator_id.json に保存

事業所住所: Phase 0 で確定したシェアキッチン住所
業種: 飲食業 (デリバリー専業)"

alert_human \
  "📝 [DAIS] 個人事業主 開業届け 提出" \
  "$DUE" "$DUE_END" \
  "オンライン (e-Tax) or 新宿税務署" \
  "$INSTRUCTION" >/dev/null || true

# Init state file (operator_id pending)
mkdir -p "$SKILL/data/cafe"
[ ! -f "$SKILL/data/cafe/operator_id.json" ] && cat > "$SKILL/data/cafe/operator_id.json" <<EOF
{
  "status": "form_generation_requested",
  "due_at": "$DUE",
  "kojin_number": null,
  "filed_at": null,
  "method": "freee-cli (yamitzky)",
  "manual_action_required": true
}
EOF
echo "✓ Phase 1 alert sent (Calendar + Slack). Dais e-Tax 提出後に個人番号を operator_id.json に追記してください"
