#!/usr/bin/env bash
# One-time helper: list candidate HeyGen voices for the given language,
# so human can pick one and write it to characters/$LANG/voice_id.txt
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"

LANG="${1:-}"
if [ "$LANG" != "en" ] && [ "$LANG" != "jp" ]; then
  echo "usage: $0 en|jp"; exit 2
fi

case "$LANG" in
  en) LC=en ;;
  jp) LC=ja ;;
esac

echo "Candidate voices (language=$LC):"
heygen voice list --language "$LC" --human 2>&1 | head -50

echo
echo "Paste the chosen voice ID, then press Enter:"
read -r PICKED
if [ -z "$PICKED" ]; then
  echo "no id entered, aborting"; exit 1
fi

mkdir -p "$HOME/anicca-monk-factory/characters/$LANG"
echo "$PICKED" > "$HOME/anicca-monk-factory/characters/$LANG/voice_id.txt"
echo "✅ saved to characters/$LANG/voice_id.txt"
