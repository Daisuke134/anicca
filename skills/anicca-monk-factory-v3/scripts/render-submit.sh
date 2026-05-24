#!/usr/bin/env bash
# Deterministically drive HeyGen Video Agent (camofox) to submit a render, print the project URL.
# Usage: render-submit.sh "<script text>"   →  stdout last line: PROJECT_URL=https://app.heygen.com/video-agent/<id>
# Encodes the proven manual flow (2026-05-23): Wise Elder avatar + attach avatar.mp4 + strict EN instruction + Submit.
set -uo pipefail
source "$(dirname "$0")/lib/camo.sh"
SCRIPT="$1"
AVATAR_MP4="/Users/anicca/Downloads/avatar.mp4"
camo_up
TAB=$(camo_open "https://app.heygen.com/video-agent"); sleep 9

# --- select avatar = Wise Elder of Tranquility (verify by composer img src ee4d1127); retry up to 3x ---
sel_ok=0
for try in 1 2 3; do
  camo_click_sel "$TAB" '.glass-pill:has-text("Avatar")' >/dev/null 2>&1; sleep 3
  # My Avatars tab
  camo_click_sel "$TAB" ':text-is("My Avatars")' >/dev/null 2>&1; sleep 2
  # expand the anicca_en_monk_v1 group's 3 looks
  camo_click_sel "$TAB" 'div.tw-text-xs:text-is("Browse 3 looks")' >/dev/null 2>&1; sleep 2
  # pick Wise Elder (leftmost)
  camo_click_sel "$TAB" 'img[alt="Wise Elder of Tranquility"]' >/dev/null 2>&1; sleep 1
  camo_click_sel "$TAB" ':nth-match(button:has-text("Use Avatar"), 1)' >/dev/null 2>&1; sleep 3
  SRC=$(camo_eval "$TAB" '(()=>{const p=[...document.querySelectorAll(".glass-pill")].find(e=>/Avatar/.test(e.innerText));const i=p&&p.querySelector("img");return i?i.src:""})()' | jq -r '.result // ""')
  case "$SRC" in *ee4d1127*) sel_ok=1; echo "avatar=Wise Elder verified (try $try)"; break;; esac
  echo "avatar not Wise Elder yet (try $try) — retry"; camo_press "$TAB" "Escape"; sleep 1
done
[ "$sel_ok" = "1" ] || { echo "FATAL: could not select Wise Elder avatar"; exit 2; }

# --- attach avatar.mp4 (carries the locked voice) to the composer file input ---
camo_upload "$TAB" "$AVATAR_MP4" "input[type=file]" >/dev/null 2>&1; sleep 6

# --- type strict instruction + script into the Describe textbox ---
# 🔴 ONE LINE ONLY — a newline in the Video Agent textbox = Enter = early submit (the script after the
#   newline never gets typed → agent says "script was missing after the colon" → no video). 2026-05-24.
SCRIPT_ONELINE=$(printf '%s' "$SCRIPT" | tr '\n' ' ')
INSTR="STRICT: use the selected avatar (anicca_en_monk_v1, Wise Elder of Tranquility) and the voice from the attached avatar.mp4. Do NOT change avatar or voice. ENGLISH only — speak this script word for word, DO NOT translate to Japanese, no rewrite. ONE talking-head portrait 9:16 for TikTok, no B-roll/scene/narrator swap. Script to speak verbatim in English: $SCRIPT_ONELINE"
camo_type_sel "$TAB" '[placeholder*="Describe"]' "$INSTR" >/dev/null 2>&1; sleep 2
# verify the script text landed
LEN=$(camo_eval "$TAB" '(()=>{const t=document.querySelector("[placeholder*=Describe],textarea");return t?(t.value||t.innerText||"").length:0})()' | jq -r '.result // 0')
[ "$LEN" -gt 100 ] 2>/dev/null || { echo "FATAL: instruction did not land in textbox (len=$LEN)"; exit 3; }

# --- Submit: the Video Agent textbox submits on ENTER (the whole one-line text is now in it).
#     (A stray mid-text newline submits early — that's why INSTR must be ONE line. Enter at the end = submit full.) ---
camo_press "$TAB" "Escape" >/dev/null 2>&1; sleep 1   # close any hashtag/mention dropdown
camo_eval "$TAB" '(()=>{const t=document.querySelector("[placeholder*=Describe],textarea");if(t)t.focus();return 0})()' >/dev/null 2>&1
camo_press "$TAB" "Enter" >/dev/null 2>&1; sleep 6
URL=$(camo_url "$TAB")
case "$URL" in *"/video-agent/"*) : ;; *)
  # fallback: click the Submit button
  camo_click_sel "$TAB" 'button:has-text("Submit")' >/dev/null 2>&1; sleep 8; URL=$(camo_url "$TAB") ;;
esac
case "$URL" in
  *"/video-agent/"*) echo "SUBMITTED ok"; echo "PROJECT_URL=$URL";;
  *) echo "FATAL: did not navigate to a project after Submit (url=$URL)"; exit 4;;
esac
