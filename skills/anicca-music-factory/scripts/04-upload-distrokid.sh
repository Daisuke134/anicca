#!/usr/bin/env bash
# DistroKid auto-upload via playwright-cli.
# Submits ONE single track. Apple Music + iTunes ALWAYS unchecked
# (Anicca's policy — never set up Apple credits).
#
# Validated 2026-05-01 with track "Empty Sky" → /new/done/?albumuuid=...
#
# Usage:
#   04-upload-distrokid.sh <audio_path> <cover_path> <title> <genre_jp> <release_yyyy_mm_dd> <output_dir>
#
# Output:
#   $output_dir/upload-receipt.json with { albumuuid, hyperfollow_url, release_date }
#
# Prereq: bash setup-login.sh has been run once (cookies saved in
# session "distrokid").

set -uo pipefail

AUDIO="$1"
COVER="$2"
TITLE="$3"
GENRE_JP="$4"        # e.g. "ニューエイジ" / "ワールド" / "クラシック"
RELEASE_DATE="$5"    # YYYY-MM-DD
OUTDIR="$6"

mkdir -p "$OUTDIR"

# ──────── helpers ────────
PROFILE_DIR="$HOME/.openclaw/playwright-cli/distrokid-profile"
mkdir -p "$PROFILE_DIR"
SS="playwright-cli -s=distrokid"
SS_OPEN="playwright-cli -s=distrokid open --persistent --profile=$PROFILE_DIR"

snap() { $SS snapshot 2>&1; }

# Escape regex metachars in a string so it can be safely embedded in grep -E.
re_escape() {
    printf '%s' "$1" | sed 's/[][(){}.*+?^$|\\]/\\&/g'
}

# Find the first ref of a role with a matching name. Args: role name
# Examples:
#   find_ref checkbox "Apple Music"
#   find_ref radio    "インスト"
#   find_ref button   "続ける"
#   find_ref checkbox "作曲 (composed by AI)"   ← parens auto-escaped
find_ref() {
    local role="$1"
    local name="$2"
    local safe_name
    safe_name=$(re_escape "$name")
    snap | grep -E "${role} \"${safe_name}\".*\[ref=e[0-9]+\]" \
         | head -1 \
         | grep -oE 'ref=e[0-9]+' \
         | sed 's/ref=//'
}

# Find ref of an element where the visible label/text contains substr.
# Used for radios/checkboxes whose accessible name is the label below them.
find_ref_after_text() {
    local pattern="$1"
    snap | grep -B1 "$pattern" | grep -oE 'ref=e[0-9]+' | head -1 | sed 's/ref=//'
}

step() {
    local label="$1"; shift
    if "$@"; then
        echo "  ✓ $label"
    else
        echo "  ✗ $label FAILED" >&2
        return 1
    fi
}

fail() {
    echo "❌ FAILED at $1: $2" >&2
    $SS screenshot 2>/dev/null
    exit 1
}

# ──────── 0. open {{profile.lateness.stakeholders.channel}} with persistent profile (idempotent) ────────
# Cookies for DistroKid are persisted in $PROFILE_DIR (Chrome user-data-dir).
# Without --persistent --profile=..., playwright-cli loses storage state on close.
echo "[0] ensure {{profile.lateness.stakeholders.channel}} is open (profile: $PROFILE_DIR)"
$SS_OPEN 2>&1 | tail -1 || true
sleep 2

# Confirm snapshot works (proves the {{profile.lateness.stakeholders.channel}} is actually reachable).
PROBE=$(snap | head -3)
if echo "$PROBE" | grep -qiE '{{profile.lateness.stakeholders.channel}} .* not open|please run open'; then
    echo "  → first open didn't stick, retrying..."
    $SS_OPEN 2>&1 | tail -1 || true
    sleep 3
    PROBE=$(snap | head -3)
fi
if echo "$PROBE" | grep -qiE '{{profile.lateness.stakeholders.channel}} .* not open|please run open'; then
    fail "session" "playwright-cli session 'distrokid' could not be opened. setup-login.sh must be run once to seed cookies (profile: $PROFILE_DIR)."
fi

# ──────── 1. open /new/ ────────
echo "[1] open /new/"
$SS goto https://distrokid.com/new/ 2>&1 | tail -1
sleep 3

# Verify session alive
URL=$(snap | grep -m1 "Page URL" | awk '{print $4}')
if [[ "$URL" == *"signin"* ]]; then
    fail "session" "DistroKid login expired — run ~/.openclaw/skills/anicca-music-factory/scripts/setup-login.sh and sign in again"
fi

# ──────── 2. uncheck Apple Music + iTunes ────────
echo "[2] uncheck Apple Music + iTunes"
APPLE_REF=$(find_ref checkbox "Apple Music")
ITUNES_REF=$(find_ref checkbox "iTunes")
if [ -n "$APPLE_REF" ]; then
    $SS click "$APPLE_REF" 2>&1 | tail -1
    sleep 1
fi
if [ -n "$ITUNES_REF" ]; then
    $SS click "$ITUNES_REF" 2>&1 | tail -1
    sleep 1
fi

# ──────── 3. release date ────────
echo "[3] release date $RELEASE_DATE"
$SS fill "#release-date-dp" "$RELEASE_DATE" 2>&1 | tail -1
sleep 1

# ──────── 4. primary genre ────────
# DistroKid has changed this UI multiple times.
# Do not rely on nearby heading text like メインジャンル / 第二ジャンル.
# Instead, scan all combobox refs and choose the first one that actually accepts GENRE_JP.
echo "[4] primary genre = $GENRE_JP"

find_genre_combobox_ref() {
    local ref
    local refs
    refs=$(snap | grep -E 'combobox.*\[ref=e[0-9]+\]' | grep -oE 'ref=e[0-9]+' | sed 's/ref=//' | awk '!seen[$0]++')
    for ref in $refs; do
        if snap | grep -A120 "\[ref=$ref\]" | grep -F "option \"$GENRE_JP\"" -q; then
            echo "$ref"
            return 0
        fi
    done
    return 1
}

GENRE_REF=$(find_genre_combobox_ref)
if [ -z "$GENRE_REF" ]; then
    snap > "$OUTDIR/.genre-debug.snap" 2>&1
    fail "genre" "could not find combobox containing '$GENRE_JP' (debug: $OUTDIR/.genre-debug.snap)"
fi
echo "  primary genre combobox = $GENRE_REF"

select_genre() {
    $SS click "$GENRE_REF" 2>&1 | tail -1
    sleep 1
    $SS select "$GENRE_REF" "$GENRE_JP" 2>&1 | tail -1
    sleep 2
    snap | grep -A120 "\[ref=$GENRE_REF\]" | grep -E "option \"$(re_escape "$GENRE_JP")\".*\[selected\]" -q
}

if ! select_genre; then
    echo "  retrying genre select..."
    sleep 1
    select_genre || {
        snap > "$OUTDIR/.genre-debug.snap" 2>&1
        fail "genre" "could not select '$GENRE_JP' in combobox $GENRE_REF after retry (debug: $OUTDIR/.genre-debug.snap)"
    }
fi
echo "  ✓ genre selected: $GENRE_JP"

# ──────── 5. cover ────────
echo "[5] cover $COVER"
COVER_BTN=$(find_ref button "Choose File")
[ -z "$COVER_BTN" ] && fail "cover-btn" "no Choose File button"
$SS click "$COVER_BTN" 2>&1 | tail -1
sleep 1
$SS upload "$COVER" 2>&1 | tail -1
sleep 2

# ──────── 6. track title ────────
echo "[6] title \"$TITLE\""
TITLE_REF=$(find_ref textbox "トラック1の曲名")
[ -z "$TITLE_REF" ] && fail "title" "no title textbox"
$SS fill "$TITLE_REF" "$TITLE" 2>&1 | tail -1
sleep 1

# ──────── 7. audio ────────
echo "[7] audio $AUDIO"
# Second "Choose File" button is for audio (cover button now consumed)
AUDIO_BTN=$(snap | grep -E 'button "Choose File".*\[ref=e[0-9]+\]' | tail -1 | grep -oE 'ref=e[0-9]+' | sed 's/ref=//')
[ -z "$AUDIO_BTN" ] && fail "audio-btn" "no audio Choose File"
$SS click "$AUDIO_BTN" 2>&1 | tail -1
sleep 1
$SS upload "$AUDIO" 2>&1 | tail -1
sleep 2

# ──────── 8. songwriter ────────
echo "[8] songwriter <your-name>"
FIRST_REF=$(snap | grep -E 'textbox "名".*\[ref=e[0-9]+\]' | head -1 | grep -oE 'ref=e[0-9]+' | sed 's/ref=//')
LAST_REF=$(snap | grep -E 'textbox "姓".*\[ref=e[0-9]+\]' | head -1 | grep -oE 'ref=e[0-9]+' | sed 's/ref=//')
[ -z "$FIRST_REF" ] && fail "songwriter-first" "no first name field"
[ -z "$LAST_REF" ] && fail "songwriter-last" "no last name field"
$SS fill "$FIRST_REF" "Daisuke" 2>&1 | tail -1
$SS fill "$LAST_REF" "Narita" 2>&1 | tail -1
sleep 1

# ──────── 9. instrumental ────────
echo "[9] instrumental"
INST_REF=$(find_ref radio "インスト")
[ -z "$INST_REF" ] && fail "instrumental" "no インスト radio"
$SS click "$INST_REF" 2>&1 | tail -1
sleep 1

# ──────── 10. AI = はい (Yes) — required disclosure for Spotify ────────
# In the AI section there are 2 radios: いいえ (1st), はい (2nd, TARGET).
# Lying = Spotify ban risk. We MUST disclose.
echo "[10] AI = はい (Yes)"
AI_YES_REF=$(snap \
  | awk '/heading.*Does this song include AI/{f=1} f; f && /separator \[ref/{exit}' \
  | grep -E 'radio.*\[ref=e[0-9]+\]' \
  | sed -n '2p' \
  | grep -oE 'ref=e[0-9]+' \
  | sed 's/ref=//')
[ -z "$AI_YES_REF" ] && fail "ai-yes" "could not locate AI Yes radio (2nd radio in AI section)"
echo "  AI Yes radio = $AI_YES_REF"
$SS click "$AI_YES_REF" 2>&1 | tail -1
sleep 3

# ──────── 11. AI modal: 作曲 + All of audio + 保存する ────────
echo "[11] AI modal: composed + all audio + save"
# Modal may take up to 10s to render. Retry finding 作曲 checkbox.
COMPOSED_REF=""
for retry in 1 2 3 4 5 6 7 8 9 10; do
    COMPOSED_REF=$(find_ref checkbox "作曲 (composed by AI)")
    if [ -n "$COMPOSED_REF" ]; then break; fi
    sleep 1
done
if [ -z "$COMPOSED_REF" ]; then
    snap > "$OUTDIR/.ai-modal-debug.snap" 2>&1
    $SS screenshot 2>/dev/null
    fail "ai-composed" "no 作曲 checkbox after 10s. Debug: $OUTDIR/.ai-modal-debug.snap"
fi
ALLAUDIO_REF=$(find_ref checkbox "All of the audio (performed by AI)")
SAVE_REF=$(find_ref button "保存する")
[ -z "$ALLAUDIO_REF" ] && fail "ai-all-audio" "no All of audio checkbox"
[ -z "$SAVE_REF" ] && fail "ai-save" "no 保存する button"
$SS check "$COMPOSED_REF" 2>&1 | tail -1
$SS check "$ALLAUDIO_REF" 2>&1 | tail -1
sleep 1
$SS click "$SAVE_REF" 2>&1 | tail -1
sleep 3

# ──────── 12. Apple persona = haven't released (defensive; even with Apple unchecked) ────────
echo "[12] Apple persona = haven't released (defensive)"
APPLE_NEVER=$(snap | grep -B1 'Anicca名義でiTunes・Apple Musicに配信したことはない' | grep -oE 'ref=e[0-9]+' | head -1 | sed 's/ref=//')
if [ -n "$APPLE_NEVER" ]; then
    $SS click "$APPLE_NEVER" 2>&1 | tail -1
    sleep 1
fi

# ──────── 13. final mandatory checkboxes (5-6 depending on title) ────────
# DistroKid sometimes shows a 6th conditional checkbox about title capitalization.
# Use grep -F (fixed string) so labels with special chars don't break the regex.
echo "[13] final mandatory checkboxes"
for label in \
    "配信先として「YouTube Music」を選択しました" \
    "特殊な大文字／小文字表記が使われています" \
    "再生回数を増やすサービスを使用しません" \
    "この音源は私自身がレコーディングしたものです" \
    "アーティスト名、曲名、アルバム名に、承認を得ていない他のアーティスト" \
    "以下の利用規約を読み、同意しました"; do
    REF=$(snap | grep -F "checkbox \"${label}" | head -1 | grep -oE 'ref=e[0-9]+' | sed 's/ref=//')
    if [ -n "$REF" ]; then
        $SS check "$REF" 2>&1 | tail -1
        echo "  ✓ checked: ${label:0:30}..."
    else
        # Conditional checkboxes (e.g. capitalization warning) may not appear → silent
        :
    fi
done
sleep 1

# ──────── 14. submit (続ける) ────────
echo "[14] submit"
SUBMIT_REF=$(find_ref button "続ける")
[ -z "$SUBMIT_REF" ] && fail "submit" "no 続ける button"
$SS click "$SUBMIT_REF" 2>&1 | tail -1
sleep 5

# ──────── 15. handle Mixea upsell page ────────
URL=$(snap | grep -m1 "Page URL" | awk '{print $4}')
if [[ "$URL" == *"/new/mixea"* ]]; then
    echo "[15] skip Mixea mastering"
    USE_UPLOADED=$(find_ref button "アップロードしたバージョンを使用")
    if [ -n "$USE_UPLOADED" ]; then
        $SS click "$USE_UPLOADED" 2>&1 | tail -1
        sleep 5
    fi
fi

# ──────── 16. verify success on /new/done/ ────────
URL=$(snap | grep -m1 "Page URL" | awk '{print $4}')
if [[ "$URL" != *"/new/done"* ]]; then
    fail "post-submit" "did not reach /new/done — current URL: $URL"
fi

# Extract albumuuid + hyperfollow URL
ALBUM_UUID=$(echo "$URL" | grep -oE 'albumuuid=[A-F0-9-]+' | sed 's/albumuuid=//')
HF_URL=$(snap | grep -oE 'https://distrokid\.com/hyperfollow/[^ )]+' | head -1)

# ──────── 17. write receipt ────────
echo "[17] receipt → $OUTDIR/upload-receipt.json"
jq -nc \
    --arg uuid  "$ALBUM_UUID" \
    --arg hf    "$HF_URL" \
    --arg title "$TITLE" \
    --arg rd    "$RELEASE_DATE" \
    --arg ts    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{albumuuid:$uuid, hyperfollow_url:$hf, title:$title, release_date:$rd, uploaded_at:$ts, status:"submitted"}' \
    > "$OUTDIR/upload-receipt.json"

echo "✓ DistroKid upload complete: \"$TITLE\" (albumuuid=$ALBUM_UUID)"
