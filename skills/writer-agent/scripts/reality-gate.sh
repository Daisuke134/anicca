#!/usr/bin/env bash
# reality-gate.sh — L4 post-publish gate (spec #20). Verify the PUBLISHED reality, not our own logs.
# Checks what the publish-time verifiers cannot: is it actually live, as an anonymous reader sees it,
# with the paid settings that were requested, and are the images actually being served.
# Pixel-size checks stay in the per-platform verifiers (verify-draft/verify-preview/x_fullverify).
#
# Usage:
#   reality-gate.sh note <key> [--paid <price>]     # published state + paid config + image URLs alive
#   reality-gate.sh x <live-status-url>             # delegates to publish-to-x.sh verify (px + shots)
#   reality-gate.sh ssr <url> [<must-contain> ...]  # substack/zenn/devto: 200 + content + images alive
# stdout: machine tokens + final VERDICT=PASS|FAIL. exit 0 only on PASS.
# On FAIL the calling agent fixes and republishes — it never calls a human.
set -uo pipefail
UA="Mozilla/5.0"
FAILS=()

tok() { echo "$1"; }
fail() { FAILS+=("$1"); echo "FAIL_$1" >&2; }

img_alive() { # <url> -> 0 if HTTP 200 and content-type image
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" -A "$UA" -L "$1")
  [ "$code" = "200" ]
}

cmd="${1:-}"; shift || true
case "$cmd" in
  note)
    KEY="${1:-}"; shift || true
    PAID=""
    while [ $# -gt 0 ]; do case "$1" in --paid) PAID="$2"; shift 2;; *) shift;; esac; done
    [ -n "$KEY" ] || { echo "usage: reality-gate.sh note <key> [--paid <price>]"; exit 2; }
    J=$(curl -s -A "$UA" "https://note.com/api/v3/notes/$KEY")
    STATUS=$(printf '%s' "$J" | jq -r '.data.status // empty')
    PRICE=$(printf '%s' "$J" | jq -r '.data.price // 0')
    LIMITED=$(printf '%s' "$J" | jq -r '.data.is_limited // false')
    TRIAL=$(printf '%s' "$J" | jq -r '.data.is_trial // false')
    URL=$(printf '%s' "$J" | jq -r '.data.note_url // empty')
    tok "NOTE_STATUS=$STATUS"; tok "NOTE_PRICE=$PRICE"; tok "NOTE_URL=$URL"
    [ "$STATUS" = "published" ] || fail "not_published:$STATUS"
    if [ -n "$PAID" ]; then
      [ "$PRICE" = "$PAID" ] || fail "price_mismatch:want=$PAID got=$PRICE"
      [ "$LIMITED" = "false" ] || fail "is_limited_true"
      [ "$TRIAL" = "false" ] || fail "is_trial_true"
    fi
    # anonymous reader view: page reachable + eyecatch + body images actually served
    if [ -n "$URL" ]; then
      HTML=$(curl -s -A "$UA" -L "$URL")
      [ -n "$HTML" ] || fail "public_page_empty"
      EYE=$(printf '%s' "$HTML" | grep -o 'property="og:image" content="[^"]*"' | head -1 | sed 's/.*content="//; s/"$//')
      if [ -z "$EYE" ]; then
        fail "eyecatch_missing"
      elif [[ "$EYE" != https://assets.st-note.com/* ]]; then
        fail "eyecatch_wrong_host"
      elif img_alive "$EYE"; then
        tok "EYECATCH_ALIVE=true"
      else
        fail "eyecatch_dead"
      fi
      N_OK=0; N_DEAD=0
      while IFS= read -r u; do
        [ -z "$u" ] && continue
        if img_alive "$u"; then N_OK=$((N_OK+1)); else N_DEAD=$((N_DEAD+1)); fi
      done < <(printf '%s' "$HTML" | grep -o 'https://assets\.st-note\.com/img/[^"?]*' | sort -u | head -20)
      tok "BODY_IMAGES_ALIVE=$N_OK DEAD=$N_DEAD"
      [ "$N_DEAD" -eq 0 ] || fail "dead_body_images:$N_DEAD"
      [ "$N_OK" -ge 1 ] || fail "body_image_missing"
    fi
    ;;
  x)
    URL="${1:-}"; [ -n "$URL" ] || { echo "usage: reality-gate.sh x <live-url>"; exit 2; }
    DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if bash "$DIR/x-publish/publish-to-x.sh" verify "$URL"; then tok "X_VERIFY=pass"; else fail "x_verify"; fi
    ;;
  ssr)
    URL="${1:-}"; shift || true
    [ -n "$URL" ] || { echo "usage: reality-gate.sh ssr <url> [<must-contain> ...]"; exit 2; }
    # SSR pages (substack/zenn/devto) embed content in JSON blobs with \uXXXX escapes —
    # raw grep misses Japanese text and mangles image URLs. Decode in python instead.
    OUT=$(python3 - "$URL" "$@" <<'PYEOF'
import sys, re, json, urllib.request, warnings
from html.parser import HTMLParser
warnings.filterwarnings("ignore")
url, needles = sys.argv[1], sys.argv[2:]
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    r = urllib.request.urlopen(req, timeout=30)
    raw = r.read().decode("utf-8", "replace")
    print(f"HTTP={r.status}")
except Exception as e:
    print(f"HTTP=ERR {e}"); print("VERDICT_HINT=FAIL"); sys.exit(0)
# decoded view: turn \uXXXX json escapes into real chars for matching
dec = raw
try:
    dec = raw.encode().decode("unicode_escape").encode("latin-1", "ignore").decode("utf-8", "ignore")
except Exception:
    pass
fails = []
for n in needles:
    if n in raw or n in dec: print(f"CONTAINS_OK={n}")
    else: fails.append(f"missing:{n}")
class ArticleMedia(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.stack = []
        self.imgs = set()
        self.svgs = 0
    def handle_starttag(self, tag, attrs):
        enters = tag.lower() in {"article", "main"}
        if enters: self.depth += 1
        self.stack.append((tag.lower(), enters))
        values = dict(attrs)
        if self.depth and tag.lower() == "img":
            src = values.get("src", "")
            if src.startswith("https://"): self.imgs.add(src)
        if self.depth and tag.lower() == "svg": self.svgs += 1
    def handle_endtag(self, tag):
        for index in range(len(self.stack)-1, -1, -1):
            if self.stack[index][0] == tag.lower():
                closing = self.stack[index:]
                del self.stack[index:]
                self.depth -= sum(1 for _, enters in closing if enters)
                break
parser = ArticleMedia()
parser.feed(raw)
imgs = set(parser.imgs)
# Substack can serialize body image URLs into hydration JSON outside the
# article node. Include only its publication-media host as a fallback.
for blob in (raw, dec):
    imgs |= set(re.findall(r"https://substack-post-media\.s3\.amazonaws\.com/public/images/[0-9a-f-]+_[0-9]+x[0-9]+\.png", blob))
ok = dead = 0
for u in sorted(imgs)[:20]:
    try:
        c = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).status
        ok += 1 if c == 200 else 0
        dead += 0 if c == 200 else 1
    except Exception:
        dead += 1
print(f"BODY_IMAGES_ALIVE={ok} DEAD={dead}")
if dead: fails.append(f"dead_body_images:{dead}")
if ok + parser.svgs < 1: fails.append("body_media_missing")
print("VERDICT_HINT=" + ("FAIL " + " ".join(fails) if fails else "PASS"))
PYEOF
)
    printf '%s\n' "$OUT" | grep -v '^VERDICT_HINT='
    HINT=$(printf '%s\n' "$OUT" | grep '^VERDICT_HINT=' | sed 's/^VERDICT_HINT=//')
    [ "$HINT" = "PASS" ] || fail "${HINT#FAIL }"
    ;;
  *)
    echo "usage: reality-gate.sh note|x|ssr ..."; exit 2 ;;
esac

if [ ${#FAILS[@]} -eq 0 ]; then echo "VERDICT=PASS"; exit 0
else echo "VERDICT=FAIL ${FAILS[*]}"; exit 1; fi
