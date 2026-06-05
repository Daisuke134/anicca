#!/usr/bin/env bash
# humanizer-ja/scripts/score.sh
# Deterministic keyword-based AI-likelihood scorer for Japanese text.
# Usage: score.sh <json_file> <id1> [id2..]
# Output: JSON array [{id, ai_likelihood, axes}]
#
# 10 axes (mapped from Wikipedia "Signs of AI writing" + humanizer-ja 20 rules):
#   1. hedging          : 「〜と言えるでしょう」「〜ではないでしょうか」等
#   2. overemphasis     : 「重要な」「極めて」「計り知れない」「画期的」
#   3. templatePhrasing : 「浮き彫り」「多面的」「包括的」「示唆を与えている」「注目」
#   4. katakanaOveruse  : カタカナ語 3+ 連続
#   5. abstractSubject  : 「あなたは〜です」「私たちは〜です」直訳臭
#   6. excessiveLength  : 50 chars 超過 (affirmation = 短く)
#   7. punctuationOveruse : 「、、」「！！」過剰句読点
#   8. lowSpecificity   : 数字・固有名詞 0 件 (一般論のみ)
#   9. passiveVoice     : 「〜される」「〜されている」連発
#  10. neutrality       : 無感情語 (「ある」「いる」「です」のみ、 感情詞 0)
#
# Each axis 0-10、 sum = ai_likelihood 0-100

set -euo pipefail

JSON_FILE="${1:?json_file required}"
shift
IDS=("$@")

if [[ ${#IDS[@]} -eq 0 ]]; then
  echo "[]"
  exit 0
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "[]"
  exit 0
fi

score_quote() {
  local text="$1"

  # Axis 1: hedging
  local hedging=0
  grep -qE 'でしょう|ではないでしょうか|かもしれません|と思われます' <<<"$text" && hedging=8 || hedging=0

  # Axis 2: overemphasis
  local emphasis=0
  for kw in '重要' '極めて' '計り知れない' '画期的' '革新的' '素晴らしい' '完璧'; do
    grep -q "$kw" <<<"$text" && emphasis=$((emphasis + 3))
  done
  [[ $emphasis -gt 10 ]] && emphasis=10

  # Axis 3: templatePhrasing
  local template=0
  for kw in '浮き彫り' '多面的' '包括的' '示唆を与え' '注目に値' 'と言えるでしょう'; do
    grep -q "$kw" <<<"$text" && template=$((template + 5))
  done
  [[ $template -gt 10 ]] && template=10

  # Axis 4: katakanaOveruse (3+ katakana words consecutive)
  local katakana=0
  if grep -qE '[ァ-ヶー]{3,}[\s　]?[ァ-ヶー]{3,}[\s　]?[ァ-ヶー]{3,}' <<<"$text"; then
    katakana=8
  elif grep -qE '[ァ-ヶー]{6,}' <<<"$text"; then
    katakana=4
  fi

  # Axis 5: abstractSubject (you-are / we-are 直訳臭)
  local abstract=0
  for pat in 'あなたは.*です' 'あなたは.*なのです' '私たちは.*です' 'あなたは.*持って' 'あなたは.*できる' '価値ある人間'; do
    grep -qE "$pat" <<<"$text" && abstract=$((abstract + 3))
  done
  [[ $abstract -gt 10 ]] && abstract=10

  # Axis 6: excessiveLength
  local len=${#text}
  local length=0
  if [[ $len -gt 80 ]]; then length=10
  elif [[ $len -gt 60 ]]; then length=6
  elif [[ $len -gt 45 ]]; then length=2
  fi

  # Axis 7: punctuationOveruse
  local punct=0
  local commas
  commas=$(echo "$text" | tr -cd '、' | wc -c | tr -d ' ')
  [[ $commas -gt 4 ]] && punct=8
  [[ $commas -gt 3 ]] && [[ $punct -eq 0 ]] && punct=4

  # Axis 8: lowSpecificity (no numbers/proper nouns)
  local specificity=0
  if ! grep -qE '[0-9]|[一-九]+月|[一-九]+日|時|朝|夜|今日|明日' <<<"$text"; then
    specificity=6
  fi

  # Axis 9: passiveVoice (「されている」連発)
  local passive=0
  local passive_count
  passive_count=$(echo "$text" | grep -oE 'されて|される' | wc -l | tr -d ' ')
  [[ $passive_count -ge 2 ]] && passive=6
  [[ $passive_count -ge 1 ]] && [[ $passive -eq 0 ]] && passive=2

  # Axis 10: neutrality (感情・五感ゼロ)
  local neutrality=0
  if ! grep -qE '光|風|香り|味|音|色|温|冷|優|柔|穏やか|静か|微笑|笑|涙|静|愛|喜|悲|怒|呼吸|心|手|目|耳' <<<"$text"; then
    neutrality=8
  fi

  local total=$((hedging + emphasis + template + katakana + abstract + length + punct + specificity + passive + neutrality))

  # Output single JSON object on stdout
  jq -nc \
    --arg id "$ID" \
    --argjson hedging "$hedging" \
    --argjson emphasis "$emphasis" \
    --argjson template "$template" \
    --argjson katakana "$katakana" \
    --argjson abstract "$abstract" \
    --argjson length "$length" \
    --argjson punct "$punct" \
    --argjson specificity "$specificity" \
    --argjson passive "$passive" \
    --argjson neutrality "$neutrality" \
    --argjson total "$total" \
    '{
      id: $id,
      ai_likelihood: $total,
      axes: {
        hedging: $hedging,
        overemphasis: $emphasis,
        templatePhrasing: $template,
        katakanaOveruse: $katakana,
        abstractSubject: $abstract,
        excessiveLength: $length,
        punctuationOveruse: $punct,
        lowSpecificity: $specificity,
        passiveVoice: $passive,
        neutrality: $neutrality
      }
    }'
}

RESULTS=()
for ID in "${IDS[@]}"; do
  # Try to extract by ID. Support:
  # - flat: {"q024": "text"}
  # - nested: {"quotes": {"q024": "text"}}
  # - nested object: {"quotes": {"q024": {"text": "..."}}}
  # - array: [{"id": "q024", "text": "..."}]
  TEXT=$(jq -r --arg id "$ID" '
    if type == "object" then
      (.quotes[$id] // .[$id])
      | (if type == "string" then . elif type == "object" then (.text // .body // "") else "" end)
    elif type == "array" then
      (.[] | select(.id == $id) | .text // .body // "") // ""
    else
      ""
    end
  ' "$JSON_FILE" 2>/dev/null || echo "")

  if [[ -z "$TEXT" || "$TEXT" == "null" ]]; then
    # Missing quote → score 100 (force fail)
    RESULTS+=("$(jq -nc --arg id "$ID" '{id: $id, ai_likelihood: 100, axes: {}, error: "quote not found"}')")
    continue
  fi
  RESULT=$(score_quote "$TEXT")
  RESULTS+=("$RESULT")
done

# Combine into JSON array
printf '[%s]\n' "$(IFS=,; echo "${RESULTS[*]}")"
