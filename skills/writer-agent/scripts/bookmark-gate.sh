#!/usr/bin/env bash
set -uo pipefail
TITLE="${1:-}"
BODY_FILE="${2:-}"
LANGUAGE=""
if [ "${3:-}" = "--lang" ]; then
  LANGUAGE="${4:-}"
elif [ -n "${3:-}" ]; then
  echo "FATAL: usage: bookmark-gate.sh TITLE BODY_FILE [--lang ja|en]" >&2
  exit 2
fi
[ -n "$TITLE" ] && [ -f "$BODY_FILE" ] || {
  echo "FATAL: usage: bookmark-gate.sh TITLE BODY_FILE [--lang ja|en]" >&2
  exit 2
}
if [ -z "$LANGUAGE" ]; then
  if printf '%s\n' "$TITLE" | grep -q '[ぁ-んァ-ヶ一-龠々]'; then
    LANGUAGE="ja"
  else
    LANGUAGE="en"
  fi
fi
case "$LANGUAGE" in
  ja|en) ;;
  *) echo "FATAL: --lang must be ja or en" >&2; exit 2 ;;
esac

N=$(echo "$TITLE $(cat "$BODY_FILE" 2>/dev/null)" | grep -oE '[0-9]+%?' | wc -l | tr -d ' ')
if [ "$LANGUAGE" = "ja" ]; then
  NAMES=$(python3 - "$TITLE" <<'PY'
import re
import sys

title = sys.argv[1]
anchors = re.findall(r"[A-Z][A-Za-z0-9.+-]*|[ァ-ヿー]{2,}", title)
if len(anchors) < 2:
    anchors.extend(re.findall(r"「[^」]{2,}」|『[^』]{2,}』", title))
print(len(anchors))
PY
)
  A=$(grep -cE \
    '(^[[:space:]]*([0-9]+[.)]|[-*][[:space:]]+).*(確認|実行|登録|検索|比較|測|設定|導入|使|試|保存|選|記録|調べ|探|返す|計算|続ける|する)|^#{1,6}[[:space:]]*([0-9]+[.)][[:space:]]*)?.*(手順|方法|やり方|確認|導入|測定))' \
    "$BODY_FILE" 2>/dev/null)
else
  NAMES=$(echo "$TITLE" | grep -oE '\b[A-Z][a-z]+' | wc -l | tr -d ' ')
  A=$(grep -ciE 'how to|here.*how|step.*[0-9]' "$BODY_FILE" 2>/dev/null)
fi
A="${A:-0}"
[ "$N" -lt 1 ] && { echo "FAIL no numbers"; exit 1; }
[ "$NAMES" -lt 2 ] && { echo "FAIL names<2"; exit 1; }
[ "$A" -lt 1 ] && { echo "FAIL not actionable"; exit 1; }
echo "OK N=$N NAMES=$NAMES A=$A"
