#!/usr/bin/env bash
# apply.sh — generate the proposal message and (if --confirm) submit it.
# stdin: JSON array of candidate objects from select.sh
# stdout: JSON array of {jid, url, generated_message, status} per candidate.
#
# Modes:
#   --dry-run         → DO NOT call cf_evaluate, DO NOT touch the runs log,
#                       generated_message stops at the proposal text, status="dry-run".
#   --confirm         → execute the proven 2-stage submit
#                       (propose_start → propose_confirm → propose_finish).
#                       Append one JSONL row per candidate to
#                       ~/.hermes/state/earn-lancers-runs.jsonl (HERMES_STATE_DIR overridable).
#   --max-apply N     → hard cap on submits per run (default 3 in run.sh; here we honor whatever caller passes).
#   --max-budget-jpy B → in --confirm mode, skip candidates with budget > B (safety bound).

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

DRY_RUN=true
CONFIRM=false
MAX_APPLY=3
MAX_BUDGET_JPY=0   # 0 = no cap
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=true; CONFIRM=false; shift ;;
    --confirm) DRY_RUN=false; CONFIRM=true; shift ;;
    --max-apply) MAX_APPLY="$2"; shift 2 ;;
    --max-budget-jpy) MAX_BUDGET_JPY="$2"; shift 2 ;;
    *) shift ;;
  esac
done

INPUT=$(cat)
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="${HERMES_STATE_DIR:-$HOME/.hermes/state}"
APPLY_LOG="$STATE_DIR/earn-lancers-runs.jsonl"
mkdir -p "$STATE_DIR"

generate_message() {
  local jid="$1" title="$2" budget="$3"
  cat <<MSG
はじめまして。 自律 AI を 中核に持つ 制作チーム Anicca です。

【ご提案 内容】 ${title} を ¥${budget} で 制作。 24-48h 納品。

【強み】 AI 音声合成 (ElevenLabs / OpenAI) + Remotion+ffmpeg コード化パイプラインで 量産可能。 24h 受付・並列処理 可。

【納品まで】 (1) 仕様 / スクリプト 連絡 (2) AI 生成 (素材/voice/字幕) (3) 編集+BGM (4) 成果物 をランサーズ メッセージで共有 → 修正 → 完納。

【納期】 1本 24-48h。 複数本 一括も 1週間で 5-10本 可。

【継続】 月単位の 単価アップ ご相談 可能。

ご検討 よろしく お願いいたします。  Anicca / 成田 大祐
MSG
}

# Build the output array
RESULT='[]'
COUNT=0
echo "$INPUT" | "$JQ" -c '.[]' | while IFS= read -r row; do
  JID=$(echo "$row" | "$JQ" -r '.jid')
  TITLE=$(echo "$row" | "$JQ" -r '.title_truncated')
  BUDGET=$(echo "$row" | "$JQ" -r '.budget_jpy')
  URL_DETAIL="https://www.lancers.jp/work/detail/$JID"
  MSG=$(generate_message "$JID" "$TITLE" "$BUDGET")

  if $DRY_RUN; then
    OUT_ROW=$("$JQ" -n --arg jid "$JID" --arg url "$URL_DETAIL" --arg msg "$MSG" \
      --argjson budget "$BUDGET" --arg title "$TITLE" \
      --argjson eff "$(echo "$row" | "$JQ" '.effort_estimate')" \
      --argjson score "$(echo "$row" | "$JQ" '.score')" \
      '{jid:$jid, url:$url, title_truncated:$title, budget_jpy:$budget,
        effort_estimate:$eff, score:$score,
        generated_message:$msg, status:"dry-run"}')
    echo "$OUT_ROW"
    continue
  fi

  # ── LIVE submit ────────────────────────────────────────────────────────
  # Safety bound: budget cap
  if [ "$MAX_BUDGET_JPY" -gt 0 ] && [ "$BUDGET" -gt "$MAX_BUDGET_JPY" ]; then
    log "skip JID=$JID budget=$BUDGET > cap=$MAX_BUDGET_JPY"
    continue
  fi
  # Safety bound: per-run cap
  COUNT=$((COUNT+1))
  if [ "$COUNT" -gt "$MAX_APPLY" ]; then
    log "reached --max-apply $MAX_APPLY — stop"
    break
  fi

  cf_health || { err "camofox down mid-apply"; break; }

  TAB=$(cf_open "https://www.lancers.jp/work/propose_start/$JID")
  sleep 6
  SNAP=$(cf_snapshot "$TAB")
  STATE=$(SNAP="$SNAP" "$PYTHON" -c '
import json,os
d=json.loads(os.environ.get("SNAP","{}") or "{}"); snap=d.get("snapshot",""); url=d.get("url","")
if "propose_start" not in url: print("REDIRECT")
elif "提案できません" in snap: print("BLOCKED")
elif "data[Proposal]" in snap or "提案文" in snap: print("OPEN")
else: print("UNKNOWN")
')
  if [ "$STATE" != "OPEN" ]; then
    log "JID=$JID state=$STATE — skip"
    cf_close "$TAB"
    OUT_ROW=$("$JQ" -n --arg jid "$JID" --arg url "$URL_DETAIL" --arg s "$STATE" \
      '{jid:$jid, url:$url, status:("skip:" + $s)}')
    echo "$OUT_ROW"
    continue
  fi

  # The proven JS — ported verbatim from
  # ~/.openclaw/skills/_archive/hybrid-v1/cfo-earner-lancers/scripts/run.sh lines 159-188
  APPLY_JS=$(MSG="$MSG" BUDGET="$BUDGET" "$PYTHON" - <<'PYEOF'
import json, os
prop  = os.environ["MSG"]
title = "AI動画制作 1本納品"
ms_desc = "AI 動画 1本 (1-3min) を MP4 で 納品。 ご希望の voice / フォーマット / 字幕 に 合わせて 24-48h で 初稿、 修正 1 回まで 無料。"
amount = os.environ["BUDGET"]
js = f"""(async()=>{{
  const setT=(el,v)=>{{
    if(!el) return false;
    const proto=el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto,'value').set.call(el,v);
    el.dispatchEvent(new Event('input',{{bubbles:true}}));
    el.dispatchEvent(new Event('change',{{bubbles:true}}));
    return true;
  }};
  const propTA=document.querySelector('textarea[name="data[Proposal][description]"]');
  if(!propTA) return JSON.stringify({{err:'no_prop_ta'}});
  setT(propTA, {json.dumps(prop)});
  setT(document.querySelector('input[name="data[Milestone][10][title]"]'), {json.dumps(title)});
  setT(document.querySelector('input[name="data[Milestone][10][schedule][year]"]'), '2026');
  setT(document.querySelector('input[name="data[Milestone][10][schedule][month]"]'), '6');
  setT(document.querySelector('input[name="data[Milestone][10][schedule][day]"]'), '15');
  setT(document.querySelector('textarea[name="data[Milestone][10][description]"]'), {json.dumps(ms_desc)});
  setT(document.querySelector('input[name="data[Milestone][10][amount_exclude_tax]"]'), '{amount}');
  await new Promise(r=>setTimeout(r,2000));
  const submit=document.querySelector('input[type=submit][name="send"]');
  if(!submit) return JSON.stringify({{err:'no_submit'}});
  submit.click();
  await new Promise(r=>setTimeout(r,15000));
  return JSON.stringify({{url:location.href}});
}})()"""
print(js)
PYEOF
)

  cf_evaluate "$TAB" "$APPLY_JS" >/dev/null || true
  sleep 8

  URL_CHECK=$(cf_snapshot "$TAB" | "$JQ" -r '.url // ""')
  STATUS="submit_failed"
  FINAL_URL=""
  if [[ "$URL_CHECK" == *"propose_confirm"* ]]; then
    FINAL_JS='(async()=>{const s=document.querySelector("input[type=submit][value=\"利用規約に同意して提案する\"]");if(!s)return JSON.stringify({err:"no_final"});s.click();await new Promise(r=>setTimeout(r,12000));return JSON.stringify({url:location.href});})()'
    cf_evaluate "$TAB" "$FINAL_JS" >/dev/null || true
    sleep 8
    FINAL_URL=$(cf_snapshot "$TAB" | "$JQ" -r '.url // ""')
    if [[ "$FINAL_URL" == *"propose_finish"* ]]; then
      STATUS="applied"
    else
      STATUS="final_click_failed"
    fi
  fi
  cf_close "$TAB"

  TS=$(date -u +%FT%TZ)
  ROW_LOG=$("$JQ" -n --arg ts "$TS" --arg jid "$JID" --arg status "$STATUS" \
                  --argjson amt "$BUDGET" --arg furl "$FINAL_URL" \
                  '{ts:$ts, jid:$jid, status:$status, amount:$amt, finish_url:$furl}')
  printf '%s\n' "$ROW_LOG" >> "$APPLY_LOG"

  OUT_ROW=$("$JQ" -n --arg jid "$JID" --arg url "$URL_DETAIL" --arg msg "$MSG" \
                   --arg status "$STATUS" --arg furl "$FINAL_URL" \
                   '{jid:$jid, url:$url, generated_message:$msg, status:$status, finish_url:$furl}')
  echo "$OUT_ROW"
done | "$JQ" -s '.'
