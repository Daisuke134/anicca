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

  # Try python langdetect if available
  if command -v python3 >/dev/null 2>&1; then
    local out
    out="$(python3 - <<PY 2>/dev/null
try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0
    import sys
    sys.stdout.write(detect("""$text"""))
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
