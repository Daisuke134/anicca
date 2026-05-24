#!/usr/bin/env bash
# MODE=jp_report — annual JP 政治団体 収支報告書 prep.
# Stays DRY until JP_SEIJIDANTAI_REGISTERED=true.
set -euo pipefail
SKILL="${SKILL:-$(cd "$(dirname "$0")/.." && pwd)}"
MODE=jp_report
source "$SKILL/scripts/lib/slack_format.sh"

DRY="${POLITICIAN_DRY_RUN:-true}"
JP="${JP_SEIJIDANTAI_REGISTERED:-false}"

YEAR="$(date -u +%Y)"
mkdir -p "$SKILL/data/filings/jp" "$SKILL/data/sign_acks"
DRAFT_PATH="$SKILL/data/filings/jp/${YEAR}.shushihokoku.draft.md"

if [[ "$DRY" == "true" || "$JP" != "true" ]]; then
  cat >&2 <<EOF
[would-prepare 政治団体 収支報告書 for $YEAR]
  団体名: <pending — politician.jp_seijidantai_name not yet set>
  会計責任者: <pending — humans.yaml: jp_kaikei_sekininsha not yet set>
  収入合計: <from JP Stripe + 寄附 ledger>
  支出合計: <from JP expenditures ledger>
  output: $DRAFT_PATH
  human-signoff sentinel: $SKILL/data/sign_acks/${YEAR}-jp.signed.json
  manual upload: https://www.soumu.go.jp/senkyo/seiji_s/seijishikin/
  deadline: 翌年5月末（諸団体）
EOF
  slack_post "📒 JP 収支報告書 prep" \
    "year=$YEAR 収入=stub 支出=stub unlock=DRY (JP_SEIJIDANTAI_REGISTERED=$JP POLITICIAN_DRY_RUN=$DRY)"
  exit 0
fi

# LIVE path (JP_SEIJIDANTAI_REGISTERED=true && POLITICIAN_DRY_RUN=false) — never auto-submits.
LEDGER="$HOME/.openclaw/state/politician/jp-ledger.jsonl"
mkdir -p "$(dirname "$LEDGER")"; [[ -f "$LEDGER" ]] || : > "$LEDGER"

DANTAI_NAME="$(python3 -c "import json,os;p='$HOME/.openclaw/state/anicca.json';d=json.load(open(p)) if os.path.exists(p) else {};print((d.get('politician') or {}).get('jp_seijidantai_name') or '')")"
KAIKEI_NAME="$(python3 -c "import yaml;d=yaml.safe_load(open('$SKILL/data/humans.yaml'));print((d.get('jp_kaikei_sekininsha') or {}).get('{{profile.lateness.stakeholders.senderType}}_name') or '')")"

# Aggregate 収入 / 支出 for the calendar year, by 様式.
AGG_JSON="$(python3 - "$LEDGER" "$YEAR" <<'PY'
import json, sys
shunyu = 0.0; shishutsu = 0.0; shunyu_rows = []; shishutsu_rows = []
with open(sys.argv[1]) as f:
    for ln in f:
        ln = ln.strip()
        if not ln: continue
        try: r = json.loads(ln)
        except Exception: continue
        if not r.get("date","").startswith(sys.argv[2]): continue
        amt = float(r.get("amount_jpy") or 0)
        if r.get("type") == "shunyu":
            shunyu += amt; shunyu_rows.append(r)
        elif r.get("type") == "shishutsu":
            shishutsu += amt; shishutsu_rows.append(r)
print(json.dumps({"shunyu_total":shunyu,"shishutsu_total":shishutsu,
                  "shunyu_rows":shunyu_rows,"shishutsu_rows":shishutsu_rows}))
PY
)"

# Render 様式9/10/11 prefill bundle.
{
  echo "# 収支報告書（${YEAR}年分）"
  echo ""
  echo "## 様式9 — 収支報告書本体"
  echo "- 政治団体名: ${DANTAI_NAME}"
  echo "- 会計責任者: ${KAIKEI_NAME}"
  echo "- 報告対象期間: ${YEAR}-01-01 〜 ${YEAR}-12-31"
  echo "- 収入合計: ¥$(jq -r '.shunyu_total' <<< "$AGG_JSON")"
  echo "- 支出合計: ¥$(jq -r '.shishutsu_total' <<< "$AGG_JSON")"
  echo ""
  echo "## 様式10 — 収入の内訳"
  jq -r '.shunyu_rows[]? | "- \(.date) ¥\(.amount_jpy) — \(.source // "")"' <<< "$AGG_JSON"
  echo ""
  echo "## 様式11 — 支出の内訳"
  jq -r '.shishutsu_rows[]? | "- \(.date) ¥\(.amount_jpy) — \(.purpose // "")"' <<< "$AGG_JSON"
} > "$DRAFT_PATH"

PORTAL_LIVE="https://kyoudou.soumu.go.jp/kyoudou/GK020202_13"
HARNESS_LOG="$SKILL/data/filings/jp/${YEAR}.harness.log"
if curl -fsS --max-time 5 http://127.0.0.1:9223/json/version >/dev/null 2>&1; then
  curl -fsS -X PUT "http://127.0.0.1:9223/json/new?$(printf '%s' "$PORTAL_LIVE" | jq -sRr @uri)" >"$HARNESS_LOG" 2>&1 || true
  HARNESS_STATUS="opened"
else
  HARNESS_STATUS="harness-unavailable"
fi

SH=$(jq -r '.shunyu_total' <<< "$AGG_JSON")
SS=$(jq -r '.shishutsu_total' <<< "$AGG_JSON")
slack_post "📒 JP 収支報告書 prep" \
  "year=$YEAR 収入=¥${SH} 支出=¥${SS} draft=\"$DRAFT_PATH\" harness=$HARNESS_STATUS sign_status=awaiting-会計責任者-click"
