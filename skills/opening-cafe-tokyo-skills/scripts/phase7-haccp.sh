#!/usr/bin/env bash
# phase7-haccp.sh — generate HACCP 衛生管理計画書 for Mango Reset.
#
# Output: data/cafe/haccp-plan.md (overwrite, idempotent)
#         data/cafe/haccp-plan.docx (optional Word export, future)
#
# This file gets uploaded to Uber Eats Merchant signup as part of the food
# safety documentation, and printed for posting in the kitchen.
#
# stdout final line:
#   ✅ haccp: <line_count> lines written → data/cafe/haccp-plan.md
#   ❌ haccp FAILED: <reason>

set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
DATA_DIR="$SKILL/data/cafe"
HACCP_FILE="$DATA_DIR/haccp-plan.md"
mkdir -p "$DATA_DIR"

set -a; source "$HOME/.openclaw/.env"; set +a

PYTHON="python3"

LOG_DIR="$SKILL/output/$(date +%Y-%m-%d)_haccp"
mkdir -p "$LOG_DIR"

PROMPT_FILE="$LOG_DIR/prompt.txt"
cat > "$PROMPT_FILE" <<'PROMPT_EOF'
You are generating a HACCP 衛生管理計画書 (food safety plan) in Japanese for a single-product Tokyo ghost-kitchen operation.

Operation:
  - Product: Anicca Cafe — Mango Reset, ¥1,500 / 350ml
  - Process: cold-pressed Mexican mango → blended in a household-grade Vitamix → poured into 350ml black PET bottles → labeled → handed to Uber Eats courier within 30 minutes of preparation
  - Location: shared ghost kitchen in Tokyo (kashispace / kumato / theghostrestaurant tier)
  - Operator: 1 person, weekend-only operation initially (sat/sun, ~5h each)
  - No reheating, no cooking, no allergen variants. Single SKU.

Deliverable: a complete HACCP-based 衛生管理計画書 in Markdown, in Japanese, suitable for filing with 保健所 + Uber Eats Merchant docs.

Sections to include (in this order):
  1. 施設の概要 (operator name placeholder, address placeholder, kitchen platform placeholder)
  2. メニュー一覧 (Mango Reset 1 SKU)
  3. 原材料 一覧 (mango, water, ice — and no allergens)
  4. 一般的な衛生管理 (general sanitation: handwashing, cleaning, equipment, water supply, pests, waste, personal hygiene)
  5. 重要管理点 (CCP) — for cold-pressed mango juice the main CCP is temperature & time control between blending and customer pickup. Specify:
     - 受入時マンゴー温度 ≤10°C (即冷蔵)
     - ブレンド〜配達員 pickup 時間 ≤30分
     - PET ボトル充填温度 ≤5°C (氷水で急冷)
     - 室温 (20°C 以上) 連続 30 分以上 = 廃棄
  6. 記録 (daily log template: date, batches made, pickup times, deviation log, corrective actions)
  7. アレルゲン情報 (mango = フルーツアレルギー、その他 28品目 該当なし)
  8. 緊急時の対応 (food poisoning suspicion → immediate stop, 保健所 contact, Uber Eats merchant suspension)
  9. 教育・訓練計画 (operator self-study annual)

Output ONLY the Markdown body (no commentary). Use H1/H2/H3 headers. Use placeholders like `{{OPERATOR_NAME}}`, `{{KITCHEN_NAME}}`, `{{KITCHEN_ADDRESS}}`, `{{LICENSE_NUMBER}}` for fields that will be filled in after kitchen contract.
PROMPT_EOF

echo "  generating HACCP plan via Claude haiku..."

# === HARD RULE #6: HACCP generation delegated to cron model ===
echo "⚠ HACCP LLM step skipped — cron model must read $PROMPT_FILE and write plan to $HACCP_FILE per SKILL.md" >&2
cat > "$HACCP_FILE" <<'HACCP_STUB'
# HACCP 衛生管理計画書

⚠️ LLM step delegated to cron model (HARD RULE #6).
See SKILL.md — cron model invoking this skill must generate the plan from the prompt file.
HACCP_STUB
if true; then
else
  echo "❌ haccp FAILED: $(head -3 "$LOG_DIR/claude.err")"
  exit 1
fi
