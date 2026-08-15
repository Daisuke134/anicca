#!/usr/bin/env bash
# producer.sh — EARN-2 affiliate FUEL. Turn a deck.json (the brain writes the educational slideshow
# text — NL judgment, model-agnostic) into a verified 1080x1920 carousel in ~/affiliate/queue/<id>/.
# Deliver (posting the carousel) is the loop's job via ig-account-poster (already proven). Deterministic
# tools only here: background gen (PIL) + compose_slides.py + verify. Disk-hygienic (/tmp workdir).
#   producer.sh <deck.json>
set -uo pipefail
SK="$HOME/.claude/skills/earn-affiliate-slideshow/scripts"
QUEUE="$HOME/affiliate/queue"; mkdir -p "$QUEUE"
PY=/opt/homebrew/bin/python3
DECK="${1:?usage: producer.sh <deck.json>}"
[ -f "$DECK" ] || { echo "{\"producer\":\"affiliate\",\"did\":\"no deck $DECK\"}"; exit 0; }
ID="aff$(date +%s)"; WORK="/tmp/aff-prod-$$"; OUT="$QUEUE/$ID"; mkdir -p "$WORK" "$OUT"
trap 'rm -rf "$WORK"' EXIT

# validate deck: every slide must have a contiguous n (1..N) AND non-empty text (FIND-005/006).
N=$("$PY" - "$DECK" <<'PYV' 2>/dev/null || echo 0
import json,sys
d=json.load(open(sys.argv[1])); sl=d.get("slides",[])
ns=sorted(int(s.get("n",0)) for s in sl)
if not sl or ns!=list(range(1,len(sl)+1)): print(0); sys.exit()   # n must be exactly 1..N
if any(not str(s.get("text","")).strip() for s in sl): print(0); sys.exit()  # no empty slide
print(len(sl))
PYV
)
[ "$N" -ge 3 ] || { echo "{\"producer\":\"affiliate\",\"did\":\"deck invalid (need contiguous n=1..N, non-empty text, >=3 slides)\"}"; exit 0; }

# 1) gradient background per slide, named by the deck's own n (compose opens slide_<n>.png) (FIND-006)
"$PY" - "$WORK" "$N" <<'PYBG'
import sys
from PIL import Image
work, n = sys.argv[1], int(sys.argv[2])
for i in range(1, n + 1):
    img = Image.new("RGB", (1080, 1920))
    for y in range(1920):
        t = y / 1920.0
        r, g, b = int(12 + 20 * t), int(40 + 36 * (1 - t)), int(56 + 60 * t)
        for x in range(1080):
            img.putpixel((x, y), (r, g, b))
    img.save(f"{work}/slide_{i}.png")
print(f"bg {n}")
PYBG

# 2) compose JP text onto backgrounds
"$PY" "$SK/compose_slides.py" "$DECK" "$WORK" >/dev/null 2>&1 || { echo "{\"producer\":\"affiliate\",\"did\":\"compose failed\"}"; exit 0; }

# 3) verify each composed PNG (exists + 1080x1920) → queue
ok=0
for i in $(seq 1 "$N"); do
  f="$WORK/composed_$i.png"
  dim=$("$PY" -c "from PIL import Image;im=Image.open('$f');print(f'{im.width}x{im.height}')" 2>/dev/null || echo "0x0")
  [ "$dim" = "1080x1920" ] && { cp "$f" "$OUT/slide_$i.png"; ok=$((ok + 1)); }
done

# 4) caption sidecar — #PR is MANDATORY (景表法); append it to ANY deck-supplied caption if missing (FIND-004)
"$PY" - "$DECK" <<'PYC' > "$OUT/caption.txt" 2>/dev/null
import json,sys
cap=json.load(open(sys.argv[1])).get("caption","AI仕事術。 リンクはプロフィール")
if "#PR" not in cap and "＃PR" not in cap: cap=cap.rstrip()+" #PR"
print(cap)
PYC

if [ "$ok" -eq "$N" ] && [ "$N" -ge 3 ]; then
  echo "{\"producer\":\"affiliate\",\"did\":\"queued $ID ($ok verified slides)\",\"queue\":\"$OUT\"}"
else
  rm -rf "$OUT"; echo "{\"producer\":\"affiliate\",\"did\":\"verify failed ($ok/$N) — not queued\"}"
fi
