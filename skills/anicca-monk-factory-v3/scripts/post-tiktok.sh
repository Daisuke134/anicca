#!/usr/bin/env bash
# Post a video to TikTok (@anicca_cemetery) via camofox {{profile.lateness.stakeholders.channel}} — REAL manual upload (human-treated → views).
# Usage: post-tiktok.sh <video.mp4> <caption.txt>
# Assumes camofox is logged into TikTok (session persists on disk). Login once via tiktok.com/login
#   (anicca_cemetery / MONK_TIKTOK_EN_PASSWORD; TikTok 2FA goes to Gmail → read with gog if prompted).
#
# 🔴 HARD-WON caption mechanic (do NOT change without re-verifying on the live page):
#   TikTok's description is a Draft.js contenteditable. Setting it reliably =
#     focus → selectAll+delete → execCommand('insertText') → dispatch input event → BLUR the field.
#   The BLUR is critical: Draft.js only commits to React state on blur. If you click Post via JS
#   .click() (no blur) the post goes out with the FILENAME as caption (slop). So we BLUR, then click
#   Post with a REAL-MOUSE camofox click (which also moves the mouse off the field). Verified 2026-05-23.
set -uo pipefail
source "$(dirname "$0")/lib/camo.sh"
VIDEO="$1"; CAPFILE="$2"
[ -f "$VIDEO" ] || { echo "FATAL: video not found: $VIDEO"; exit 1; }
[ -f "$CAPFILE" ] || { echo "FATAL: caption file not found: $CAPFILE"; exit 1; }
CAPTION="$(cat "$CAPFILE")"
TAB=$(camo_open "https://www.tiktok.com/tiktokstudio/upload"); echo "TAB=$TAB"; sleep 9

# logged-in guard
if camo_text "$TAB" | grep -qiE "Log in to TikTok|Use phone / {{profile.lateness.stakeholders.channel}}"; then
  echo "NOT_LOGGED_IN — log into TikTok in camofox first (anicca_cemetery). Aborting."; exit 2
fi

SEL='[contenteditable=true][role=combobox]'
READSEL='(()=>{const e=document.querySelector("[contenteditable=true][role=combobox]")||document.querySelector("[contenteditable=true]");return e?e.innerText.replace(/\s+/g," ").trim():null})()'
EDITORCHK='(()=>{const b=[...document.querySelectorAll("button")].find(x=>/^Turn on$/i.test((x.innerText||"").trim()));if(b)b.click();return (document.querySelector("[contenteditable=true][role=combobox]")||document.querySelector("[contenteditable=true]"))?1:0})()'

echo "[1/6] upload + wait for editor (RE-UPLOAD if the first attempt does not take — common flake)"
EDITOR_OK=0
for up in 1 2 3; do
  camo_upload "$TAB" "$VIDEO" >/dev/null 2>&1; sleep 8
  for w in $(seq 1 12); do
    R=$(camo_eval "$TAB" "$EDITORCHK" | jq -r '.result // 0')
    [ "$R" = "1" ] && { EDITOR_OK=1; break; }
    sleep 3
  done
  [ "$EDITOR_OK" = "1" ] && { echo "  editor ready (upload attempt $up)"; break; }
  echo "  upload attempt $up did not produce the editor — re-uploading"
done
[ "$EDITOR_OK" = "1" ] || { echo "FATAL: editor never appeared after 3 uploads"; camo_shot "$TAB" ~/anicca-monk-factory/tt_upload_fail.png; exit 4; }

echo "[3/6] set caption — REAL keyboard typing via STABLE selector. CLEAR = Meta+a (macOS Cmd+A; Control+a does NOT select-all on Mac — that was the filename-stuck bug 2026-05-23)"
# focus + clear (real mouse + real keys) then type. Retry up to 3x until the field actually holds our caption.
PROBE_HEAD="$(printf '%s' "$CAPTION" | cut -c1-20)"
PROBE_TAG="$(printf '%s' "$CAPTION" | grep -oE '#[a-z0-9]+' | tail -1)"
FNAME="$(basename "$VIDEO" .mp4)"
FIELD=""
for try in 1 2 3; do
  camo_click_sel "$TAB" "$SEL" >/dev/null 2>&1; sleep 1
  # CLEAR with Meta+a (macOS Cmd+A) + Backspace, loop until empty (TikTok restores the last DRAFT caption — be persistent)
  for c in 1 2 3; do
    camo_press "$TAB" "Meta+a"; sleep 1; camo_press "$TAB" "Backspace"; sleep 1
    L=$(camo_eval "$TAB" '(()=>{const e=document.querySelector("[contenteditable=true][role=combobox]")||document.querySelector("[contenteditable=true]");return (e?e.innerText:"").trim().length})()' | jq -r '.result // 1')
    [ "$L" = "0" ] && break
  done
  camo_type_sel "$TAB" "$SEL" "$CAPTION" >/dev/null 2>&1; sleep 2
  camo_press "$TAB" "Escape"; sleep 1
  FIELD=$(camo_eval "$TAB" "$READSEL" | jq -r '.result // ""')
  # if a leftover filename token got appended (draft-restore artifact), strip it from the end
  if printf '%s' "$FIELD" | grep -qiF "$FNAME"; then
    camo_press "$TAB" "End"; for i in $(seq 1 ${#FNAME}); do camo_press "$TAB" "Backspace"; done; sleep 1
    FIELD=$(camo_eval "$TAB" "$READSEL" | jq -r '.result // ""')
  fi
  echo "  try $try caption field: ${FIELD:0:80}"
  if printf '%s' "$FIELD" | grep -qiF "$PROBE_HEAD" && printf '%s' "$FIELD" | grep -qiF "$PROBE_TAG" && ! printf '%s' "$FIELD" | grep -qiF "$FNAME"; then break; fi
done

echo "[4/6] 🔴 VERIFY caption BEFORE posting (must == our caption; reject filename prefix)"
echo "caption field now: ${FIELD:0:100}"
PROBE_HEAD="$(printf '%s' "$CAPTION" | cut -c1-20)"
PROBE_TAG="$(printf '%s' "$CAPTION" | grep -oE '#[a-z0-9]+' | tail -1)"
FNAME="$(basename "$VIDEO" .mp4)"
if printf '%s' "$FIELD" | grep -qiF "$FNAME"; then
  echo "CAPTION_HAS_FILENAME — '$FNAME' still in field. ABORTING (clear failed)."; camo_shot "$TAB" ~/anicca-monk-factory/tt_caption_fail.png; exit 3
elif printf '%s' "$FIELD" | grep -qiF "$PROBE_HEAD" && printf '%s' "$FIELD" | grep -qiF "$PROBE_TAG"; then
  echo "CAPTION_PREPOST_OK"
else
  echo "CAPTION_NOT_SET — field missing our caption head/tag. ABORTING before posting slop."; camo_shot "$TAB" ~/anicca-monk-factory/tt_caption_fail.png; exit 3
fi

echo "[5/6] click Post via JS (caption is in React state from real typing)"
camo_eval "$TAB" '(()=>{const b=[...document.querySelectorAll("button")].find(x=>/^Post$/i.test((x.innerText||"").trim())&&!x.disabled);if(b){b.click();return{clicked:1}}return{clicked:0}})()'; echo; sleep 7
# content-check modal may re-appear at Post → confirm it
camo_eval "$TAB" '(()=>{const b=[...document.querySelectorAll("button")].find(x=>/^(Turn on|Post now)$/i.test((x.innerText||"").trim()));if(b){b.click();return{m:1}}return{m:0}})()' >/dev/null; sleep 8
URL_AFTER="$(camo_url "$TAB")"; echo "post URL: $URL_AFTER"
case "$URL_AFTER" in *"/content"*) echo "POST_SUBMITTED_OK";; *) echo "WARN: still on $URL_AFTER — Post may not have submitted";; esac

echo "[6/6] VERIFY caption on the TOP (newest) post in /content"
camo_nav "$TAB" "https://www.tiktok.com/tiktokstudio/content"; sleep 5
# top post description is the FIRST post-description text node in the list
TOPCAP=$(camo_eval "$TAB" '(()=>{const links=[...document.querySelectorAll("a[href*=video]")];if(!links.length)return"";const first=links[0];const row=first.closest("[class*=row],tr,li")||first.parentElement.parentElement;return (row.innerText||"").replace(/\s+/g," ").slice(0,120)})()' | jq -r .result)
echo "TOP post text: $TOPCAP"
PROBE="$(printf '%s' "$CAPTION" | cut -c1-25)"
VIDURL=$(camo_eval "$TAB" '(()=>{const a=[...document.querySelectorAll("a")].map(x=>x.href).find(h=>/video\/\d{15,}/.test(h));return a||""})()' | jq -r '.result // ""')
if printf '%s' "$TOPCAP" | grep -qiF "$PROBE"; then
  echo "CAPTION_VERIFIED_OK"
  echo "TIKTOK_URL=$VIDURL"
else
  echo "CAPTION_MISMATCH — top post does not show our caption. Likely filename slop — FIX & retry."
fi
echo "TIKTOK_POST_DONE video=$VIDEO"
