#!/usr/bin/env bash
# Anicca v3.2 lang-detect — minimal language detection helper.
#
# Public API:
#   ld_detect <file-or-string>   echoes "en" / "ja" / "und" to stdout.
#
# Strategy: prefer python3 langdetect; fall back to heuristic
# (kanji/kana present → ja; otherwise ascii-heavy → en).

ld_detect() {
  local input="$1"
  local text
  if [ -f "$input" ]; then
    text="$(cat "$input")"
  else
    text="$input"
  fi

  # Heuristic fast path: any Japanese codepoint → ja
  if printf '%s' "$text" | LC_ALL=C grep -qE $'[\xE3-\xEF]'; then
    echo "ja"
    return 0
  fi

  # Try python langdetect if available.
  # IMPORTANT: heredoc delimiter is single-quoted ('PY') so $text is NOT shell-expanded.
  # The caption is piped on stdin and read by Python, treating it as data not code.
  # Without this, captioned content like '""")\nimport os; os.system(...)' could
  # execute arbitrary code (HIGH-severity shell→python injection).
  if command -v python3 >/dev/null 2>&1; then
    local out
    out="$(printf '%s' "$text" | python3 - <<'PY' 2>/dev/null
import sys
try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0
    sys.stdout.write(detect(sys.stdin.read()))
except Exception:
    pass
PY
)"
    if [ -n "$out" ]; then
      echo "$out"
      return 0
    fi
  fi

  # Fallback: ascii ratio > 0.7 → en
  local ascii non_ascii ratio
  ascii=$(printf '%s' "$text" | LC_ALL=C tr -cd '\11\12\15\40-\176' | wc -c)
  total=$(printf '%s' "$text" | wc -c)
  if [ "$total" -gt 0 ] && [ "$ascii" -gt 0 ] && [ "$((ascii * 10 / total))" -ge 7 ]; then
    echo "en"
    return 0
  fi

  echo "und"
}

# If invoked directly (not sourced), run on $1
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  ld_detect "$1"
fi
