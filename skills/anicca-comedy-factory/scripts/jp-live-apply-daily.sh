#!/usr/bin/env bash
# anicca-comedy-factory — apply to amateur JP comedy lives (form/{{profile.lateness.stakeholders.channel}} entry)
# Sources that ACTUALLY accept free/amateur pin geinin via form/{{profile.lateness.stakeholders.channel}} (NOT X DM):
#   - U&C パワーオブフリー  http://uandcenterprise.jp/schedule.php?genre=newcomer
#                           entry: EMAIL to live_entry@yahoo.co.jp (entry.php は mailto のみ、Webフォーム無し)
#                           本文◆: 希望月日・曜日 / ライブ名 / ユニット名 / 人数(ピン) / ネタ形態(漫談) / 代表者名 / 電話番号
#                           名義: {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}} (Dais 2026-05-21 決定、本名出さない)
#                           venue: 新宿バッシュ (near 中野/信濃町), 3min neta
#                           ⚠ キャンセル料: 5日前〜発生 / 月2回 or 4割キャンセルで出演禁止
#   - 楽しいペチカ          https://amateurowarai.amebaownd.com/
#                           entry: tanoshiipetika@gmail.com ({{profile.lateness.stakeholders.channel}}), weekly, amateur
# NOTE: K-PRO ゲレロン removed — X DM only, not automatable.
#       たか7 小猿/肉食ライブ (なかの芸能小劇場) = X DM, manual fallback.
# Usage: ALL=true DAYS=14 bash scripts/jp-live-apply-daily.sh
# Recipe is replayable by ANY agent (CC / Anicca / any) — all logic here.
set -uo pipefail

SKILL=~/.openclaw/skills/anicca-comedy-factory
ALL="${ALL:-true}"; DAYS="${DAYS:-14}"; DRY_RUN="${DRY_RUN:-false}"
FC=/opt/homebrew/bin/firecrawl
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
source ~/.openclaw/skills/_shared/gcal-day.sh
mkdir -p "$SKILL/data/jp-live"

NOW=$(date -u +%FT%TZ); TODAY=$(date +%F)
CUTOFF=$(date -v+${DAYS}d +%F 2>/dev/null || gdate -d "+${DAYS} days" +%F)
echo "▶ jp-comedy-apply  ${NOW}  window=${TODAY}-${CUTOFF}  all=${ALL}  dry=${DRY_RUN}"

# ── gcal-first: busy map + travel buffer (→新宿バッシュ) ─────────────────────
HOME_BASE="${HOME_BASE:-$([ "$(date +%u)" -lt 6 ] && echo 中野 || echo 信濃町)}"
TRAVEL=$([ "$HOME_BASE" = "中野" ] && echo 20 || echo 18)   # →新宿
GCAL_BUSY=$(gog calendar events list --from "$TODAY" --to "$CUTOFF" --json 2>/dev/null \
  | jq -r '(.events//[])[]|(.start.dateTime//.start.date)' 2>/dev/null || echo "")
gcal_busy_on(){ [ -z "$GCAL_BUSY" ] && return 1; echo "$GCAL_BUSY" | grep -q "$1"; }
memory_has(){ curl -sS -X POST http://localhost:3111/agentmemory/search -H 'Content-Type: application/json' \
  -d "{\"query\":\"applied $1\",\"project\":\"anicca\"}" 2>/dev/null | jq -e '(.results//[])|length>0' >/dev/null 2>&1; }

apply_count=0

# ── Source A: U&C パワーオブフリー (entry = EMAIL to live_entry@yahoo.co.jp) ────
# entry.php は Web フォームではなく mailto。応募 = メール送信 (e2e 2026-05-21 確認)。
# OPEN 判定: ブロックに「エントリーあと」が在る回のみ。ライブ名(vol.千NN)も取得。
echo "  source: U&C パワーオブフリー"
UC_MD=$($FC scrape "http://uandcenterprise.jp/schedule.php?genre=newcomer" markdown 2>/dev/null)
CUR_Y=$(date +%Y); CUR_M=$(date +%-m)
printf '%s' "$UC_MD" | python3 -c "
import sys,re
cur_y=$CUR_Y; cur_m=$CUR_M
txt=sys.stdin.read()
for blk in re.split(r'(?=^### )', txt, flags=re.M):
    m=re.match(r'###\s*(\d+)/(\d+)\s*\(([^)]*)\)\s*([^\n]*)', blk)
    if not m: continue
    if 'エントリーあと' not in blk: continue   # open slots only
    mo,da,name=int(m.group(1)),int(m.group(2)),m.group(4).strip()
    y=cur_y if mo>=cur_m else cur_y+1
    print('%04d-%02d-%02d\t%s'%(y,mo,da,name))
" 2>/dev/null | while IFS=$'\t' read -r DATE_ISO LIVENAME; do
  [ -z "$DATE_ISO" ] && continue
  [ "$DATE_ISO" \< "$TODAY" ] && continue
  [ "$DATE_ISO" \> "$CUTOFF" ] && continue
  OUT="$SKILL/data/jp-live/uc-$DATE_ISO.json"
  jq -n --arg v "U&C パワーオブフリー" --arg date "$DATE_ISO" --arg venue "新宿バッシュ" \
        --arg entry "live_entry@yahoo.co.jp" --arg neta "3分" --arg source "uc" \
        --arg livename "${LIVENAME:-パワーオブフリー(Ｓ)}" \
        --arg discovered_at "$NOW" --argjson status null \
        '$ARGS.named' > "$OUT"
  echo "  + U&C open slot: $DATE_ISO 新宿バッシュ (${LIVENAME})"
done

# ── Source B: 楽しいペチカ ───────────────────────────────────────────────────
echo "  source: 楽しいペチカ"
PETIKA_MD=$($FC scrape "https://amateurowarai.amebaownd.com/" markdown 2>/dev/null)
# (parse schedule similarly — ameba ownd structure varies; capture dates if present)
echo "$PETIKA_MD" | grep -oE '[0-9]{1,2}/[0-9]{1,2}' 2>/dev/null | sort -u | head -8 | while read -r MD; do
  M=$(echo "$MD" | cut -d/ -f1); D=$(echo "$MD" | cut -d/ -f2)
  Y=$CUR_Y; [ "$M" -lt "$CUR_M" ] && Y=$((CUR_Y+1))
  DATE_ISO=$(printf "%04d-%02d-%02d" "$Y" "$M" "$D" 2>/dev/null) || continue
  [ "$DATE_ISO" \< "$TODAY" ] && continue
  [ "$DATE_ISO" \> "$CUTOFF" ] && continue
  OUT="$SKILL/data/jp-live/petika-$DATE_ISO.json"
  jq -n --arg v "楽しいペチカ" --arg date "$DATE_ISO" --arg venue "都内" \
        --arg entry "tanoshiipetika@gmail.com" --arg neta "3分" \
        --arg discovered_at "$NOW" --argjson status null \
        '$ARGS.named' > "$OUT" 2>/dev/null && echo "  + ペチカ candidate: $DATE_ISO"
done

# ── Apply loop ───────────────────────────────────────────────────────────────
for EV in "$SKILL/data/jp-live/"*.json; do
  [ -f "$EV" ] || continue
  [ "$(jq -r '.status' "$EV")" = "null" ] || continue
  VENUE=$(jq -r '.v' "$EV"); DATE=$(jq -r '.date' "$EV"); ENTRY=$(jq -r '.entry' "$EV"); PLACE=$(jq -r '.venue' "$EV")
  SRC=$(jq -r '.source // ""' "$EV"); LIVENAME=$(jq -r '.livename // .v' "$EV")
  echo "  → apply: $VENUE $DATE ($PLACE)"
  gcal_day_has_event "$DATE" && { echo "    ⏭ HARD RULE: $DATE already has a night event — skip (no double booking)"; continue; }
  memory_has "$VENUE $DATE" && { echo "    ⏭ already applied (memory)"; continue; }
  if [ "$DRY_RUN" = "true" ]; then echo "    [DRY] skip submit"; continue; fi

  # 曜日(漢字) + M/D for the entry body
  WK=("" 月 火 水 木 金 土 日)
  DOW_N=$(date -j -f "%Y-%m-%d" "$DATE" +%u 2>/dev/null || gdate -d "$DATE" +%u)
  DOW_K="${WK[$DOW_N]}"
  M_S=$(echo "$DATE" | cut -d- -f2 | sed 's/^0//'); D_S=$(echo "$DATE" | cut -d- -f3 | sed 's/^0//')

  # Submit entry (real {{profile.lateness.stakeholders.channel}}; {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}名義 per Dais 2026-05-21 decision):
  if [ "$SRC" = "uc" ]; then
    # U&C パワーオブフリー: live_entry@yahoo.co.jp に mailto テンプレ通り送信
    printf '希望月日・曜日◆ %s/%s(%s)\n\nライブ名◆ %s\n\nユニット名◆ {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}\n\n人数(ピンorコンビorトリオ)◆ ピン\n\nネタ形態(漫才orコントor漫談)◆ 漫談\n\n代表者名(必ず本名)◆ {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}\n\n電話番号◆ %s\n\nよろしくお願いいたします。' \
      "$M_S" "$D_S" "$DOW_K" "$LIVENAME" "${DAIS_PHONE:-}" \
      | gog gmail send --to "$ENTRY" --subject "ライブ出演希望" --body-file - 2>&1 | tail -1 \
      && echo "    ✓ U&C entry mail sent → $ENTRY ($DATE $LIVENAME)" || echo "    ⚠ U&C mail send failed"
  elif echo "$ENTRY" | grep -q "@"; then
    # ペチカ: 汎用エントリーメール
    printf 'お笑いライブ出演申込\n\n出演希望日: %s/%s(%s)\n芸名: {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}\nネタ: ピン・漫談・3分\n連絡先: %s\n\nよろしくお願いいたします。' \
      "$M_S" "$D_S" "$DOW_K" "${DAIS_EMAIL:-{{profile.contact.personalEmail}}}" \
      | gog gmail send --to "$ENTRY" --subject "【出演申込】${M_S}/${D_S}(${DOW_K}) {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}" --body-file - 2>&1 | tail -1 \
      && echo "    ✓ ペチカ entry mail sent → $ENTRY ($DATE)" || echo "    ⚠ mail send failed"
  fi

  # gcal create with travel buffer
  SL="${DATE}T19:00:00"; START="${SL}+09:00"; END="${DATE}T21:00:00+09:00"
  DEP=$(date -j -v-${TRAVEL}M -f "%Y-%m-%dT%H:%M:%S" "$SL" "+%Y-%m-%dT%H:%M:%S+09:00" 2>/dev/null || echo "${SL}+09:00")
  gog calendar create primary --summary "🎤 [PENDING] $VENUE" --from "$DEP" --to "$END" \
    --location "$PLACE" --description "出発:${DEP} ${HOME_BASE}->新宿 ${TRAVEL}分 開始:${START} entry:${ENTRY}" 2>&1 | tail -1 || true
  # memory + daily-memory
  curl -sS -X POST http://localhost:3111/agentmemory/observe -H 'Content-Type: application/json' \
    -d "{\"hookType\":\"manual\",\"sessionId\":\"apply-jp-comedy\",\"project\":\"anicca\",\"cwd\":\"$SKILL\",\"timestamp\":\"$NOW\",\"content\":\"applied JP comedy $VENUE $DATE $PLACE entry $ENTRY — awaiting confirmation\",\"tags\":[\"apply\",\"comedy\",\"jp\",\"awaiting-reply\"]}" >/dev/null 2>&1 || true
  echo "- [$(date +%H:%M)] applied JP comedy: $VENUE ($DATE) $PLACE travel ${TRAVEL}min → gcal PENDING" >> "$HOME/.openclaw/workspace/daily-memory/$(date +%F).md"
  jq '.status="applied"' "$EV" > "$EV.tmp" && mv "$EV.tmp" "$EV"
  apply_count=$((apply_count+1)); [ "$ALL" != "true" ] && break
done

echo "✅ jp comedy applied $apply_count slots (U&C+ペチカ, next${DAYS}d, gcal+travel)"
